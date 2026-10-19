import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / 'contracts'

def check_schema(name, payload):
    schema=json.loads((SCHEMAS / name).read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(payload)

def test_health_contract(client):
    response=client.get('/health')
    assert response.status_code==200
    assert response.json()=={'status':'ok','service':'parcelguard','api_version':'v1'}

def test_openapi_documentation(client):
    doc=client.get('/openapi.json').json()
    assert doc['info']['title']=='ParcelGuard QA | Logistics API'
    assert '/v1/shipments/{tracking_id}/scans' in doc['paths']

def test_shipment_contract_on_create(client,headers,shipment):
    check_schema('shipment.v1.schema.json',shipment)
    assert shipment['status']=='CREATED' and shipment['version']==0
    response=client.get('/v1/shipments/'+shipment['tracking_id'],headers=headers['ana'])
    check_schema('shipment.v1.schema.json',response.json())

def test_scan_contract(client,headers,shipment,event):
    result=client.post(f"/v1/shipments/{shipment['tracking_id']}/scans",headers=headers['operator'],json=event())
    assert result.status_code==201, result.text
    check_schema('scan-result.v1.schema.json',result.json())

def test_response_collection_shape(client,headers,shipment):
    collection=client.get('/v1/shipments?limit=5',headers=headers['operator']).json()
    assert set(collection)=={'items','total','limit','offset'}
    assert collection['total']==1 and collection['offset']==0
    for entry in collection['items']:check_schema('shipment.v1.schema.json',entry)

def test_schema_fails_for_unexpected_field(shipment):
    with pytest.raises(Exception):
        check_schema('shipment.v1.schema.json',{**shipment,'password':'leak'})
