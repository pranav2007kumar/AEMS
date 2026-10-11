"""Receives recognition results; never loads or executes a model."""
import re
from typing import Literal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field,field_validator
from sqlalchemy import select,String,Float,ForeignKey,Integer,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base,get_db
from .models import Gate,Visit
from .schemas import Input
from .security import current_user,require,utcnow
from . import services as svc

class PlateDetection(Base):
    __tablename__='plate_detections'
    id: Mapped[str]=mapped_column(String(80),primary_key=True)
    plate: Mapped[str]=mapped_column(String(20))
    confidence: Mapped[float]=mapped_column(Float)
    gate_id: Mapped[str]=mapped_column(ForeignKey('gates.id'))
    direction: Mapped[str]=mapped_column(String(10))
    captured_at: Mapped[str]=mapped_column(String(40))
    received_at: Mapped[str]=mapped_column(String(40))
    submitted_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
    plate_raw: Mapped[str]=mapped_column(String(40),default='')
    original_decision: Mapped[str]=mapped_column(String(20),default='HOLD')
    reason_code: Mapped[str]=mapped_column(String(60),default='HOLD_REVIEW_REQUIRED')
    reason_text: Mapped[str]=mapped_column(String(250),default='Guard verification required')
    status: Mapped[str]=mapped_column(String(20),default='open')
    review_note: Mapped[str]=mapped_column(String(500),default='')
    reviewed_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    version: Mapped[int]=mapped_column(Integer,default=1)
    __mapper_args__={'version_id_col':version}

class Detection(Input):
    detection_id: str=Field(min_length=8,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')
    plate: str=Field(min_length=1,max_length=40)
    confidence: float=Field(ge=0,le=1)
    gate_id: str='MAIN'
    direction: Literal['entry','exit']='entry'
    captured_at: datetime
    @field_validator('captured_at')
    @classmethod
    def timezone_required(cls,value):
        if value.tzinfo is None:raise ValueError('Timestamp must include timezone')
        return value

def normalize(value):
    value=re.sub(r'[\s.-]','',value.upper())
    return value[3:] if value.startswith('IND') else value
def valid_plate(value):return bool(re.fullmatch(r'(?:[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}|\d{2}BH\d{4}[A-Z]{1,2})',value))

def decision(db,p):
    from .models import VehicleOccupancy
    from .registry import RegisteredVehicle,RegisteredPassage
    from .monitoring import policy
    config=policy(db)
    def result(d,c,t):return {'decision':d,'reason_code':c,'reason_text':t}
    if not p.reviewed_by and p.confidence<config.min_confidence:return result('HOLD','HOLD_LOW_CONFIDENCE','Uncertain recognition. Check and correct the visible plate before permission verification.')
    if not valid_plate(p.plate):return result('HOLD','HOLD_UNKNOWN_FORMAT','Plate format needs explicit correction. The original reading is preserved.')
    occupied=db.get(VehicleOccupancy,p.plate)
    if p.direction=='exit':
        if not occupied:return result('HOLD','EXIT_ORPHAN','No recorded entry exists. Check the gate history; no entry is invented.')
        visit=db.get(Visit,occupied.source_id)
        if visit and visit.status!='exit':return result('HOLD','HOLD_EXIT_APPROVAL','Assigned warden exit clearance is pending.')
        return result('EXIT','EXIT_READY','Departure can be recorded after guard verification.')
    r=db.scalar(select(RegisteredVehicle).where(RegisteredVehicle.plate==p.plate))
    if r and not r.active:return result('DENY','DENY_BLOCKED','Vehicle registration is suspended.')
    if config.mode=='lockdown':return result('DENY','DENY_LOCKDOWN','New campus entry is paused. Exit remains available.')
    if occupied:return result('HOLD','HOLD_DUPLICATE_PRESENCE','Vehicle is already recorded inside campus.')
    if db.scalar(select(func.count()).select_from(VehicleOccupancy))>=config.capacity:return result('HOLD','HOLD_CAPACITY_FULL','Campus vehicle capacity is full.')
    visit=db.scalar(select(Visit).where(Visit.plate==p.plate,Visit.visit_date==svc.today(),Visit.status=='approved'))
    if visit:return result('ALLOW','ALLOW_WARDEN_APPROVED','Warden-approved visit. Inspection and guard verification are required before passage.')
    if r:
        if r.valid_until<svc.today():return result('HOLD','HOLD_REGISTRATION_EXPIRED','Vehicle registration has expired.')
        return result('ALLOW','ALLOW_REGISTERED','Registered vehicle. Inspection and occupant verification remain required.')
    return result('HOLD','HOLD_UNKNOWN','No active registration or approved visitor request. Contact the assigned warden or security head.')

def view(p,db=None):
    result={k:getattr(p,k) for k in ['id','plate','plate_raw','confidence','gate_id','direction','captured_at','received_at','original_decision','reason_code','reason_text','status','review_note','version']}
    result['decision']=p.original_decision
    if db:result['current_permission']=decision(db,p)
    return result

router=APIRouter(prefix='/api/v1/anpr',tags=['ANPR output integration'])
@router.post('/detections',status_code=201)
def receive(body:Detection,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security')
    if not db.get(Gate,body.gate_id):raise HTTPException(404,'Gate not found')
    if db.get(PlateDetection,body.detection_id):raise HTTPException(409,'Detection ID already received')
    p=PlateDetection(id=body.detection_id,plate=normalize(body.plate),plate_raw=body.plate,confidence=body.confidence,gate_id=body.gate_id,
        direction=body.direction,captured_at=body.captured_at.isoformat(),received_at=utcnow(),submitted_by=user.id)
    d=decision(db,p);p.original_decision=d['decision'];p.reason_code=d['reason_code'];p.reason_text=d['reason_text'];p.status='open' if d['decision']=='HOLD' else 'auto'
    db.add(p);svc.audit(db,user,'ANPR output received',note=p.plate+' / '+p.id);db.commit()
    return {'detection':view(p,db),'review_required':True,'inspection_required':body.direction=='entry',
        'message':'Detection received. Guard must check permission, visible plate and occupant before passage. No barrier command was sent.'}
@router.get('/detections')
def list_detections(user=Depends(current_user),db=Depends(get_db)):
    require(user,'security','head','admin')
    return {'items':[view(p,db) for p in db.scalars(select(PlateDetection).order_by(PlateDetection.received_at.desc()).limit(50))]}

class Review(Input):
    version: int=Field(ge=1)
    verified_plate: str=Field(min_length=6,max_length=20)
    note: str=Field(min_length=3,max_length=500)
@router.post('/detections/{did}/review')
def review(did:str,body:Review,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security','head','admin');p=db.get(PlateDetection,did)
    if not p:raise HTTPException(404,'Recognition record not found')
    if p.version!=body.version or p.status!='open':raise HTTPException(409,'Read already reviewed or changed')
    corrected=normalize(body.verified_plate)
    if not valid_plate(corrected):raise HTTPException(422,'Verified plate format is invalid')
    p.plate=corrected;p.reviewed_by=user.id;p.review_note=body.note;p.status='resolved'
    d=decision(db,p)
    if d['decision']=='DENY':raise HTTPException(409,d['reason_text'])
    svc.audit(db,user,'ANPR read reviewed',note=p.plate+' / '+body.note);db.commit()
    return view(p,db)
