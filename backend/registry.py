from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, Index, text, String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, get_db
from .models import User, VehicleOccupancy
from .schemas import Input
from .security import current_user, require, uid, utcnow
from . import services as svc

class RegisteredVehicle(Base):
    __tablename__='registered_vehicles'
    id: Mapped[str]=mapped_column(String(40),primary_key=True)
    plate: Mapped[str]=mapped_column(String(20),unique=True)
    owner_name: Mapped[str]=mapped_column(String(100))
    category: Mapped[str]=mapped_column(String(40))
    purpose: Mapped[str]=mapped_column(String(180))
    valid_until: Mapped[str]=mapped_column(String(10))
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    approved_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
    created_at: Mapped[str]=mapped_column(String(40))
    version: Mapped[int]=mapped_column(Integer,default=1)
    __mapper_args__={'version_id_col':version}

class RegisteredPassage(Base):
    __tablename__='registered_passages'
    __table_args__=(Index('unique_registered_vehicle_inside','vehicle_id',unique=True,
        sqlite_where=text('exited_at IS NULL'),postgresql_where=text('exited_at IS NULL')),)
    id: Mapped[str]=mapped_column(String(40),primary_key=True)
    vehicle_id: Mapped[str]=mapped_column(ForeignKey('registered_vehicles.id'))
    entry_guard: Mapped[str]=mapped_column(ForeignKey('users.id'))
    exit_guard: Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    inspection_confirmed_at: Mapped[str]=mapped_column(String(40))
    entered_at: Mapped[str]=mapped_column(String(40))
    exited_at: Mapped[str|None]=mapped_column(String(40),nullable=True)
    entry_person_count: Mapped[int|None]=mapped_column(Integer,nullable=True)
    exit_person_count: Mapped[int|None]=mapped_column(Integer,nullable=True)
    version: Mapped[int]=mapped_column(Integer,default=1)
    __mapper_args__={'version_id_col':version}

from typing import Literal
class Registration(Input):
    plate: str=Field(min_length=6,max_length=20)
    owner_name: str=Field(min_length=2,max_length=100)
    category: Literal['Faculty','Staff','Approved daily visitor','Vendor']
    purpose: str=Field(min_length=3,max_length=180)
    valid_until: date
class RegistryStatus(Input):
    active: bool
    version: int=Field(ge=1)
class RegistryEntry(Input):
    person_count: int=Field(ge=1,le=100,strict=True)
    plate: str
    visitor_verified: bool
    inspection_completed: bool
    version: int=Field(ge=1)
class RegistryExit(Input):
    person_count: int=Field(ge=1,le=100,strict=True)
    plate: str
    visitor_verified: bool
    version: int=Field(ge=1)

def vehicle_view(db,row):
    return {'id':row.id,'plate':row.plate,'owner_name':row.owner_name,'category':row.category,
        'purpose':row.purpose,'valid_until':row.valid_until,'active':row.active,
        'approved_by':db.get(User,row.approved_by).name,'version':row.version,
        'eligible':row.active and row.valid_until>=svc.today()}
def passage_view(db,p):
    r=db.get(RegisteredVehicle,p.vehicle_id)
    return {'id':p.id,'plate':r.plate,'visitor':r.owner_name,'student':'Registered campus access',
        'studentId':'','branch':r.category,'hostel':'Campus','warden':'Security-head registration',
        'relation':r.category,'vehicleType':'Car','phone':'','purpose':r.purpose,
        'date':p.entered_at[:10],'status':'completed' if p.exited_at else 'inside',
        'created':p.entered_at,'entered':p.entered_at,'exited':p.exited_at,'version':p.version,
        'entry_person_count':p.entry_person_count,'exit_person_count':p.exit_person_count,
        'inspectionConfirmed':True,'inspectionConfirmedAt':p.inspection_confirmed_at,
        'registered_vehicle_id':r.id,'access_type':'registered'}

router=APIRouter(prefix='/api/v1',tags=['Registered vehicles'])

@router.get('/registered-vehicles')
def list_registered(user=Depends(current_user),db=Depends(get_db)):
    require(user,'security','head','admin')
    return {'items':[vehicle_view(db,v) for v in db.scalars(select(RegisteredVehicle).order_by(RegisteredVehicle.owner_name))]}
