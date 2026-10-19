from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(tmp_path: Path):
    with TestClient(create_app(tmp_path / 'parcelguard.sqlite3')) as c:
        yield c

@pytest.fixture
def tokens(client):
    return {email.split('@')[0]: client.post('/v1/auth/login',json={'email':email,'password':'demo1234'}).json()['access_token']
      for email in ('operator@parcelguard.local','ana@parcelguard.local','bruno@parcelguard.local')}

@pytest.fixture
def headers(tokens):
    return {who: {'Authorization':'Bearer '+token} for who,token in tokens.items()}

@pytest.fixture
def shipment(client, headers):
    response = client.post('/v1/shipments',headers=headers['operator'],json={'customer_email':'ana@parcelguard.local','destination':'Recife, Pernambuco - Bairro Boa Vista','service_level':'EXPRESS'})
    assert response.status_code == 201, response.text
    return response.json()

@pytest.fixture
def event():
    def make(event_id='EVT-10001', status='PICKED_UP', version=0, delta_minutes=0):
        occurred=(datetime.now(timezone.utc)-timedelta(hours=1)+timedelta(minutes=delta_minutes)).isoformat()
        return {'event_id':event_id,'new_status':status,'expected_version':version,'occurred_at':occurred}
    return make
