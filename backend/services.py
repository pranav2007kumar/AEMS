import json, re, math
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select
from .models import *
from .security import uid, utcnow, require

IST = ZoneInfo('Asia/Kolkata')
def today(): return datetime.now(IST).date().isoformat()
def normalized(value): return re.sub(r'[^A-Z0-9]', '', value.upper())

def accessible(db, user):
    query = select(Visit)
    if user.role == 'warden':
        query = query.join(Student).where(Student.warden_id == user.id)
    return db.scalars(query.order_by(Visit.created_at.desc())).all()

def visit_for(db, user, vid, version=None):
    visit = db.get(Visit, vid)
    if not visit: raise HTTPException(404, 'Visit not found')
    student = db.get(Student, visit.student_id)
    if user.role == 'warden' and student.warden_id != user.id:
        raise HTTPException(403, 'This student is assigned to another warden')
    if version is not None and visit.version != version:
        raise HTTPException(409, 'Visit changed. Refresh and repeat your action.')
    return visit

def audit(db, user, action, visit=None, note=''):
    db.add(AuditLog(id=uid('LOG-'), visit_id=visit.id if visit else None,
        actor_id=user.id if user else None, actor_name=user.name if user else 'Visitor',
        action=action, note=note, created_at=utcnow()))

def bump(visit): visit.updated_at = utcnow()

def student_view(db, student):
    return {'studentId':student.id, 'student':student.name, 'branch':student.branch,
        'hostel':db.get(Hostel, student.hostel_id).name,
        'warden':db.get(User, student.warden_id).name, 'sample':student.sample}

def visit_view(db, visit, user=None):
    result = student_view(db, db.get(Student, visit.student_id))
    inspection = db.scalar(select(Inspection).where(Inspection.visit_id == visit.id).order_by(Inspection.confirmed_at.desc()).limit(1))
    phone = visit.phone
    if user and user.role == 'security': phone = '******' + phone[-4:]
    result.update(id=visit.id,visitor=visit.visitor_name,phone=phone,relation=visit.relationship,
        vehicleType=visit.vehicle_type,plate=visit.plate,purpose=visit.purpose,date=visit.visit_date,
        status=visit.status,created=visit.created_at,entered=visit.entered_at,exited=visit.exited_at,
        entry_person_count=visit.entry_person_count,exit_person_count=visit.exit_person_count,
        version=visit.version,inspectionConfirmed=bool(inspection and inspection.passed),
        inspectionConfirmedAt=inspection.confirmed_at if inspection else None)
    return result

def approval(db, user, vid, body, phase):
    require(user, 'warden')
    visit = visit_for(db, user, vid, body.version)
    if phase == 'entry':
        if visit.status != 'pending' or visit.visit_date < today(): raise HTTPException(409, 'Only a current or future pending request can be approved')
        visit.status = 'approved' if body.decision == 'approve' else 'rejected'
    else:
        if visit.status != 'inside' or body.decision != 'approve' or not body.meeting_verified:
            raise HTTPException(409, 'Confirm the meeting for a visitor currently inside before exit clearance')
        visit.status = 'exit'
    db.add(Approval(id=uid('APR-'),visit_id=visit.id,phase=phase,decision=body.decision,
        actor_id=user.id,note=body.note,created_at=utcnow()))
    bump(visit); audit(db,user,'Entry approved' if visit.status=='approved' else 'Request rejected' if visit.status=='rejected' else 'Exit approved',visit,body.note)
    db.commit()
    return visit_view(db,visit,user)

def inspection(db, user, vid, body):
    require(user,'security')
    visit = visit_for(db,user,vid,body.version)
    if visit.status != 'approved' or visit.visit_date != today(): raise HTTPException(409,'Inspection requires an approved visit for today')
    db.add(Inspection(id=uid('INS-'),visit_id=vid,guard_id=user.id,passed=body.passed,note=body.note,confirmed_at=utcnow()))
    bump(visit);audit(db,user,'Physical inspection passed' if body.passed else 'Physical inspection failed',visit,body.note)
    db.commit(); return visit_view(db,visit,user)

