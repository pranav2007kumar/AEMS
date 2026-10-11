"""Run from the repository root: bundled-python backend/run.py."""
import os, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend/.deps'))
sys.path.insert(0,str(root))
import uvicorn
if __name__=='__main__':
    # Shared credentials are allowed only for this loopback demonstration runner.
    if os.getenv('APP_ENV')!='production':
        os.environ.setdefault('LOCAL_DEMO_LOGIN','1')
        if (root/'backend/models/plate-detector.pt').is_file() and (root/'backend/models/ocr/english_g2.pth').is_file():
            os.environ.setdefault('ANPR_ENABLE_INFERENCE','1')
    uvicorn.run('backend.main:app',host='127.0.0.1',port=int(os.getenv('PORT','4174')))