@router.post('/registered-vehicles',status_code=201)
def register(body:Registration,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');plate=svc.normalized(body.plate)
    if len(plate)<6 or len(plate)>16:raise HTTPException(422,'Invalid vehicle number')
    if body.valid_until.isoformat()<svc.today():raise HTTPException(422,'Registration expiry cannot be in the past')
    row=RegisteredVehicle(id=uid('REG-'),plate=plate,owner_name=body.owner_name,category=body.category,
        purpose=body.purpose,valid_until=body.valid_until.isoformat(),active=True,approved_by=user.id,created_at=utcnow())
    db.add(row);svc.audit(db,user,'Regular vehicle registration approved',note=plate+' / '+body.purpose);db.commit()
    return vehicle_view(db,row)
@router.patch('/registered-vehicles/{rid}')
def status_change(rid:str,body:RegistryStatus,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');r=db.get(RegisteredVehicle,rid)
    if not r:raise HTTPException(404,'Registration not found')
    if r.version!=body.version:raise HTTPException(409,'Registration changed')
    r.active=body.active;svc.audit(db,user,'Registration activated' if body.active else 'Registration suspended',note=r.plate);db.commit()
    return vehicle_view(db,r)
@router.get('/registered-vehicles/lookup/{plate}')
def lookup(plate:str,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security','head','admin')
    r=db.scalar(select(RegisteredVehicle).where(RegisteredVehicle.plate==svc.normalized(plate)))
    if not r:raise HTTPException(404,'Vehicle is not registered')
    p=db.scalar(select(RegisteredPassage).where(RegisteredPassage.vehicle_id==r.id,RegisteredPassage.exited_at.is_(None)))
    return {'vehicle':vehicle_view(db,r),'inside':passage_view(db,p) if p else None}
@router.post('/registered-vehicles/{rid}/entry')
def regular_entry(rid:str,body:RegistryEntry,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security');r=db.get(RegisteredVehicle,rid)
    if not r:raise HTTPException(404,'Registration not found')
    if r.version!=body.version:raise HTTPException(409,'Registration changed. Look up the plate again.')
    if not r.active or r.valid_until<svc.today():raise HTTPException(409,'Registration is inactive or expired')
    from .tailgating import ensure_clear,open_cycle
    ensure_clear(db)
    from .monitoring import entry_check
    entry_check(db,r.plate)
    if not body.inspection_completed or not body.visitor_verified or svc.normalized(body.plate)!=r.plate:
        raise HTTPException(409,'Physical inspection and visible plate/occupant verification are required')
    from .models import Visit
    if db.scalar(select(Visit).where(Visit.plate==r.plate,Visit.status.in_(['inside','exit']))):
        raise HTTPException(409,'Vehicle is already inside under a visitor request')
    if db.get(VehicleOccupancy,r.plate):raise HTTPException(409,'Vehicle is already inside campus')
    r.version+=1
    p=RegisteredPassage(id=uid('REGVISIT-'),vehicle_id=rid,entry_guard=user.id,
        inspection_confirmed_at=utcnow(),entered_at=utcnow(),entry_person_count=body.person_count)
    db.add(p);db.add(VehicleOccupancy(plate=r.plate,source_id=p.id,entered_at=p.entered_at))
    open_cycle(db,user,p.id,r.plate)
    svc.audit(db,user,'Registered vehicle inspected and entered',note=f'{r.plate} / {body.person_count} people including driver');db.commit()
    return passage_view(db,p)
@router.post('/registered-passages/{pid}/exit')
def regular_exit(pid:str,body:RegistryExit,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security');p=db.get(RegisteredPassage,pid)
    if not p:raise HTTPException(404,'Registered passage not found')
    r=db.get(RegisteredVehicle,p.vehicle_id)
    if p.version!=body.version or p.exited_at:raise HTTPException(409,'Departure already recorded or record changed')
    if not body.visitor_verified or svc.normalized(body.plate)!=r.plate:raise HTTPException(409,'Verify visible vehicle and occupant')
    if p.entry_person_count is None:raise HTTPException(409,'Entry passenger count is missing. Contact the security head before departure.')
    if body.person_count!=p.entry_person_count:raise HTTPException(409,f'Passenger count mismatch: entry {p.entry_person_count}, exit {body.person_count}. Recheck occupants; departure has not been recorded.')
    p.exited_at=utcnow();p.exit_guard=user.id;p.exit_person_count=body.person_count
    occupancy=db.get(VehicleOccupancy,r.plate)
    if occupancy and occupancy.source_id==p.id:db.delete(occupancy)
    svc.audit(db,user,'Registered vehicle departed',note=f'{r.plate} / {body.person_count} people including driver');db.commit()
    return passage_view(db,p)
