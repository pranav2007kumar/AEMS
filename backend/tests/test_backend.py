import os, tempfile
from pathlib import Path
test_dir=Path(tempfile.mkdtemp(prefix='campus-api-tests-'))
os.environ['DATABASE_URL']='sqlite:///'+(test_dir/'test.sqlite3').as_posix()
os.environ['TEST_PASSWORD']='TestPassword-Only-2026'
os.environ['IMPORT_LEGACY']='0'
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Session
from backend.models import Visit, Approval, Inspection, GateEvent, AuditLog
from backend.services import today
from sqlalchemy import select
import pytest

@pytest.fixture(scope='module')
def clients():
    with TestClient(app) as owner:
        result={'anon':owner}
        for name,username in [('warden','warden.menon'),('other','warden.devi'),('guard','guard'),('head','head')]:
            c=TestClient(app);c.headers['Origin']='http://testserver'
            assert c.post('/api/v1/auth/login',json={'username':username,'password':os.environ['TEST_PASSWORD']}).status_code==200
            result[name]=c
        yield result

def create(clients,plate='TN38AB1234'):
    r=clients['anon'].post('/api/v1/visits',json={'visitor':'Sample Parent','phone':'9000000001','relation':'Parent',
        'plate':plate,'studentId':'CB.CSE.DEMO01','purpose':'Meet student','date':today(),'vehicleType':'Car'})
    assert r.status_code==201,r.text
    return r.json()

def test_authorization_tracking_and_duplicate(clients):
    value=create(clients);vid=value['visit']['id']
    assert clients['anon'].get('/api/v1/state').status_code==401
    assert clients['anon'].get('/api/v1/public/visits/'+vid).status_code==404
    assert clients['anon'].get('/api/v1/public/visits/'+vid,headers={'X-Visit-Token':value['tracking_token']}).status_code==200
    assert clients['other'].get('/api/v1/visits/'+vid).status_code==403
    assert clients['guard'].post('/api/v1/visits/'+vid+'/entry-approval',json={'version':1}).status_code==403
    assert clients['other'].post('/api/v1/visits/'+vid+'/entry-approval',json={'version':1}).status_code==403
    assert clients['anon'].post('/api/state',json={}).status_code==410
    assert clients['anon'].post('/api/v1/visits',json={'visitor':'Sample Parent','phone':'9000000001','relation':'Parent',
        'plate':'TN 38 AB 1234','studentId':'CB.CSE.DEMO01','purpose':'Duplicate','date':today()}).status_code==409

def test_full_flow_enforced_on_server(clients):
    result=create(clients,'TN38AB1235');v=result['visit'];url='/api/v1/visits/'+v['id']
    def post(who,path,body):return clients[who].post(url+path,json=body)
    p={'version':v['version'],'plate':v['plate'],'person_count':2,'visitor_verified':True}
    assert post('guard','/entry',p).status_code==409
    approved=post('warden','/entry-approval',{'version':v['version']});assert approved.status_code==200,approved.text;v=approved.json()
    assert post('warden','/entry-approval',{'version':1}).status_code==409
    p['version']=v['version'];assert post('guard','/entry',p).status_code==409
    failed=post('guard','/inspection',{'version':v['version'],'passed':False,'note':'Needs verification'});assert failed.status_code==200;v=failed.json()
    p['version']=v['version'];assert post('guard','/entry',p).status_code==409
    passed=post('guard','/inspection',{'version':v['version'],'passed':True});assert passed.status_code==200;v=passed.json()
    p['version']=v['version'];p['visitor_verified']=False;assert post('guard','/entry',p).status_code==409
    p['visitor_verified']=True;p['plate']='TN38WRONG';assert post('guard','/entry',p).status_code==409
    p['plate']=v['plate'];entered=post('guard','/entry',p);assert entered.status_code==200,entered.text;v=entered.json();assert v['status']=='inside'
    p['version']=v['version'];assert post('guard','/entry',p).status_code==409
    assert post('guard','/exit',p).status_code==409
    assert post('warden','/exit-approval',{'version':v['version']}).status_code==409
    cleared=post('warden','/exit-approval',{'version':v['version'],'meeting_verified':True});assert cleared.status_code==200;v=cleared.json()
    p['version']=v['version'];p['person_count']=3;assert post('guard','/exit',p).status_code==409;assert clients['head'].get(url).json()['status']=='exit';p['person_count']=2;exited=post('guard','/exit',p);assert exited.status_code==200,exited.text;assert exited.json()['status']=='completed';assert exited.json()['entry_person_count']==exited.json()['exit_person_count']==2
    with Session() as db:
        assert len(db.scalars(select(Approval).where(Approval.visit_id==v['id'])).all())==2
        assert len(db.scalars(select(Inspection).where(Inspection.visit_id==v['id'])).all())==2
        assert len(db.scalars(select(GateEvent).where(GateEvent.visit_id==v['id'])).all())==2
        assert len(db.scalars(select(AuditLog).where(AuditLog.visit_id==v['id'])).all())==7

