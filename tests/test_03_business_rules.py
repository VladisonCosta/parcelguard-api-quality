import pytest

def scan(client,headers,tracking,data):
    return client.post('/v1/shipments/'+tracking+'/scans',headers=headers['operator'],json=data)

@pytest.mark.parametrize('payload',[
 {'customer_email':'unknown@parcelguard.local','destination':'Endereço fictício em Recife'},
 {'customer_email':'ana@parcelguard.local','destination':'curto'},
 {'customer_email':'ana@parcelguard.local','destination':'Endereço fictício em Recife','service_level':'INVALID'},
])
def test_invalid_shipment_rejected(client,headers,payload):
    assert client.post('/v1/shipments',headers=headers['operator'],json=payload).status_code==422

def test_full_happy_path(client,headers,shipment,event):
    tracking=shipment['tracking_id']
    for i,status in enumerate(['PICKED_UP','IN_TRANSIT','OUT_FOR_DELIVERY','DELIVERED']):
        r=scan(client,headers,tracking,event(event_id=f'EVT-{10000+i}',status=status,version=i,delta_minutes=i+1))
        assert r.status_code==201, r.text
        assert r.json()['version']==i+1
    detail=client.get('/v1/shipments/'+tracking,headers=headers['ana']).json()
    assert detail['status']=='DELIVERED' and detail['version']==4
    history=client.get('/v1/shipments/'+tracking+'/scans',headers=headers['ana']).json()
    assert [e['new_status'] for e in history['items']]==['PICKED_UP','IN_TRANSIT','OUT_FOR_DELIVERY','DELIVERED']

def test_reject_illegal_transition(client,headers,shipment,event):
    r=scan(client,headers,shipment['tracking_id'],event(status='DELIVERED'))
    assert r.status_code==409 and 'transition' in r.json()['detail']

def test_reject_stale_version(client,headers,shipment,event):
    tracking=shipment['tracking_id']
    assert scan(client,headers,tracking,event()).status_code==201
    r=scan(client,headers,tracking,event('EVT-10002','IN_TRANSIT',0,2))
    assert r.status_code==409 and 'Stale' in r.json()['detail']

def test_no_next_state_after_delivery(client,headers,shipment,event):
    tracking=shipment['tracking_id']
    for i,status in enumerate(['PICKED_UP','IN_TRANSIT','OUT_FOR_DELIVERY','DELIVERED']):
        assert scan(client,headers,tracking,event(f'EVT-{10000+i}',status,i,i)).status_code==201
    assert scan(client,headers,tracking,event('EVT-20000','PICKED_UP',4,7)).status_code==409

def test_invalid_timestamp(client,headers,shipment,event):
    payload=event()
    payload['occurred_at']='2026-10-19T09:00:00' # no timezone
    assert scan(client,headers,shipment['tracking_id'],payload).status_code==422

def test_future_timestamp(client,headers,shipment,event):
    from datetime import datetime,timedelta,timezone
    payload=event()
    payload['occurred_at']=(datetime.now(timezone.utc)+timedelta(hours=3)).isoformat()
    assert scan(client,headers,shipment['tracking_id'],payload).status_code==422

def test_out_of_order_timestamp(client,headers,shipment,event):
    tracking=shipment['tracking_id']
    assert scan(client,headers,tracking,event('EVT-10001','PICKED_UP',0,30)).status_code==201
    result=scan(client,headers,tracking,event('EVT-10002','IN_TRANSIT',1,2))
    assert result.status_code==409 and 'Out-of-order' in result.json()['detail']

def test_idempotent_replay(client,headers,shipment,event):
    tracking=shipment['tracking_id']
    payload=event()
    a=scan(client,headers,tracking,payload)
    b=scan(client,headers,tracking,payload)
    assert (a.status_code,b.status_code)==(201,201)
    assert a.json()['replayed'] is False
    assert b.json()['replayed'] is True
    assert client.get('/v1/shipments/'+tracking,headers=headers['operator']).json()['version']==1
    assert client.get('/v1/shipments/'+tracking+'/scans',headers=headers['operator']).json()['total']==1

def test_duplicate_event_different_payload_conflict(client,headers,shipment,event):
    tracking=shipment['tracking_id']
    assert scan(client,headers,tracking,event()).status_code==201
    assert scan(client,headers,tracking,event(status='IN_TRANSIT',version=1,delta_minutes=2)).status_code==409

def test_list_filter_and_pagination(client,headers,shipment):
    body={'customer_email':'bruno@parcelguard.local','destination':'Porto Alegre, Rio Grande do Sul'}
    for _ in range(3):
        assert client.post('/v1/shipments',headers=headers['operator'],json=body).status_code==201
    page=client.get('/v1/shipments?limit=2&offset=1&status=CREATED',headers=headers['operator'])
    assert page.status_code==200
    assert page.json()['total']==4 and len(page.json()['items'])==2
    assert client.get('/v1/shipments?limit=101',headers=headers['operator']).status_code==422
    assert client.get('/v1/shipments?offset=-1',headers=headers['operator']).status_code==422
