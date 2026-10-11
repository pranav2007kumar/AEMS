"""Passage count demonstration. Real sensor/barrier hardware is not yet attached."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import Field
from .database import Base, get_db
from .schemas import Input
from .security import current_user,require,uid,utcnow
from . import services as svc

class BarrierCycle(Base):
    __tablename__='barrier_cycles'
    id: Mapped[str]=mapped_column(String(40),primary_key=True)
    passage_id: Mapped[str]=mapped_column(String(40),unique=True)
    plate: Mapped[str]=mapped_column(String(20))
    authorized_count: Mapped[int]=mapped_column(Integer,default=1)
    detected_count: Mapped[int]=mapped_column(Integer,default=0)
    status: Mapped[str]=mapped_column(String(20),default='awaiting_count')
    source: Mapped[str]=mapped_column(String(30),default='manual_demo')
    guard_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    opened_at: Mapped[str]=mapped_column(String(40))
    resolved_at: Mapped[str|None]=mapped_column(String(40),nullable=True)
    resolution_note: Mapped[str]=mapped_column(String(500),default='')
    version: Mapped[int]=mapped_column(Integer,default=1)
    __mapper_args__={'version_id_col':version}

def ensure_clear(db):
    if db.scalar(select(BarrierCycle).where(BarrierCycle.status=='alert')):
        raise HTTPException(409,'Resolve the tailgating alert before recording another entry')

def open_cycle(db,user,passage,plate):
    db.add(BarrierCycle(id=uid('CYCLE-'),passage_id=passage,plate=plate,guard_id=user.id,opened_at=utcnow()))

def view(c):
    return {k:getattr(c,k) for k in ['id','passage_id','plate','authorized_count','detected_count','status','source','opened_at','resolved_at','resolution_note','version']}

class Count(Input):
    version: int=Field(ge=1)
    detected_count: int=Field(ge=1,le=20)
class Resolve(Input):
    version: int=Field(ge=1)
    note: str=Field(min_length=10,max_length=500)

router=APIRouter(prefix='/api/v1/barrier-cycles',tags=['Tailgating demonstration'])
@router.get('')
def cycles(user=Depends(current_user),db=Depends(get_db)):
    require(user,'security','head','admin')
    return {'items':[view(c) for c in db.scalars(select(BarrierCycle).order_by(BarrierCycle.opened_at.desc()).limit(100))],'hardware_connected':False}
@router.post('/{cid}/count')
def record_count(cid:str,body:Count,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security');c=db.get(BarrierCycle,cid)
    if not c:raise HTTPException(404,'Passage cycle not found')
    if c.version!=body.version or c.status!='awaiting_count':raise HTTPException(409,'Cycle changed or already counted')
    c.detected_count=body.detected_count;c.status='alert' if body.detected_count>c.authorized_count else 'clear'
    svc.audit(db,user,'Tailgating alert' if c.status=='alert' else 'Passage count verified',note=c.plate+' / '+str(body.detected_count)+' vehicles; manual demonstration')
    db.commit();return view(c)
@router.post('/{cid}/resolve')
def resolve(cid:str,body:Resolve,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security','head','admin');c=db.get(BarrierCycle,cid)
    if not c:raise HTTPException(404,'Passage cycle not found')
    if c.version!=body.version or c.status!='alert':raise HTTPException(409,'Alert changed or already resolved')
    c.status='resolved';c.resolution_note=body.note;c.resolved_at=utcnow()
    svc.audit(db,user,'Tailgating alert resolved',note=c.plate+' / '+body.note);db.commit();return view(c)