def test_incident_assignment_and_settings(clients):
    v=create(clients,'TN38AB1236')['visit']
    body={'visit_id':v['id'],'title':'Verify visit purpose','owner':'security','note':'Check the arrival documents'}
    assert clients['guard'].post('/api/v1/incidents',json=body).status_code==403
    r=clients['head'].post('/api/v1/incidents',json=body);assert r.status_code==201,r.text;i=r.json()
    action={'version':i['version'],'action':'investigate','outcome':'Further verification requested','note':'Guard acknowledged'}
    assert clients['warden'].post('/api/v1/incidents/'+i['id']+'/actions',json=action).status_code==403
    r=clients['guard'].post('/api/v1/incidents/'+i['id']+'/actions',json=action);assert r.status_code==200
    action.update(version=r.json()['version'],action='resolve',outcome='No issue found')
    assert clients['guard'].post('/api/v1/incidents/'+i['id']+'/actions',json=action).status_code==200
    assert clients['head'].get('/api/v1/visits/'+v['id']).json()['status']=='pending'
    values={'waiting':8,'lanes':2,'seconds':150,'dwell':240}
    assert clients['guard'].patch('/api/v1/settings',json=values).status_code==403
    assert clients['head'].patch('/api/v1/settings',json=values).status_code==200
    assert clients['head'].get('/api/v1/analytics/summary').json()['queue']['clearance_minutes']==10

