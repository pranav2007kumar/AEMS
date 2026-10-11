import os, json, time, hashlib, secrets, re
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from .database import ROOT, get_db
from .models import *
from .schemas import *
from .security import current_user, optional_user, issue_session, verify_password, hash_password, token_hash, uid, utcnow, require
from . import services as svc, ai
from .bootstrap import initialize
from .registry import router as registry_router, RegisteredPassage, passage_view
from .tailgating import router as tailgating_router
from .anpr import router as anpr_router
from .monitoring import router as monitoring_router
from .camera import router as camera_router

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app=FastAPI(title='Amrita Campus Gate API',version='1.0.0',lifespan=lifespan)
app.include_router(registry_router)
app.include_router(tailgating_router)
app.include_router(anpr_router)
app.include_router(monitoring_router)
app.include_router(camera_router)
limits=defaultdict(deque)

@app.middleware('http')
async def safety(request,call_next):
    if request.url.path.startswith('/api/'):
        if request.method in ('POST','PATCH','DELETE'):
            origin=request.headers.get('origin')
            if origin and origin!=str(request.base_url).rstrip('/') or request.headers.get('sec-fetch-site')=='cross-site':
                return JSONResponse({'detail':'Same-origin requests required'},403)
            if request.cookies.get('campus_session') and not origin:
                return JSONResponse({'detail':'Origin required for cookie-authenticated changes'},403)
            maximum=1900000 if request.url.path=='/api/v1/anpr/frames' else 32000 if '/ai/' in request.url.path else 16000
            try:
                body=await request.body()
                if len(body)>maximum:return JSONResponse({'detail':'Request too large'},413)
            except Exception:return JSONResponse({'detail':'Invalid request body'},400)
        if request.url.path in ('/api/v1/auth/login','/api/v1/visits') or '/ai/' in request.url.path:
            key=(request.client.host,request.url.path)
            now=time.monotonic();q=limits[key]
            while q and now-q[0]>60:q.popleft()
            maximum=10 if request.url.path.endswith('/login') else 30
            if len(q)>=maximum:return JSONResponse({'detail':'Too many requests. Retry in one minute.'},429,headers={'Retry-After':'60'})
            q.append(now)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    # Local development assets must never outlive a code update in browser cache.
    response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma']='no-cache'
    response.headers['Expires']='0'
    return response

@app.exception_handler(StaleDataError)
async def stale(_,exc):return JSONResponse({'detail':'Record changed. Refresh before retrying.'},409)
@app.exception_handler(IntegrityError)
async def integrity(_,exc):return JSONResponse({'detail':'Duplicate or conflicting record'},409)
@app.exception_handler(OperationalError)
async def operational(_,exc):return JSONResponse({'detail':'Database busy. Refresh and retry.'},503)

def user_view(user):return {'id':user.id,'username':user.username,'name':user.name,'role':user.role}

@app.get('/api/v1/health')
def health(db=Depends(get_db)):
    db.execute(select(Gate.id).limit(1))
    return {'status':'ok','database':'relational','camera_connected':False}

@app.post('/api/v1/auth/login')
def login(body:Login,response:Response,request:Request,db=Depends(get_db)):
    demo = (os.getenv('LOCAL_DEMO_LOGIN')=='1' and os.getenv('APP_ENV')!='production'
            and request.client.host in ('127.0.0.1','::1','testclient')
            and request.url.hostname in ('127.0.0.1','localhost','testserver'))
    alias = demo and body.username=='1234' and secrets.compare_digest(body.password,'1234')
    if alias:
        account = {'security':'GUARD','head':'HEAD','registry':'HEAD','admin':'ADMIN','warden':body.warden_id}.get(body.portal)
        if not account:raise HTTPException(409,'This sign-in page is outdated. Open /refresh-local-cache, then sign in again with 1234 / 1234.')
        user = db.get(User,account) if account else None
    else:
        user=db.scalar(select(User).where(User.username==body.username.lower()))
        alias = bool(demo and user and user.id in ('HEAD','GUARD','MENON','DEVI','ADMIN') and secrets.compare_digest(body.password,'1234'))
    if not user or not user.active or (not alias and not verify_password(body.password,user.password_hash)):
        raise HTTPException(401,'Invalid username or password')
    token=issue_session(db,user)
    response.set_cookie('campus_session',token,httponly=True,samesite='strict',secure=os.getenv('APP_ENV')=='production',max_age=8*3600,path='/')
    svc.audit(db,user,'Staff signed in');db.commit()
    return {'user':user_view(user)}

@app.get('/api/v1/auth/me')
def me(user=Depends(current_user)):return user_view(user)

