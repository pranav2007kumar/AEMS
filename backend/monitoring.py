"""Server-backed campus policy and security-head overview."""
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,String,Integer,Float,func
from sqlalchemy.orm import Mapped,mapped_column
from pydantic import Field
from typing import Literal
from .database import Base,get_db
from .models import VehicleOccupancy,Visit
from .schemas import Input
from .security import current_user,require,utcnow
from . import services as svc

class AccessPolicy(Base):
    __tablename__='access_policy'
    id: Mapped[str]=mapped_column(String(10),primary_key=True,default='MAIN')
    capacity: Mapped[int]=mapped_column(Integer,default=200)
    mode: Mapped[str]=mapped_column(String(20),default='normal')
    min_confidence: Mapped[float]=mapped_column(Float,default=0.9)
    updated_at: Mapped[str]=mapped_column(String(40))
    version: Mapped[int]=mapped_column(Integer,default=1)
    __mapper_args__={'version_id_col':version}

def policy(db):return db.get(AccessPolicy,'MAIN')
def policy_view(p):return {k:getattr(p,k) for k in ['capacity','mode','min_confidence','updated_at','version']}
def entry_check(db,plate):
    from .registry import RegisteredVehicle
    p=policy(db)
    registered=db.scalar(select(RegisteredVehicle).where(RegisteredVehicle.plate==plate))
    if registered and not registered.active:raise HTTPException(409,'Vehicle registration is suspended. Contact the security head.')
    if p.mode=='lockdown':raise HTTPException(409,'Campus entry is paused by the security head. Departure remains available.')
    if db.scalar(select(func.count()).select_from(VehicleOccupancy))>=p.capacity:raise HTTPException(409,'Campus vehicle capacity is full')
    # Shared version serializes concurrent entry/capacity checks and policy changes.
    p.version+=1

class PolicyChange(Input):
    capacity: int=Field(ge=1,le=100000)
    mode: Literal['normal','lockdown']
    min_confidence: float=Field(ge=0.5,le=1)
    version: int=Field(ge=1)

router=APIRouter(prefix='/api/v1',tags=['Security-head monitoring'])
@router.get('/access-policy')
def read_policy(user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin','security');return policy_view(policy(db))
@router.patch('/access-policy')
def change_policy(body:PolicyChange,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');p=policy(db)
    if p.version!=body.version:raise HTTPException(409,'Policy or occupancy changed. Refresh before saving.')
    p.capacity=body.capacity;p.mode=body.mode;p.min_confidence=body.min_confidence;p.updated_at=utcnow()
    p.version+=1
    svc.audit(db,user,'Campus access policy updated',note=f'Mode {p.mode}; capacity {p.capacity}; recognition threshold {p.min_confidence}')
    db.commit();return policy_view(p)

def overview(db,user):
    from .registry import RegisteredVehicle,RegisteredPassage,passage_view,vehicle_view
    from .tailgating import BarrierCycle,view as cycle_view
    from .anpr import PlateDetection,view as detection_view
    regs=db.scalars(select(RegisteredVehicle)).all()
    occupancy=db.scalars(select(VehicleOccupancy).order_by(VehicleOccupancy.entered_at.desc())).all()
    inside=[]
    for o in occupancy:
        v=db.get(Visit,o.source_id)
        if v:inside.append(svc.visit_view(db,v,user))
        else:
            p=db.get(RegisteredPassage,o.source_id)
            if p:inside.append(passage_view(db,p))
    detections=db.scalars(select(PlateDetection).order_by(PlateDetection.received_at.desc())).all()
    reads=[detection_view(d,db) for d in detections]
    bins=[];now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    for n in range(11,-1,-1):
        start=now-timedelta(hours=n);end=start+timedelta(hours=1)
        bins.append({'hour':start.astimezone(svc.IST).strftime('%H:%M'),
            'count':sum(start<=datetime.fromisoformat(d.received_at.replace('Z','+00:00'))<end for d in detections)})
    return {'policy':policy_view(policy(db)),'activity':svc.analytics(db,user),
        'inside':inside,'occupancy':len(occupancy),
        'registry':{'total':len(regs),'active':sum(r.active and r.valid_until>=svc.today() for r in regs),
            'suspended':sum(not r.active for r in regs),'expired':sum(r.active and r.valid_until<svc.today() for r in regs)},
        'registrations':[vehicle_view(db,r) for r in regs],
        'read_summary':{'total':len(reads),'allow':sum(r['decision']=='ALLOW' for r in reads),
            'hold':sum(r['decision']=='HOLD' for r in reads),'deny':sum(r['decision']=='DENY' for r in reads),
            'exit':sum(r['decision']=='EXIT' for r in reads)},
        'review_queue':[r for r in reads if r['status']=='open'],'recent_reads':reads[:100],
        'hourly_reads':bins,'tailgating_alerts':[cycle_view(c) for c in db.scalars(select(BarrierCycle).where(BarrierCycle.status=='alert'))]}

@router.get('/monitoring/overview')
def get_overview(user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');return overview(db,user)
