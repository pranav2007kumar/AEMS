"""Output-only bridge for the supplied model. IMPORTING THIS FILE DOES NOT RUN IT.

Call publish_recognition() from a separately operated inference/OCR process,
after that process has produced plate text and confidence. A bounding-box-only
detector needs OCR before this function can be called. Model format and classes
have not been validated because inference/loading was explicitly forbidden.
"""
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
import os
import httpx

MODEL_PATH=Path(__file__).parent/'models'/'campus-anpr.pt'
DEFAULT_BACKEND_URL='http://127.0.0.1:4174'

def publish_recognition(plate_text:str,confidence:float,*,session_cookie:str,
                        gate_id:str='MAIN',direction:str='entry',
                        detection_id:str|None=None,captured_at:str|None=None,
                        backend_url:str=DEFAULT_BACKEND_URL):
    """POST already-computed output using an authenticated guard session.

    Use a stable detection_id for retries. The backend rejects duplicate IDs.
    This function never opens MODEL_PATH or imports torch/ultralytics.
    Guard credentials/cookies must remain on the trusted local workstation.
    """
    if not session_cookie:raise ValueError('An authenticated guard session is required')
    if direction not in ('entry','exit'):raise ValueError('Invalid direction')
    payload={'detection_id':detection_id or str(uuid4()),'plate':plate_text,
        'confidence':confidence,'gate_id':gate_id,'direction':direction,
        'captured_at':captured_at or datetime.now(timezone.utc).isoformat()}
    with httpx.Client(timeout=15) as client:
        response=client.post(backend_url.rstrip('/')+'/api/v1/anpr/detections',json=payload,
            cookies={'campus_session':session_cookie},headers={'Origin':backend_url.rstrip('/')})
        response.raise_for_status();return response.json()

# Deliberately no model load, inference loop, camera capture or automatic startup.