@app.post('/api/v1/auth/logout')
def logout(request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    for row in db.scalars(select(LoginSession).where(LoginSession.user_id==user.id)):db.delete(row)
    svc.audit(db,user,'Staff signed out');db.commit();response.delete_cookie('campus_session',path='/')
    return {'message':'Signed out'}

@app.get('/api/v1/students/{student_id}')
def student_lookup(student_id:str,db=Depends(get_db)):
    student=db.get(Student,student_id.strip().upper())
    if not student:raise HTTPException(404,'Student ID not found')
    # Only explicitly seeded sample directory records are public.
    if not student.sample:raise HTTPException(403,'Official directory requires authenticated university access')
    return svc.student_view(db,student)

@app.post('/api/v1/visits',status_code=201)
def create_visit(body:VisitCreate,db=Depends(get_db)):
    student=db.get(Student,body.studentId.upper())
    if not student:raise HTTPException(404,'Student not found')
    if body.date.isoformat()<svc.today():raise HTTPException(400,'Choose today or a future visit date')
    existing=db.scalar(select(Visit).where(Visit.plate==body.plate,Visit.visit_date==body.date.isoformat(),Visit.status.notin_(['completed','rejected'])))
    if existing:raise HTTPException(409,'An active visit already exists for this vehicle and date')
    tracking=secrets.token_urlsafe(32)
    visit=Visit(id=uid('AMV-'),visitor_name=body.visitor,phone=body.phone,relationship=body.relation,
        vehicle_type=body.vehicleType,plate=body.plate,student_id=student.id,purpose=body.purpose,
        visit_date=body.date.isoformat(),status='pending',tracking_hash=token_hash(tracking),created_at=utcnow(),updated_at=utcnow())
    db.add(visit);db.flush();svc.audit(db,None,'Request submitted',visit);db.commit()
    return {'visit':svc.visit_view(db,visit),'tracking_token':tracking}

@app.get('/api/v1/public/visits/{vid}')
def track(vid:str,request:Request,db=Depends(get_db)):
    visit=db.get(Visit,vid);token=request.headers.get('X-Visit-Token','')
    if not visit or not secrets.compare_digest(visit.tracking_hash,token_hash(token)):
        raise HTTPException(404,'Request not found or tracking token invalid')
    return svc.visit_view(db,visit)

@app.get('/api/v1/visits')
def visits(status:str|None=None,plate:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),user=Depends(current_user),db=Depends(get_db)):
    rows=svc.accessible(db,user)
    if status:rows=[v for v in rows if v.status==status]
    if plate:rows=[v for v in rows if svc.normalized(plate)==v.plate]
    return {'items':[svc.visit_view(db,v,user) for v in rows[(page-1)*page_size:page*page_size]],'total':len(rows),'page':page,'page_size':page_size}

@app.get('/api/v1/visits/{vid}')
def visit_details(vid:str,user=Depends(current_user),db=Depends(get_db)):
    return svc.visit_view(db,svc.visit_for(db,user,vid),user)

@app.post('/api/v1/visits/{vid}/entry-approval')
def entry_approval(vid:str,body:ApprovalChange,user=Depends(current_user),db=Depends(get_db)):
    return svc.approval(db,user,vid,body,'entry')
@app.post('/api/v1/visits/{vid}/exit-approval')
def exit_approval(vid:str,body:ApprovalChange,user=Depends(current_user),db=Depends(get_db)):
    return svc.approval(db,user,vid,body,'exit')
@app.post('/api/v1/visits/{vid}/inspection')
def inspection(vid:str,body:InspectionChange,user=Depends(current_user),db=Depends(get_db)):
    return svc.inspection(db,user,vid,body)
@app.post('/api/v1/visits/{vid}/entry')
def entry(vid:str,body:Passage,user=Depends(current_user),db=Depends(get_db)):
    return svc.passage(db,user,vid,body,'entry')
@app.post('/api/v1/visits/{vid}/exit')
def exit(vid:str,body:Passage,user=Depends(current_user),db=Depends(get_db)):
    return svc.passage(db,user,vid,body,'exit')

@app.get('/api/v1/state')
def state(user=Depends(current_user),db=Depends(get_db)):
    result=svc.projection(db,user)
    if user.role in ('head','admin','security'):
        result['visits'] += [passage_view(db,p) for p in db.scalars(select(RegisteredPassage).order_by(RegisteredPassage.entered_at.desc()))]
    return {'state':result}

@app.get('/api/v1/incidents')
def incident_list(user=Depends(current_user),db=Depends(get_db)):
    return {'items':svc.projection(db,user)['incidents']}

