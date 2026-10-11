"""Camera frames -> optional local detector/OCR -> existing audited recognition API.

Import and status checks never load or run the supplied model.
"""
import os, base64, io, importlib.util, threading, logging
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from .schemas import Input
from .security import current_user, require
from .database import get_db
from .anpr import Detection, receive, normalize, valid_plate
from .anpr_adapter import MODEL_PATH

router=APIRouter(prefix='/api/v1/anpr',tags=['Live camera'])
lock=threading.Lock()
detector=None
reader=None
fallback_reader=None
DETECTOR_PATH=MODEL_PATH.parent/'plate-detector.pt'
OCR_PATH=MODEL_PATH.parent/'ocr'
logger=logging.getLogger(__name__)

def status():
    missing=[m for m in ('ultralytics','torch','torchvision','cv2','PIL','easyocr') if importlib.util.find_spec(m) is None]
    enabled=os.getenv('ANPR_ENABLE_INFERENCE')=='1'
    ready=enabled and DETECTOR_PATH.is_file() and (OCR_PATH/'english_g2.pth').is_file() and not missing
    return {'enabled':enabled,'ready':ready,'model_present':MODEL_PATH.is_file(),
        'detector_present':DETECTOR_PATH.is_file(),'missing_dependencies':missing,'message':'Recognition available' if ready else
        'Model inference is disabled' if not enabled else 'Install local recognition dependencies'}

class Frame(Input):
    image: str=Field(min_length=20,max_length=1800000)
    direction: str=Field(pattern='^(entry|exit)$')
    gate_id: str='MAIN'

def recognize(image):
    global detector,reader,fallback_reader
    # Guarded lazy initialization: no inference from imports/startup/status.
    if not status()['ready']:raise HTTPException(503,status()['message'])
    # Require restricted loading; never silently fall back to unrestricted pickle.
    os.environ.setdefault('YOLO_AUTOINSTALL','False')
    os.environ.setdefault('YOLO_CONFIG_DIR',str(MODEL_PATH.parent))
    from ultralytics import YOLO
    from ultralytics.nn.tasks import torch_safe_load
    import torch, easyocr, numpy as np
    torch.set_num_threads(4)
    if detector is None:
        checkpoint,_=torch_safe_load(str(DETECTOR_PATH),safe_only=True)
        weights=checkpoint.get('ema') or checkpoint['model']
        if weights.names!={0:'number_plate'}:raise ValueError('Unexpected detector classes')
        detector=YOLO('yolo11s.yaml',task='detect',verbose=False)
        # Preserve the checkpoint's one-class head. Loading into the default
        # 80-class YAML model would silently skip its trained classifier weights.
        detector.model=weights.float().eval()
        detector.model.args={**getattr(weights,'args',{}),'task':'detect'}
    # The supplied CRNN needs its original training preprocessing confirmed.
    # Use the verified English reader until then; no downloads during requests.
    if fallback_reader is None:
        fallback_reader=easyocr.Reader(['en'],gpu=False,detector=False,download_enabled=False,
            model_storage_directory=str(OCR_PATH),user_network_directory=str(OCR_PATH/'network'),verbose=False)
    results=detector.predict(image,device='cpu',imgsz=640,conf=.25,verbose=False,save=False)
    candidates=[]
    boxes=[box for result in results if result.boxes is not None for box in result.boxes]
    if len(boxes)>1:
        # Preserve ambiguity even if only one of several vehicles has readable text.
        return [{'plate':'','confidence':0.,'box':[]} for _ in boxes]
    regions=[]
    for box in boxes:
        regions.append((list(map(int,box.xyxy[0].tolist())),float(box.conf[0]),'plate_detector'))
    if not regions:
        # A plate held up to a laptop may lack the vehicle context seen in YOLO
        # training. Read the visible alignment guide as an explicit OCR fallback.
        region=[0,0,image.width,image.height] if image.width/image.height>3 else [int(image.width*.1),int(image.height*.36),int(image.width*.9),int(image.height*.64)]
        regions.append((region,1.,'guided_ocr'))
    for coordinates,detector_score,source in regions:
        x1,y1,x2,y2=coordinates
        crop=image.crop((max(0,x1),max(0,y1),min(image.width,x2),min(image.height,y2)))
        if crop.width<8 or crop.height<8:continue
        if crop.width/crop.height>2:
            # Trim surrounding background from a light plate panel, including
            # margin left by the detector around a laptop demonstration plate.
            import cv2
            gray=np.array(crop.convert('L'))
            _,binary=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            contours,_=cv2.findContours(binary,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            rectangles=[cv2.boundingRect(c) for c in contours]
            rectangles=[r for r in rectangles if r[2]>=90 and r[3]>=20 and 2.5<r[2]/r[3]<10 and r[2]*r[3]>.1*crop.width*crop.height]
            if rectangles:
                rx,ry,rw,rh=max(rectangles,key=lambda r:r[2]*r[3])
                crop=crop.crop((rx,ry,rx+rw,ry+rh))
        parts=fallback_reader.recognize(np.array(crop.convert('L')),allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',detail=1)
        if not parts:continue
        raw=''.join(p[1] for p in parts).upper()
        ocr_score=min(float(p[2]) for p in parts)
        if not valid_plate(normalize(raw)):continue
        if ocr_score<.5:continue
        candidates.append({'plate':raw,'confidence':min(detector_score,ocr_score),'box':[x1,y1,x2,y2],'source':source})
    return candidates

@router.get('/camera-status')
def camera_status(user=Depends(current_user)):
    require(user,'security','head','admin');return status()

@router.post('/frames')
def frame(body:Frame,user=Depends(current_user),db=Depends(get_db)):
    require(user,'security')
    if not status()['ready']:raise HTTPException(503,status()['message'])
    if not lock.acquire(blocking=False):raise HTTPException(429,'Recognition busy. Try the next frame.')
    try:
        from PIL import Image, UnidentifiedImageError
        try:
            raw=base64.b64decode(body.image,validate=True)
            if len(raw)>1200000:raise ValueError()
            image=Image.open(io.BytesIO(raw))
            if image.format not in ('JPEG','PNG') or image.width*image.height>2100000:raise ValueError()
            image=image.convert('RGB')
        except (ValueError,UnidentifiedImageError,OSError):raise HTTPException(422,'Use a JPEG/PNG camera frame no larger than 1920 × 1080.')
        candidates=recognize(image)
        if len(candidates)!=1:
            return {'detection':None,'message':'No readable plate. Reposition the vehicle or correct it manually.' if not candidates else 'Multiple plates detected. Check one vehicle at a time.'}
        c=candidates[0]
        output=receive(Detection(detection_id='CAM-'+uuid4().hex,plate=c['plate'],confidence=c['confidence'],
            direction=body.direction,gate_id=body.gate_id,captured_at=datetime.now(timezone.utc)),user,db)
        output['box']=c['box'];output['source']=c.get('source','plate_detector');return output
    except HTTPException:raise
    except Exception:
        logger.exception("Local plate recognition failed")
        raise HTTPException(503,'Recognition could not run. Check the local detector and recognizer configuration; use manual plate verification.')
    finally:lock.release()