def passage(db,user,vid,body,direction):
    require(user,'security')
    visit = visit_for(db,user,vid,body.version)
    if normalized(body.plate)!=visit.plate or not body.visitor_verified: raise HTTPException(409,'Confirm the visible plate and visitor identity')
    if not db.get(Gate,body.gate_id): raise HTTPException(404,'Gate not found')
    phase = 'entry' if direction=='entry' else 'exit'
    approval_row=db.scalar(select(Approval).where(Approval.visit_id==vid,Approval.phase==phase,Approval.decision=='approve'))
    if not approval_row: raise HTTPException(409,'Required warden approval is missing')
    if direction=='entry':
        from .tailgating import ensure_clear,open_cycle
        ensure_clear(db)
        from .monitoring import entry_check
        entry_check(db,visit.plate)
        if visit.status!='approved' or visit.visit_date!=today() or visit.entered_at: raise HTTPException(409,'Visit is not eligible for entry today')
        inspected=db.scalar(select(Inspection).where(Inspection.visit_id==vid).order_by(Inspection.confirmed_at.desc()).limit(1))
        if not inspected or not inspected.passed: raise HTTPException(409,'A passed physical inspection is required')
        occupied=db.scalar(select(Visit).where(Visit.plate==visit.plate,Visit.id!=vid,Visit.status.in_(['inside','exit'])))
        if occupied: raise HTTPException(409,'This vehicle is already recorded inside campus')
        if db.get(VehicleOccupancy,visit.plate): raise HTTPException(409,'Vehicle is already inside campus')
        visit.status='inside';visit.entered_at=utcnow();visit.entry_person_count=body.person_count
        db.add(VehicleOccupancy(plate=visit.plate,source_id=visit.id,entered_at=visit.entered_at))
        open_cycle(db,user,vid,visit.plate)
    else:
        if visit.status!='exit' or not visit.entered_at or visit.exited_at: raise HTTPException(409,'Visit is not eligible for departure')
        if visit.entry_person_count is None:raise HTTPException(409,'Entry passenger count is missing. Contact the security head before departure.')
        if body.person_count!=visit.entry_person_count:raise HTTPException(409,f'Passenger count mismatch: entry {visit.entry_person_count}, exit {body.person_count}. Recheck occupants; departure has not been recorded.')
        visit.status='completed';visit.exited_at=utcnow();visit.exit_person_count=body.person_count
        occupancy=db.get(VehicleOccupancy,visit.plate)
        if occupancy and occupancy.source_id==visit.id:db.delete(occupancy)
    db.add(GateEvent(id=uid('EVT-'),visit_id=vid,gate_id=body.gate_id,guard_id=user.id,
        direction=direction,original_plate=body.original_plate,recorded_at=utcnow()))
    bump(visit);audit(db,user,'Vehicle entered' if direction=='entry' else 'Vehicle departed',visit,f'{body.person_count} people including driver. '+body.note)
    db.commit();return visit_view(db,visit,user)

def incident_view(db,item):
    visit=db.get(Visit,item.visit_id);student=db.get(Student,visit.student_id)
    actions=db.scalars(select(IncidentAction).where(IncidentAction.incident_id==item.id).order_by(IncidentAction.created_at)).all()
    return {'id':item.id,'source':'browser','visit':item.visit_id,'plate':visit.plate,
        'warden':db.get(User,student.warden_id).name,'title':item.title,'priority':item.priority,
        'owner':item.owner_role,'status':item.status,'note':item.note,'outcome':item.outcome,
        'created':item.created_at,'version':item.version,'timeline':[{'action':a.action,'note':a.note,
        'time':a.created_at,'actor':db.get(User,a.actor_id).name if a.actor_id else 'Legacy import'} for a in actions]}

def settings(db):
    result={'waiting':0,'lanes':1,'seconds':150,'dwell':240,'reviews':{},'source':'browser'}
    for row in db.scalars(select(Setting).where(Setting.key.like('monitor.%'))):
        result[row.key[8:]]=json.loads(row.value)
    return result

