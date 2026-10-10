"""Revision-checked SQLite snapshot store for the local multi-portal prototype."""
import json, sqlite3
from contextlib import closing
from pathlib import Path
DB = Path(__file__).resolve().parent / 'data' / 'gate-state.sqlite3'

def connect(path=DB):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)')
    return db

def read(path=DB):
    with closing(connect(path)) as db:
        row=db.execute('SELECT revision,payload FROM state WHERE id=1').fetchone()
    return {'revision':row[0],'state':json.loads(row[1])} if row else {'revision':0,'state':None}

def write(revision,state,path=DB):
    if type(revision) is not int or revision<0 or not isinstance(state,dict):raise ValueError('Invalid state revision')
    if set(state)!={'visits','logs','headSettings','incidents'}:raise ValueError('Invalid state fields')
    for key in ['visits','logs','incidents']:
        if not isinstance(state[key],list) or any(not isinstance(v,dict) for v in state[key]):raise ValueError('Invalid '+key)
    if not isinstance(state['headSettings'],dict):raise ValueError('Invalid head settings')
    for key in ['visits','incidents']:
        ids=[v.get('id') for v in state[key]]
        if any(not isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Missing or duplicate IDs')
    raw=json.dumps(state)
    if len(raw.encode())>5000000:raise ValueError('State exceeds prototype limit')
    with closing(connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT revision,payload FROM state WHERE id=1').fetchone()
        current=row[0] if row else 0
        if revision!=current:
            return False, {'revision':current,'state':json.loads(row[1]) if row else None}
        db.execute('INSERT OR REPLACE INTO state VALUES (1,?,?)',(current+1,raw))
        db.commit()
    return True, {'revision':current+1,'state':state}