def test_logout_and_origin(clients):
    assert clients['guard'].post('/api/v1/settings',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert clients['other'].post('/api/v1/auth/logout',json={}).status_code==200
    assert clients['other'].get('/api/v1/auth/me').status_code==401

def test_ai_uses_server_records_not_client_facts(clients,monkeypatch):
    from backend import ai
    seen={}
    async def inference(kind,body):
        seen.update(body)
        return {'reply':'The authorized records are available.','ai':{'provider':'test'}} if kind=='chat' else {'ids':[f['id'] for f in body['facts']]}
    monkeypatch.setattr(ai,'infer',inference)
    body={'messages':[{'role':'user','content':'How many visits?'}],'context':{'facts':[{'id':'fake','text':'99999 invented entries'}]}}
    r=clients['head'].post('/api/v1/ai/chat',json=body);assert r.status_code==200,r.text
    assert '99999' not in str(seen)
    assert clients['guard'].post('/api/v1/ai/chat',json=body).status_code==403
    assert clients['head'].post('/api/v1/ai/summary',json={}).status_code==200

def test_registered_access_roles_inspection_and_history(clients):
    body={'plate':'TN 38 RG 1001','owner_name':'Demo Faculty','category':'Faculty','purpose':'Daily teaching duties','valid_until':'2099-12-31'}
    assert clients['guard'].post('/api/v1/registered-vehicles',json=body).status_code==403
    assert clients['anon'].get('/api/v1/registered-vehicles').status_code==401
    response=clients['head'].post('/api/v1/registered-vehicles',json=body)
    assert response.status_code==201,response.text
    r=response.json();assert r['plate']=='TN38RG1001' and r['eligible']
    assert clients['head'].post('/api/v1/registered-vehicles',json=body).status_code==409
    guard=clients['guard'];url='/api/v1/registered-vehicles/'+r['id']+'/entry'
    entry={'version':r['version'],'plate':r['plate'],'person_count':2,'visitor_verified':True,'inspection_completed':False}
    assert guard.post(url,json=entry).status_code==409
    entry['inspection_completed']=True
    p=guard.post(url,json=entry);assert p.status_code==200,p.text;p=p.json()
    assert p['status']=='inside' and p['access_type']=='registered'
    fresh=guard.get('/api/v1/registered-vehicles/lookup/TN38RG1001').json()
    assert fresh['inside']['id']==p['id']
    entry['version']=fresh['vehicle']['version'];assert guard.post(url,json=entry).status_code==409
    assert clients['head'].get('/api/v1/analytics/summary').json()['inside']>=1
    assert any(x['id']==p['id'] for x in clients['head'].get('/api/v1/state').json()['state']['visits'])
    exitbody={'version':p['version'],'plate':r['plate'],'person_count':2,'visitor_verified':True}
    exitbody['person_count']=3;assert guard.post('/api/v1/registered-passages/'+p['id']+'/exit',json=exitbody).status_code==409
    assert guard.get('/api/v1/registered-vehicles/lookup/'+r['plate']).json()['inside']['entry_person_count']==2
    exitbody['person_count']=2
    assert guard.post('/api/v1/registered-passages/'+p['id']+'/exit',json=exitbody).json()['exit_person_count']==2
    assert guard.post('/api/v1/registered-passages/'+p['id']+'/exit',json=exitbody).status_code==409
    logs=clients['head'].get('/api/v1/audit-logs').json()['items']
    assert any(x['action']=='Registered vehicle departed' and x['plate']==r['plate'] for x in logs)

def test_registered_suspension_expiry_and_cross_workflow(clients):
    body={'plate':'TN38RG1002','owner_name':'Demo Staff','category':'Staff','purpose':'Daily office access','valid_until':'2099-12-31'}
    r=clients['head'].post('/api/v1/registered-vehicles',json=body).json();url='/api/v1/registered-vehicles/'+r['id']
    suspended=clients['head'].patch(url,json={'version':r['version'],'active':False}).json()
    entry={'version':suspended['version'],'plate':r['plate'],'person_count':2,'visitor_verified':True,'inspection_completed':True}
    assert clients['guard'].post(url+'/entry',json=entry).status_code==409
    active=clients['head'].patch(url,json={'version':suspended['version'],'active':True}).json()
    entry['version']=active['version'];p=clients['guard'].post(url+'/entry',json=entry).json()
    v=create(clients,r['plate'])['visit'];vurl='/api/v1/visits/'+v['id']
    v=clients['warden'].post(vurl+'/entry-approval',json={'version':v['version']}).json()
    v=clients['guard'].post(vurl+'/inspection',json={'version':v['version'],'passed':True}).json()
    assert clients['guard'].post(vurl+'/entry',json={'version':v['version'],'plate':r['plate'],'person_count':2,'visitor_verified':True}).status_code==409
    clients['guard'].post('/api/v1/registered-passages/'+p['id']+'/exit',json={'version':p['version'],'plate':r['plate'],'person_count':2,'visitor_verified':True})
    entered=clients['guard'].post(vurl+'/entry',json={'version':v['version'],'plate':r['plate'],'person_count':2,'visitor_verified':True});assert entered.status_code==200,entered.text
    fresh=clients['guard'].get('/api/v1/registered-vehicles/lookup/'+r['plate']).json()['vehicle']
    entry['version']=fresh['version'];assert clients['guard'].post(url+'/entry',json=entry).status_code==409
    from backend.registry import RegisteredVehicle
    with Session() as db:
        row=db.get(RegisteredVehicle,r['id']);row.valid_until='2020-01-01';db.commit()
    assert not clients['guard'].get('/api/v1/registered-vehicles/lookup/'+r['plate']).json()['vehicle']['eligible']
    body.update(plate='TN38RG1003',valid_until='2020-01-01')
    assert clients['head'].post('/api/v1/registered-vehicles',json=body).status_code==422

def test_tailgating_alert_blocks_additional_entry_until_resolved(clients):
    guard=clients['guard'];head=clients['head']
    cycles=guard.get('/api/v1/barrier-cycles').json()
    assert cycles['hardware_connected'] is False
    c=next(x for x in cycles['items'] if x['status']=='awaiting_count')
    url='/api/v1/barrier-cycles/'+c['id']
    assert head.post(url+'/count',json={'version':c['version'],'detected_count':2}).status_code==403
    r=guard.post(url+'/count',json={'version':c['version'],'detected_count':2});assert r.status_code==200,r.text;c=r.json()
    assert c['status']=='alert' and c['authorized_count']==1
    assert guard.post(url+'/count',json={'version':c['version'],'detected_count':1}).status_code==409
    body={'plate':'TN38RG2001','owner_name':'Demo Faculty Two','category':'Faculty','purpose':'Teaching duties','valid_until':'2099-12-31'}
    registered=head.post('/api/v1/registered-vehicles',json=body).json()
    entry={'version':registered['version'],'plate':registered['plate'],'person_count':2,'visitor_verified':True,'inspection_completed':True}
    assert guard.post('/api/v1/registered-vehicles/'+registered['id']+'/entry',json=entry).status_code==409
    assert guard.post(url+'/resolve',json={'version':c['version'],'note':'Checked second vehicle; guard recorded a separate authorization.'}).status_code==200
    assert guard.post('/api/v1/registered-vehicles/'+registered['id']+'/entry',json=entry).status_code==200

def test_anpr_output_only_ingestion(clients):
    from backend.security import utcnow
    body={'detection_id':'TEST-OUTPUT-ONLY-0001','plate':'TN 38 AB 1234','confidence':0.94,'direction':'entry','gate_id':'MAIN','captured_at':utcnow()}
    assert clients['anon'].post('/api/v1/anpr/detections',json=body).status_code==401
    assert clients['head'].post('/api/v1/anpr/detections',json=body).status_code==403
    r=clients['guard'].post('/api/v1/anpr/detections',json=body);assert r.status_code==201,r.text
    assert r.json()['detection']['plate']=='TN38AB1234'
    assert r.json()['review_required'] and r.json()['inspection_required']
    assert clients['guard'].post('/api/v1/anpr/detections',json=body).status_code==409
    assert any(x['id']==body['detection_id'] for x in clients['head'].get('/api/v1/anpr/detections').json()['items'])
    # Test payload only: no torch import, model load, camera or inference.
    body.update(detection_id='TEST-OUTPUT-ONLY-0002',confidence=1.4)
    assert clients['guard'].post('/api/v1/anpr/detections',json=body).status_code==422

def test_monitoring_policy_enforced_and_exit_stays_available(clients):
    head=clients['head'];guard=clients['guard']
    assert guard.get('/api/v1/monitoring/overview').status_code==403
    info=head.get('/api/v1/monitoring/overview');assert info.status_code==200,info.text
    info=info.json();assert info['registry']['total']>=3
    p=info['policy'];assert p['capacity']==200
    changed={**{k:p[k] for k in ['mode','capacity','min_confidence','version']},'mode':'lockdown'}
    assert guard.patch('/api/v1/access-policy',json=changed).status_code==403
    r=head.patch('/api/v1/access-policy',json=changed);assert r.status_code==200,r.text
    assert head.patch('/api/v1/access-policy',json=changed).status_code==409
    body={'plate':'TN38RG3001','owner_name':'Policy Test Faculty','category':'Faculty','purpose':'Policy checks','valid_until':'2099-12-31'}
    reg=head.post('/api/v1/registered-vehicles',json=body).json();entry={'version':reg['version'],'plate':reg['plate'],'person_count':2,'visitor_verified':True,'inspection_completed':True}
    assert guard.post('/api/v1/registered-vehicles/'+reg['id']+'/entry',json=entry).status_code==409
    p=head.get('/api/v1/access-policy').json();changed.update(version=p['version'],mode='normal',capacity=1)
    assert head.patch('/api/v1/access-policy',json=changed).status_code==200
    assert guard.post('/api/v1/registered-vehicles/'+reg['id']+'/entry',json=entry).status_code==409
    p=head.get('/api/v1/access-policy').json();changed.update(version=p['version'],capacity=200)
    assert head.patch('/api/v1/access-policy',json=changed).status_code==200
    entered=guard.post('/api/v1/registered-vehicles/'+reg['id']+'/entry',json=entry);assert entered.status_code==200,entered.text
    passage=entered.json();p=head.get('/api/v1/access-policy').json();changed.update(version=p['version'],mode='lockdown')
    assert head.patch('/api/v1/access-policy',json=changed).status_code==200
    departed=guard.post('/api/v1/registered-passages/'+passage['id']+'/exit',json={'plate':reg['plate'],'person_count':2,'visitor_verified':True,'version':passage['version']})
    assert departed.status_code==200,departed.text
    p=head.get('/api/v1/access-policy').json();changed.update(version=p['version'],mode='normal');head.patch('/api/v1/access-policy',json=changed)

def test_recognition_raw_history_review_and_rule_reasons(clients):
    from backend.security import utcnow
    guard=clients['guard'];head=clients['head']
    body={'detection_id':'TEST-LOW-SCORE-001','plate':'IND TN 38 RG 3001','confidence':0.62,'direction':'entry','captured_at':utcnow()}
    r=guard.post('/api/v1/anpr/detections',json=body);assert r.status_code==201,r.text
    read=r.json()['detection'];assert read['plate_raw']==body['plate'] and read['plate']=='TN38RG3001'
    assert read['decision']=='HOLD' and read['reason_code']=='HOLD_LOW_CONFIDENCE'
    overview=head.get('/api/v1/monitoring/overview').json();assert any(x['id']==read['id'] for x in overview['review_queue'])
    reviewed=head.post('/api/v1/anpr/detections/'+read['id']+'/review',json={'version':read['version'],'verified_plate':'TN 38 RG 3001','note':'Verified visible plate against registration.'})
    assert reviewed.status_code==200,reviewed.text
    reviewed=reviewed.json();assert reviewed['status']=='resolved' and reviewed['plate_raw']==body['plate']
    assert reviewed['original_decision']=='HOLD' and reviewed['current_permission']['decision']=='ALLOW'
    assert head.post('/api/v1/anpr/detections/'+read['id']+'/review',json={'version':read['version'],'verified_plate':read['plate'],'note':'Duplicate review'}).status_code==409
    body.update(detection_id='TEST-INVALID-RAW-001',plate='not a plate',confidence=0.99)
    r=guard.post('/api/v1/anpr/detections',json=body);assert r.status_code==201,r.text
    assert r.json()['detection']['reason_code']=='HOLD_UNKNOWN_FORMAT'
    body.update(detection_id='TEST-ORPHAN-EXIT-001',plate='TN38XY9900',direction='exit')
    assert guard.post('/api/v1/anpr/detections',json=body).json()['detection']['reason_code']=='EXIT_ORPHAN'

def test_loopback_shared_demo_login_preserves_roles(clients,monkeypatch):
    from backend.main import limits
    limits.clear()
    monkeypatch.setenv('LOCAL_DEMO_LOGIN','1')
    with TestClient(app) as c:
        c.headers['Origin']='http://testserver'
        for portal,uid in [('security','GUARD'),('head','HEAD'),('warden','MENON'),('admin','ADMIN'),('registry','HEAD')]:
            r=c.post('/api/v1/auth/login',json={'username':'1234','password':'1234','portal':portal})
            assert r.status_code==200,r.text
            assert r.json()['user']['id']==uid
        r=c.post('/api/v1/auth/login',json={'username':'1234','password':'1234','portal':'warden','warden_id':'DEVI'})
        assert r.json()['user']['id']=='DEVI'
        assert c.post('/api/v1/auth/login',json={'username':'1234','password':'wrong','portal':'head'}).status_code==401
        assert c.post('/api/v1/auth/login',json={'username':'guard','password':'1234','portal':'security'}).json()['user']['id']=='GUARD'
        assert c.post('/api/v1/auth/login',json={'username':'1234','password':'1234'}).status_code==409
        monkeypatch.setenv('APP_ENV','production')
        assert c.post('/api/v1/auth/login',json={'username':'1234','password':'1234','portal':'head'}).status_code==401

def test_camera_frame_bridge_without_executing_model(clients,monkeypatch):
    import base64,io
    from PIL import Image
    from backend import camera
    monkeypatch.delenv('ANPR_ENABLE_INFERENCE',raising=False)
    assert clients['guard'].get('/api/v1/anpr/camera-status').json()['enabled'] is False
    assert clients['anon'].get('/api/v1/anpr/camera-status').status_code==401
    image=io.BytesIO();Image.new('RGB',(64,32)).save(image,format='JPEG')
    body={'image':base64.b64encode(image.getvalue()).decode(),'direction':'entry'}
    assert clients['guard'].post('/api/v1/anpr/frames',json=body).status_code==503
    assert clients['head'].post('/api/v1/anpr/frames',json=body).status_code==403
    monkeypatch.setattr(camera,'status',lambda:{'ready':True})
    # Deliberately mock recognition: never import torch or open the supplied model.
    monkeypatch.setattr(camera,'recognize',lambda image:[{'plate':'TN38RG3001','confidence':.98,'box':[0,0,32,16]}])
    result=clients['guard'].post('/api/v1/anpr/frames',json=body)
    assert result.status_code==200,result.text
    assert result.json()['detection']['plate']=='TN38RG3001'
    assert result.json()['inspection_required'] is True
    assert clients['guard'].get('/api/v1/registered-vehicles/lookup/TN38RG3001').json()['inside'] is None
    monkeypatch.setattr(camera,'recognize',lambda image:[])
    assert clients['guard'].post('/api/v1/anpr/frames',json=body).json()['detection'] is None
    body['image']='not-an-image'*10
    assert clients['guard'].post('/api/v1/anpr/frames',json=body).status_code==422


def test_parent_warden_security_share_request_and_approval_history(clients):
    created=create(clients,'TN38ZZ8624');v=created['visit'];vid=v['id'];url='/api/v1/visits/'+vid
    def shared(client):
        return next(row for row in client.get('/api/v1/state').json()['state']['visits'] if row['id']==vid)
    assert shared(clients['warden'])['status']=='pending'
    assert shared(clients['guard'])['plate']==v['plate']
    assert shared(clients['warden'])['entryApproval'] is None
    r=clients['warden'].post(url+'/entry-approval',json={'version':v['version']})
    assert r.status_code==200,r.text
    approved=r.json()
    assert approved['id']==vid and approved['entryApproval']['decision']=='approve'
    tracked=clients['anon'].get('/api/v1/public/visits/'+vid,headers={'X-Visit-Token':created['tracking_token']}).json()
    guard=clients['guard'].get(url).json()
    assert tracked['status']==guard['status']==shared(clients['warden'])['status']=='approved'
    assert tracked['entryApproval']==guard['entryApproval']==approved['entryApproval']
    logs=clients['warden'].get('/api/v1/state').json()['state']['logs']
    assert {row['action'] for row in logs if row['visit']==vid}=={'Request submitted','Entry approved'}
    assert all(row['plate']==v['plate'] for row in logs if row['visit']==vid)
