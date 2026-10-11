import os, json, sqlite3, shutil, secrets
from pathlib import Path
from sqlalchemy import select, text
from .database import Base, engine, Session, DATA
from .models import *
from .security import hash_password, token_hash, uid, utcnow

def initialize():
    from alembic.config import Config
    from alembic import command
    cfg=Config(str(Path(__file__).parent/'alembic.ini'))
    command.upgrade(cfg,'head')
    with Session() as db:
        if not db.get(User,'HEAD'):
            if os.getenv('APP_ENV')=='production':raise RuntimeError('Bootstrap users explicitly before starting production')
            credentials=[]
            for id,username,name,role in [('HEAD','head','Security Head','head'),('GUARD','guard','Gate Security','security'),
                ('MENON','warden.menon','Dr. R. Menon','warden'),('DEVI','warden.devi','Dr. S. Devi','warden'),('ADMIN','admin','System Administrator','admin')]:
                password=os.getenv('TEST_PASSWORD') or secrets.token_urlsafe(14)
                db.add(User(id=id,username=username,name=name,role=role,password_hash=hash_password(password)))
                credentials.append(username+' : '+password)
            db.flush()
            for hid,name in [('GAUTHAMA','Gauthama Bhavanam'),('MYTHREYI','Mythreyi Bhavanam'),('GARGI','Gargi Bhavanam')]:
                db.add(Hostel(id=hid,name=name))
            db.add(Gate(id='MAIN',name='Coimbatore Main Gate'));db.flush()
            for sid,name,branch,hid,wid in [('CB.CSE.DEMO01','Arjun Kumar','Computer Science','GAUTHAMA','MENON'),
                ('CB.ECE.DEMO02','Meera Nair','Electronics & Communication','MYTHREYI','DEVI'),
                ('CB.AI.DEMO03','Kavya Raman','Artificial Intelligence','GARGI','DEVI')]:
                db.add(Student(id=sid,name=name,branch=branch,hostel_id=hid,warden_id=wid,sample=True))
            db.commit()
            if not os.getenv('TEST_PASSWORD'):
                (DATA/'backend-demo-accounts.txt').write_text('LOCAL DEMO ACCOUNTS - do not deploy these accounts publicly\n'+'\n'.join(credentials))
        if os.getenv('IMPORT_LEGACY','1')=='1': migrate_legacy(db)
        for visit in db.scalars(select(Visit).where(Visit.status.in_(['inside','exit']))):
            if not db.get(VehicleOccupancy,visit.plate):
                db.add(VehicleOccupancy(plate=visit.plate,source_id=visit.id,entered_at=visit.entered_at or utcnow()))
        db.commit()

def migrate_legacy(db):
    original=DATA/'gate-state.sqlite3'
    if not original.exists() or db.get(Setting,'legacy_imported'):return
    backup=DATA/'backups';backup.mkdir(exist_ok=True)
    with sqlite3.connect(original) as src, sqlite3.connect(backup/'gate-state-before-normalization.sqlite3') as dest:
        src.backup(dest)
        row=src.execute('SELECT payload FROM state WHERE id=1').fetchone()
    if not row:return
    state=json.loads(row[0]);report={'visits':0,'skipped':[],'incidents':0,'logs':0}
    for old in state.get('visits',[]):
        try:
            student=db.get(Student,old['studentId'])
            if not student:
                warden=db.scalar(select(User).where(User.name==old.get('warden')))
                if not warden:raise ValueError('Unknown warden assignment')
                hostel=db.scalar(select(Hostel).where(Hostel.name==old.get('hostel')))
                if not hostel:
                    hostel=Hostel(id=uid('HOSTEL-'),name=old['hostel']);db.add(hostel);db.flush()
                student=Student(id=old['studentId'],name=old['student'],branch=old['branch'],hostel_id=hostel.id,warden_id=warden.id,sample=True)
                db.add(student);db.flush()
            status=old.get('status','pending')
            if status not in ['pending','approved','inside','exit','completed','rejected']:raise ValueError('Unknown lifecycle state')
            if db.get(Visit,old['id']):continue
            visit=Visit(id=old['id'],visitor_name=old['visitor'],phone=old.get('phone',''),relationship=old.get('relation','Other visitor'),
                vehicle_type=old.get('vehicleType','Car'),plate=old['plate'],student_id=student.id,purpose=old.get('purpose','Legacy visit'),
                visit_date=old['date'],status=status,tracking_hash=token_hash(secrets.token_urlsafe(32)),created_at=old.get('created',utcnow()),
                updated_at=utcnow(),entered_at=old.get('entered'),exited_at=old.get('exited'))
            db.add(visit);db.flush()
            for phase in (['entry','exit'] if status in ('exit','completed') else ['entry'] if status in ('approved','inside') else []):
                db.add(Approval(id=uid('APR-'),visit_id=visit.id,phase=phase,decision='approve',actor_id=None,note='Imported legacy approval; identity not authenticated',created_at=visit.created_at))
            if old.get('inspectionConfirmed'):
                db.add(Inspection(id=uid('INS-'),visit_id=visit.id,guard_id=None,passed=True,note='Imported legacy confirmation',confirmed_at=old.get('inspectionConfirmedAt',utcnow())))
            for direction,value in [('entry',visit.entered_at),('exit',visit.exited_at)]:
                if value:db.add(GateEvent(id=uid('EVT-'),visit_id=visit.id,gate_id='MAIN',guard_id=None,direction=direction,recorded_at=value,original_plate=''))
            report['visits']+=1
        except (KeyError,ValueError) as exc:report['skipped'].append({'id':old.get('id'),'reason':str(exc)})
    db.flush()
    for old in state.get('logs',[]):
        if not db.get(Visit,old.get('visit')):continue
        db.add(AuditLog(id=uid('LOG-'),visit_id=old['visit'],actor_id=None,actor_name='Legacy: '+old.get('actor','unknown'),
            action=old.get('action','Legacy event'),note=old.get('note',''),created_at=old.get('time',utcnow())));report['logs']+=1
    for old in state.get('incidents',[]):
        if old.get('source')=='sample' or not db.get(Visit,old.get('visit')):continue
        item=Incident(id=old['id'],visit_id=old['visit'],title=old.get('title','Legacy concern'),priority=old.get('priority','Normal'),
            owner_role=old.get('owner','security'),status=old.get('status','open'),note=old.get('note',''),outcome=old.get('outcome',''),created_at=old.get('created',utcnow()))
        db.add(item);db.flush()
        for action in old.get('timeline',[]):db.add(IncidentAction(id=uid('ACT-'),incident_id=item.id,actor_id=None,action=action['action'],note=action.get('note',''),created_at=action['time']))
        report['incidents']+=1
    db.add(Setting(key='legacy_imported',value=json.dumps(report)));db.commit()
    (DATA/'legacy-migration-report.json').write_text(json.dumps(report,indent=2))