@app.post('/api/v1/incidents',status_code=201)
def incident_create(body:IncidentCreate,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');visit=svc.visit_for(db,user,body.visit_id)
    item=Incident(id=uid('INC-'),visit_id=visit.id,title=body.title,owner_role=body.owner,
        priority=body.priority,note=body.note,status='open',created_at=utcnow())
    db.add(item);db.flush()
    db.add(IncidentAction(id=uid('ACT-'),incident_id=item.id,actor_id=user.id,action='Incident reported',note=body.note,created_at=utcnow()))
    svc.audit(db,user,'Incident reported',visit,body.note);db.commit()
    return svc.incident_view(db,item)

@app.post('/api/v1/incidents/{iid}/actions')
def incident_change(iid:str,body:IncidentChange,user=Depends(current_user),db=Depends(get_db)):
    item=db.get(Incident,iid)
    if not item:raise HTTPException(404,'Incident not found')
    svc.visit_for(db,user,item.visit_id)
    if user.role not in ('head','admin') and item.owner_role!=user.role:raise HTTPException(403,'Incident belongs to another team')
    if item.version!=body.version or item.status=='resolved':raise HTTPException(409,'Incident changed or already resolved')
    if not body.note:raise HTTPException(422,'An investigation note is required')
    item.status='resolved' if body.action=='resolve' else 'in_progress';item.outcome=body.outcome
    name='Incident resolved' if body.action=='resolve' else 'Incident acknowledged'
    db.add(IncidentAction(id=uid('ACT-'),incident_id=iid,actor_id=user.id,action=name,note=body.outcome+': '+body.note,created_at=utcnow()))
    svc.audit(db,user,name,db.get(Visit,item.visit_id),body.note);db.commit();return svc.incident_view(db,item)

@app.get('/api/v1/settings')
def settings(user=Depends(current_user),db=Depends(get_db)):return svc.settings(db)
@app.patch('/api/v1/settings')
def settings_change(body:SettingsChange,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin')
    for key,value in body.model_dump().items():
        row=db.get(Setting,'monitor.'+key)
        if row:row.value=json.dumps(value)
        else:db.add(Setting(key='monitor.'+key,value=json.dumps(value)))
    svc.audit(db,user,'Monitoring settings updated');db.commit();return svc.settings(db)

@app.get('/api/v1/audit-logs')
def audit_logs(page:int=Query(1,ge=1),page_size:int=Query(100,ge=1,le=500),user=Depends(current_user),db=Depends(get_db)):
    rows=svc.projection(db,user)['logs'];return {'items':rows[(page-1)*page_size:page*page_size],'total':len(rows)}
@app.get('/api/v1/analytics/summary')
def analytics(date:str|None=None,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');return svc.analytics(db,user,date)

@app.get('/api/ai/status')
@app.get('/api/v1/ai/status')
def ai_status(user=Depends(current_user)):
    require(user,'head','admin');return {'models':[ai.MODEL] if ai.configured() else [],'groqConfigured':ai.configured()}
@app.post('/api/ai/chat')
@app.post('/api/v1/ai/chat')
async def chat(body:Chat,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');return await ai.chat(db,user,body)
@app.post('/api/ai/summary')
@app.post('/api/v1/ai/summary')
async def summary(body:Summary,user=Depends(current_user),db=Depends(get_db)):
    require(user,'head','admin');return await ai.summary(db,user,body)

@app.post('/api/state')
def old_snapshot_write():raise HTTPException(410,'Snapshot writes retired. Use authenticated visit action endpoints.')

@app.get('/',response_class=HTMLResponse)
def index():
    content=(ROOT/'dist/index.html').read_text(encoding='utf-8')
    content=content.replace('<script src="shared-state.js"></script>','<script src="head-monitor.js"></script><script src="live-camera.js"></script><script src="backend-ui.js"></script>')
    def fresh_asset(match):
        name=match.group(2)
        if name.startswith(('http:','https:','//')):return match.group(0)
        path=Path(__file__).parent/'frontend'/name if name in ('head-monitor.js','backend-ui.js','live-camera.js') else ROOT/'dist'/name
        if not path.is_file():return match.group(0)
        version=hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return match.group(1)+name+'?v='+version+match.group(3)
    content=re.sub(r'''((?:src|href)=["'])([^"'?]+\.(?:js|css))(?:\?[^"']*)?(["'])''',fresh_asset,content)
    return HTMLResponse(content,headers={'Cache-Control':'no-store'})

@app.get('/refresh-local-cache',response_class=HTMLResponse)
def refresh_local_cache():
    # Cache only: preserve authentication cookies, private tracking tokens and records.
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>Refreshing local app</title></head>
    <body style="font-family:system-ui;padding:40px"><h1>Refreshing the local app…</h1><p>Removing cached assets. Your records and sign-in are preserved.</p>
    <script>(async()=>{try{if('caches' in window){for(const name of await caches.keys())await caches.delete(name)}
    if('serviceWorker' in navigator){for(const worker of await navigator.serviceWorker.getRegistrations())await worker.unregister()}}
    catch(error){console.warn('Cache cleanup unavailable',error)}
    location.replace('/?fresh='+Date.now()+'#head')})();</script></body></html>''',
        headers={'Clear-Site-Data':'"cache"','Cache-Control':'no-store'})
@app.get('/backend-ui.js')
def backend_ui():return FileResponse(Path(__file__).parent/'frontend/backend-ui.js',media_type='text/javascript',headers={'Cache-Control':'no-store'})

@app.get('/head-monitor.js')
def head_monitor():return FileResponse(Path(__file__).parent/'frontend/head-monitor.js',media_type='text/javascript',headers={'Cache-Control':'no-store'})

@app.get('/live-camera.js')
def live_camera():return FileResponse(Path(__file__).parent/'frontend/live-camera.js',media_type='text/javascript',headers={'Cache-Control':'no-store'})

# API routes above take precedence; reuse the existing visual assets without changing the hosted Site.
app.mount('/',StaticFiles(directory=str(ROOT/'dist')),name='frontend')
