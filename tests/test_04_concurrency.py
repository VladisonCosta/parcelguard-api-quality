from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta

def test_parallel_scans_only_one_wins(client,headers,shipment):
    tracking=shipment['tracking_id']
    time=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
    def try_scan(seq):
        return client.post('/v1/shipments/'+tracking+'/scans',headers=headers['operator'],json={
         'event_id':f'RACE-{seq:04d}','new_status':'PICKED_UP','expected_version':0,'occurred_at':time})
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(try_scan,range(6)))
    assert sorted(x.status_code for x in results)==[201,409,409,409,409,409]
    assert client.get('/v1/shipments/'+tracking,headers=headers['operator']).json()['version']==1
    assert client.get('/v1/shipments/'+tracking+'/scans',headers=headers['operator']).json()['total']==1
