import pytest

def test_requires_bearer(client):
    assert client.get('/v1/shipments').status_code==401
    assert client.get('/v1/shipments',headers={'Authorization':'Bearer invalid'}).status_code==401

def test_bad_password(client):
    r=client.post('/v1/auth/login',json={'email':'ana@parcelguard.local','password':'wrong'})
    assert r.status_code==401 and r.json()['detail']=='Invalid credentials'

def test_customer_cannot_create_shipment(client,headers):
    r=client.post('/v1/shipments',headers=headers['ana'],json={'customer_email':'ana@parcelguard.local','destination':'Endereço Rua X, Recife'})
    assert r.status_code==403

def test_customer_cannot_scan(client,headers,shipment,event):
    r=client.post('/v1/shipments/'+shipment['tracking_id']+'/scans',headers=headers['ana'],json=event())
    assert r.status_code==403

def test_other_customer_cannot_see_shipment(client,headers,shipment):
    tracking=shipment['tracking_id']
    assert client.get('/v1/shipments/'+tracking,headers=headers['bruno']).status_code==404
    assert client.get('/v1/shipments/'+tracking+'/scans',headers=headers['bruno']).status_code==404
    assert client.get('/v1/shipments',headers=headers['bruno']).json()['total']==0
    assert client.get('/v1/shipments',headers=headers['ana']).json()['total']==1

def test_logout_revokes_token(client,headers):
    auth=headers['ana']
    assert client.post('/v1/auth/logout',headers=auth).status_code==204
    assert client.get('/v1/shipments',headers=auth).status_code==401

def test_cannot_access_unknown_tracking(client,headers):
    for invalid in ['PG-999999','oops','PG-abcdef']:
        assert client.get('/v1/shipments/'+invalid,headers=headers['operator']).status_code==404

def test_strict_request_rejects_extra_fields(client,headers):
    r=client.post('/v1/shipments',headers=headers['operator'],json={
     'customer_email':'ana@parcelguard.local','destination':'Av Teste, Recife','service_level':'EXPRESS','is_admin':True})
    assert r.status_code==422