def projection(db,user):
    rows=accessible(db,user);ids=[v.id for v in rows]
    log_query=select(AuditLog).order_by(AuditLog.created_at.desc())
    if user.role=='warden':log_query=log_query.where(AuditLog.visit_id.in_(ids))
    logs=db.scalars(log_query.limit(5000)).all()
    incidents=db.scalars(select(Incident).where(Incident.visit_id.in_(ids)).order_by(Incident.created_at.desc())).all()
    if user.role not in ('head','admin'):
        incidents=[i for i in incidents if i.owner_role==user.role]
    return {'visits':[visit_view(db,v,user) for v in rows],
        'logs':[{'id':l.id,'action':l.action,'visit':l.visit_id or 'Gate operations','plate':db.get(Visit,l.visit_id).plate if l.visit_id else l.note.split(' / ')[0] if l.action.startswith(('Registered vehicle','Regular vehicle','Registration ','Tailgating','Passage count','ANPR output')) else '',
        'time':l.created_at,'actor':l.actor_name,'note':l.note} for l in logs],
        'incidents':[incident_view(db,i) for i in incidents],'headSettings':settings(db)}

def analytics(db,user,date=None):
    rows=accessible(db,user);chosen=date or today();config=settings(db)
    from .registry import RegisteredPassage, RegisteredVehicle
    from types import SimpleNamespace
    if user.role in ('head','admin','security'):
        rows=list(rows)+[SimpleNamespace(id=p.id,plate=db.get(RegisteredVehicle,p.vehicle_id).plate,
            entered_at=p.entered_at,exited_at=p.exited_at,status='completed' if p.exited_at else 'inside',visit_date=p.entered_at[:10])
            for p in db.scalars(select(RegisteredPassage))]
    def day(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(IST).date().isoformat() if value else None
    counts={'entries':sum(day(v.entered_at)==chosen for v in rows),
        'departures':sum(day(v.exited_at)==chosen for v in rows),
        'inside':sum(v.status in ('inside','exit') for v in rows),
        'pending':sum(v.status=='pending' and v.visit_date>=today() for v in rows)}
    alerts=[];dates={};now=datetime.now(timezone.utc)
    for v in rows:
        if not v.entered_at:continue
        entry=datetime.fromisoformat(v.entered_at.replace('Z','+00:00'));local=entry.astimezone(IST)
        if local.hour<6 or local.hour>=21: alerts.append({'visit':v.id,'plate':v.plate,'type':'outside_hours'})
        end=datetime.fromisoformat(v.exited_at.replace('Z','+00:00')) if v.exited_at else now
        if (end-entry).total_seconds()/60>config['dwell']:alerts.append({'visit':v.id,'plate':v.plate,'type':'long_dwell'})
        if today()>local.date().isoformat()>=(datetime.now(IST).date()-timedelta(days=14)).isoformat():
            key=local.date().isoformat();dates.setdefault(key,[0]*24)[local.hour]+=1
    bars=[{'hour':h,'value':sum(a[h] for a in dates.values())/len(dates)} for h in range(24)] if len(dates)>=3 else []
    return {'date':chosen,**counts,'flags':alerts,'hourly':bars,'recorded_days':len(dates),
        'queue':{'clearance_minutes':math.ceil(config['waiting']/config['lanes'])*config['seconds']/60,
        'capacity_per_hour':config['lanes']*(3600//config['seconds'])}}

def facts(db,user,date=None):
    a=analytics(db,user,date);rows=accessible(db,user);ids=[v.id for v in rows]
    unresolved=len(db.scalars(select(Incident).where(Incident.visit_id.in_(ids),Incident.status!='resolved')).all())
    from .tailgating import BarrierCycle
    tail_alerts=len(db.scalars(select(BarrierCycle).where(BarrierCycle.status=='alert')).all())
    from .monitoring import policy
    config=policy(db)
    return [{'id':k,'text':f'{a[k]} {label} on {a["date"]}.'} for k,label in
        [('entries','vehicle entries recorded'),('departures','vehicle departures recorded'),('inside','visits currently inside')]]+[
        {'id':'incidents','text':f'{unresolved} unresolved security incidents in the authorized records.'},
        {'id':'inspection_policy','text':'Every incoming vehicle requires physical inspection and guard verification. Active registered faculty, staff and approved daily visitors bypass a new warden request, but never bypass inspection. Plates alone do not establish occupant identity.'},
        {'id':'tailgating','text':f'{tail_alerts} unresolved tailgating count alerts; vehicle counts are manually simulated, and physical barrier hardware is not connected.'},
        {'id':'access_policy','text':f'Campus entry policy: {config.mode}; vehicle capacity: {config.capacity}; minimum recognition score: {config.min_confidence:.0%}. Policy is rechecked when recording entry.'},
        {'id':'flags','text':f'{len(a["flags"])} review flags across authorized history; human investigation is required.'}]
