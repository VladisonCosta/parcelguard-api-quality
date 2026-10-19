"""Logistics demo API built for contract, security, idempotency and concurrency QA."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

DB_DEFAULT = Path(__file__).resolve().parent.parent / 'data' / 'parcelguard.sqlite3'
STAGES = ("CREATED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED")
NEXT = {"CREATED": "PICKED_UP", "PICKED_UP": "IN_TRANSIT", "IN_TRANSIT": "OUT_FOR_DELIVERY", "OUT_FOR_DELIVERY": "DELIVERED"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def digest_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 150_000).hex()


def db_open(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db


@contextmanager
def session(path: Path):
    db = db_open(path)
    try:
        yield db
    finally:
        db.close()


def setup(path: Path):
    with session(path) as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users(
              id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
              salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tokens(
              token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shipments(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              customer_id INTEGER NOT NULL REFERENCES users(id), destination TEXT NOT NULL,
              service_level TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'CREATED',
              version INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scans(
              id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
              shipment_id INTEGER NOT NULL REFERENCES shipments(id),
              new_status TEXT NOT NULL, expected_version INTEGER NOT NULL,
              occurred_at TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_shipments_customer ON shipments(customer_id);
            CREATE INDEX IF NOT EXISTS ix_scans_shipment ON scans(shipment_id);
        ''')
        for email, role in (("operator@parcelguard.local", "OPERATOR"), ("ana@parcelguard.local", "CUSTOMER"), ("bruno@parcelguard.local", "CUSTOMER")):
            if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                continue
            salt = secrets.token_bytes(16)
            db.execute("INSERT INTO users(email,salt,password_hash,role) VALUES(?,?,?,?)",
                       (email, salt.hex(), digest_password("demo1234", salt), role))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(StrictModel):
    email: str
    password: str


class CreateShipment(StrictModel):
    customer_email: str = Field(min_length=5, max_length=120)
    destination: str = Field(min_length=8, max_length=180)
    service_level: Literal["STANDARD", "EXPRESS"] = "STANDARD"


class Scan(StrictModel):
    event_id: str = Field(min_length=6, max_length=64, pattern=r'^[A-Za-z0-9-]+$')
    new_status: Literal["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]
    expected_version: int = Field(ge=0)
    occurred_at: datetime

    @field_validator('occurred_at')
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if not value.tzinfo or value.utcoffset() is None:
            raise ValueError('timestamp must include timezone')
        return value.astimezone(timezone.utc)


def to_shipment(row: sqlite3.Row):
    return {
        "tracking_id": f"PG-{row['id']:06d}", "customer_email": row['email'],
        "destination": row['destination'], "service_level": row['service_level'],
        "status": row['status'], "version": row['version'],
        "created_at": row['created_at'], "updated_at": row['updated_at'],
    }


def create_app(db_path: Path | None = None) -> FastAPI:
    path = Path(db_path or os.environ.get('PARCELGUARD_DB_PATH', DB_DEFAULT))
    setup(path)
    app = FastAPI(title="ParcelGuard QA | Logistics API", version="1.0.0", description="Fictional API for quality engineering tests. Demo only.")

    def current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, detail='Authentication required')
        token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
        with session(path) as db:
            row = db.execute('''SELECT u.id,u.email,u.role FROM tokens t JOIN users u ON u.id=t.user_id
                                 WHERE t.token_hash=? AND t.expires_at>?''',
                             (token_hash, utc_now().isoformat())).fetchone()
        if not row:
            raise HTTPException(401, detail='Invalid or expired token')
        return dict(row)

    def operator_only(user: dict) -> None:
        if user['role'] != 'OPERATOR':
            raise HTTPException(403, detail='Operator role required')

    def find_shipment(db, tracking_id: str, user: dict):
        if not tracking_id.startswith('PG-') or not tracking_id[3:].isdigit():
            raise HTTPException(404, detail='Shipment not found')
        row = db.execute('''SELECT s.*,u.email FROM shipments s JOIN users u ON u.id=s.customer_id
                            WHERE s.id=?''', (int(tracking_id[3:]),)).fetchone()
        if not row or (user['role'] != 'OPERATOR' and row['customer_id'] != user['id']):
            raise HTTPException(404, detail='Shipment not found')
        return row

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'parcelguard', 'api_version': 'v1'}

    @app.post('/v1/auth/login')
    def login(credentials: Credentials):
        with session(path) as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (credentials.email.strip().lower(),)).fetchone()
            salt = bytes.fromhex(user['salt']) if user else b'0'*16
            attempt = digest_password(credentials.password, salt)
            if not user or not hmac.compare_digest(attempt, user['password_hash']):
                raise HTTPException(401, detail='Invalid credentials')
            token = secrets.token_urlsafe(32)
            db.execute('INSERT INTO tokens(token_hash,user_id,expires_at) VALUES(?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user['id'], (utc_now()+timedelta(hours=2)).isoformat()))
        return {'access_token': token, 'token_type': 'bearer', 'role': user['role']}

    @app.post('/v1/auth/logout', status_code=204)
    def logout(authorization: Annotated[str | None, Header()] = None):
        if authorization and authorization.startswith('Bearer '):
            with session(path) as db:
                db.execute('DELETE FROM tokens WHERE token_hash=?', (hashlib.sha256(authorization[7:].encode()).hexdigest(),))
        return None

    @app.post('/v1/shipments', status_code=201)
    def create_shipment(payload: CreateShipment, user: dict = Depends(current_user)):
        operator_only(user)
        if len(payload.destination.strip()) < 8:
            raise HTTPException(422, detail='Destination too short')
        with session(path) as db:
            recipient = db.execute("SELECT id FROM users WHERE email=? AND role='CUSTOMER'", (payload.customer_email.strip().lower(),)).fetchone()
            if not recipient:
                raise HTTPException(422, detail='Unknown customer')
            now = utc_now().isoformat()
            cursor = db.execute('INSERT INTO shipments(customer_id,destination,service_level,status,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                                (recipient['id'], payload.destination.strip(), payload.service_level, 'CREATED', 0, now, now))
            row = db.execute('SELECT s.*,u.email FROM shipments s JOIN users u ON s.customer_id=u.id WHERE s.id=?',(cursor.lastrowid,)).fetchone()
        return to_shipment(row)

    @app.get('/v1/shipments')
    def list_shipments(
        status: Literal['CREATED','PICKED_UP','IN_TRANSIT','OUT_FOR_DELIVERY','DELIVERED'] | None = None,
        limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
        user: dict = Depends(current_user)
    ):
        filters, args = [], []
        if user['role'] == 'CUSTOMER':
            filters.append('s.customer_id=?');args.append(user['id'])
        if status:
            filters.append('s.status=?');args.append(status)
        where = (' WHERE '+' AND '.join(filters)) if filters else ''
        with session(path) as db:
            total = db.execute('SELECT COUNT(*) FROM shipments s'+where, args).fetchone()[0]
            rows = db.execute('SELECT s.*,u.email FROM shipments s JOIN users u ON s.customer_id=u.id'+where+' ORDER BY s.id DESC LIMIT ? OFFSET ?', args+[limit,offset]).fetchall()
        return {'items': [to_shipment(x) for x in rows], 'total': total, 'limit': limit, 'offset': offset}

    @app.get('/v1/shipments/{tracking_id}')
    def get_shipment(tracking_id: str, user: dict = Depends(current_user)):
        with session(path) as db:
            return to_shipment(find_shipment(db, tracking_id, user))

    @app.get('/v1/shipments/{tracking_id}/scans')
    def get_scans(tracking_id: str, user: dict = Depends(current_user)):
        with session(path) as db:
            shipment = find_shipment(db, tracking_id, user)
            rows = db.execute('SELECT event_id,new_status,occurred_at,expected_version FROM scans WHERE shipment_id=? ORDER BY id', (shipment['id'],)).fetchall()
        return {'items': [dict(x) for x in rows], 'total': len(rows)}

    @app.post('/v1/shipments/{tracking_id}/scans', status_code=201)
    def append_scan(tracking_id: str, payload: Scan, user: dict = Depends(current_user)):
        operator_only(user)
        if payload.occurred_at > utc_now() + timedelta(minutes=5):
            raise HTTPException(422, detail='Future scan timestamp')
        with session(path) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                shipment = find_shipment(db, tracking_id, user)
                existing = db.execute('SELECT * FROM scans WHERE event_id=?', (payload.event_id,)).fetchone()
                if existing:
                    same = (existing['shipment_id'] == shipment['id'] and existing['new_status']==payload.new_status and
                            existing['expected_version']==payload.expected_version and
                            existing['occurred_at']==payload.occurred_at.isoformat())
                    if not same:
                        raise HTTPException(409, detail='Event ID already used with different payload')
                    db.execute('COMMIT')
                    return {'event_id': payload.event_id, 'tracking_id': tracking_id, 'status': payload.new_status,
                            'version': payload.expected_version+1, 'replayed': True}
                if shipment['version'] != payload.expected_version:
                    raise HTTPException(409, detail='Stale shipment version')
                if NEXT.get(shipment['status']) != payload.new_status:
                    raise HTTPException(409, detail='Invalid status transition')
                last = db.execute('SELECT occurred_at FROM scans WHERE shipment_id=? ORDER BY id DESC LIMIT 1', (shipment['id'],)).fetchone()
                if last and payload.occurred_at < datetime.fromisoformat(last['occurred_at']):
                    raise HTTPException(409, detail='Out-of-order scan timestamp')
                now = utc_now().isoformat()
                db.execute('INSERT INTO scans(event_id,shipment_id,new_status,expected_version,occurred_at,created_at) VALUES(?,?,?,?,?,?)',
                           (payload.event_id, shipment['id'], payload.new_status, payload.expected_version, payload.occurred_at.isoformat(), now))
                db.execute('UPDATE shipments SET status=?,version=version+1,updated_at=? WHERE id=?',
                           (payload.new_status,now,shipment['id']))
                db.execute('COMMIT')
            except Exception:
                if db.in_transaction:
                    db.execute('ROLLBACK')
                raise
        return {'event_id': payload.event_id, 'tracking_id': tracking_id, 'status': payload.new_status,
                'version': payload.expected_version+1, 'replayed': False}

    return app


app = create_app()
