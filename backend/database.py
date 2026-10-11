import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///' + (DATA / 'campus-gate.sqlite3').as_posix())
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 15} if DATABASE_URL.startswith('sqlite') else {})
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase):
    pass

def get_db():
    with Session() as db:
        yield db
