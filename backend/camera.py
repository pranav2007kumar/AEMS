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

ALLOWED='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

def overlap(a,b):
    """Intersection area divided by the SMALLER box, so a box inside another counts as the same plate."""
    iw=max(0,min(a[2],b[2])-max(a[0],b[0]));ih=max(0,min(a[3],b[3])-max(a[1],b[1]))
    return iw*ih/max(1,min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1])))

def read_best(crops):
    """Read a plate crop several ways and return the best valid (text, score), or None.

    Real camera frames are small, soft and slightly tilted, so one OCR pass is not
    enough. We retry with: original / contrast-enhanced, upscaled to a readable text
    height, small rotations, and (for square two-line plates) top + bottom halves.
    Every result must still be a valid plate format with score >= .5; nothing is guessed.
    """
    import cv2, numpy as np
    from PIL import Image
    clahe=cv2.createCLAHE(clipLimit=2.5,tileGridSize=(4,4))
    def ocr(gray):
        if gray.shape[0]<64:  # upscale tiny crops so characters are ~64px tall
            f=64/gray.shape[0];gray=cv2.resize(gray,None,fx=f,fy=f,interpolation=cv2.INTER_CUBIC)
        parts=fallback_reader.recognize(gray,allowlist=ALLOWED,detail=1)
        if not parts:return None
        return ''.join(p[1] for p in parts).upper(),min(float(p[2]) for p in parts)
    def accept(result):
        return result if result and result[1]>=.5 and valid_plate(normalize(result[0])) else None
    import re
    # Prefer the standard Indian layout (AA 00 AA 0000) over looser valid shapes:
    # this picks the right reading when OCR is torn between e.g. 8 and B.
    standard=lambda text:bool(re.fullmatch(r'[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}',normalize(text)))
    rank=lambda r:(standard(r[0]),r[1])
    best=None
    for crop in crops:
        for angle in (0,-6,6,-12,12):
            turned=crop.rotate(angle,expand=True,fillcolor=(255,255,255)) if angle else crop
            gray=np.array(turned.convert('L'))
            for variant in (gray,clahe.apply(gray)):
                found=accept(ocr(variant))
                if found and (best is None or rank(found)>rank(best)):best=found
                if best and standard(best[0]) and best[1]>=.65:return best  # confident enough, stop early
            if angle==0 and turned.width/turned.height<2.2:
                # two-line plate: read the top and bottom rows and join them
                h=gray.shape[0];top,bottom=ocr(gray[:h//2]),ocr(gray[h//2:])
                if top and bottom:
                    found=accept((top[0]+bottom[0],min(top[1],bottom[1])))
                    if found and (best is None or rank(found)>rank(best)):best=found
    return best

def read_crnn(crops):
    """Read crops with the project's trained CRNN (backend/plate_reader.py).

    One read of a CRNN can drop or swap a character after a tiny change in the
    crop, and a single wide crop can be confidently wrong. The reader costs ~3 ms,
    so each crop is read in a few slightly different versions (width stretched /
    squeezed) and the readings VOTE: the text read most often wins (ties go to the
    higher total confidence). Reads must be a valid plate format with mean
    confidence >= .5; nothing is guessed. Returns (text, mean confidence) or None.
    """
    from collections import defaultdict
    from PIL import Image
    from . import plate_reader
    votes=defaultdict(lambda:[0,0.,0.]);order=0   # text -> [count, total confidence, best confidence]
    for rank,crop in enumerate(crops):
        for stretch in (1.,.85,1.15):
            view=crop if stretch==1. else crop.resize((max(8,int(crop.width*stretch)),crop.height),Image.BILINEAR)
            text,score=plate_reader.read_crop(reader,view)
            if score>=.5 and valid_plate(normalize(text)):
                # The detector's own box (first crop) counts double: it is what the OCR was trained on.
                weight=2 if rank==0 else 1
                entry=votes[text];entry[0]+=weight;entry[1]+=score*weight;entry[2]=max(entry[2],score)
    if not votes:return None
    text=max(votes,key=lambda t:(votes[t][0],votes[t][1]))
    return text,votes[text][2]

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
    # Primary reader: the project's trained CRNN (preprocessing confirmed from the
    # training notebook). If it cannot load, the EasyOCR reader below still works.
    if reader is None and MODEL_PATH.is_file():
        try:
            from . import plate_reader
            reader=plate_reader.build_reader(str(MODEL_PATH))
        except Exception:
            logger.exception('Trained plate reader could not load; using fallback reader')
            reader=False
    # Fallback reader; no downloads during requests.
    if fallback_reader is None:
        fallback_reader=easyocr.Reader(['en'],gpu=False,detector=False,download_enabled=False,
            model_storage_directory=str(OCR_PATH),user_network_directory=str(OCR_PATH/'network'),verbose=False)
    # imgsz 640 = the size the detector was trained at.
    results=detector.predict(image,device='cpu',imgsz=640,conf=.1,verbose=False,save=False)
    candidates=[]
    every=[(list(map(int,box.xyxy[0].tolist())),float(box.conf[0])) for result in results if result.boxes is not None for box in result.boxes]
    # Only boxes with score >= .25 define "a plate"; weaker boxes are just extra
    # crop hints (on tilted plates the strongest box often covers only part of the
    # plate while a weaker, wider box covers all of it).
    boxes=sorted([b for b in every if b[1]>=.25],key=lambda b:-b[1]);distinct=[]
    # The detector often emits several overlapping boxes for ONE plate (blur, tilt,
    # low-resolution webcams). Keep the strongest box of each overlapping group so
    # one plate is not mistaken for several vehicles.
    for box in boxes:
        if all(overlap(box[0],kept[0])<.4 for kept in distinct):distinct.append(box)
    if len(distinct)>1:
        # Preserve ambiguity even if only one of several vehicles has readable text.
        return [{'plate':'','confidence':0.,'box':[]} for _ in distinct]
    regions=[]
    for b,c in distinct:
        group=[g for g,_ in every if overlap(g,b)>=.4]
        union=[min(g[0] for g in group),min(g[1] for g in group),max(g[2] for g in group),max(g[3] for g in group)]
        regions.append((b,c,'plate_detector',[union]+[g for g in group if g!=b]))
    if not regions:
        # A plate held up to a laptop may lack the vehicle context seen in YOLO
        # training. Read the visible alignment guide as an explicit OCR fallback.
        region=[0,0,image.width,image.height] if image.width/image.height>3 else [int(image.width*.1),int(image.height*.36),int(image.width*.9),int(image.height*.64)]
        regions.append((region,1.,'guided_ocr',[]))
    for coordinates,detector_score,source,alternates in regions:
        x1,y1,x2,y2=coordinates
        crop=image.crop((max(0,x1),max(0,y1),min(image.width,x2),min(image.height,y2)))
        if crop.width<8 or crop.height<8:continue
        # Slightly padded copy of the detector box: tight boxes can clip the first/last character.
        px,py=int((x2-x1)*.06),int((y2-y1)*.12)
        padded=image.crop((max(0,x1-px),max(0,y1-py),min(image.width,x2+px),min(image.height,y2+py)))
        detector_box=crop  # untouched detector box: first choice for the trained OCR
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
        extra=[image.crop((max(0,a[0]),max(0,a[1]),min(image.width,a[2]),min(image.height,a[3]))) for a in alternates]
        crops=[detector_box,crop,padded]+[e for e in extra if e.width>=8 and e.height>=8]
        best=(read_crnn(crops) if reader else None) or read_best(crops)
        if not best:continue
        raw,ocr_score=best
        # Reported confidence = reliability of the TEXT read. The detector score only says
        # "this box looks like a plate" (already required >= .25 above) and is not a
        # measure of whether the characters are right, so it must not drag the policy
        # score (default 0.90) down for a clean reading.
        candidates.append({'plate':raw,'confidence':ocr_score,'box':[x1,y1,x2,y2],'source':source})
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
