from alembic import op
from sqlalchemy import inspect,text
from backend.monitoring import AccessPolicy
from backend.security import utcnow
revision='0006_monitoring'
down_revision='0005_anpr_output'
branch_labels=None
depends_on=None
def upgrade():
    connection=op.get_bind()
    AccessPolicy.__table__.create(connection,checkfirst=True)
    if not connection.execute(text("SELECT id FROM access_policy WHERE id='MAIN'")).first():
        connection.execute(text("INSERT INTO access_policy(id,capacity,mode,min_confidence,updated_at,version) VALUES('MAIN',200,'normal',0.9,:t,1)"),{'t':utcnow()})
    fields={c['name'] for c in inspect(connection).get_columns('plate_detections')}
    definitions={'plate_raw':"VARCHAR(40) NOT NULL DEFAULT ''",'original_decision':"VARCHAR(20) NOT NULL DEFAULT 'HOLD'",
        'reason_code':"VARCHAR(60) NOT NULL DEFAULT 'HOLD_REVIEW_REQUIRED'",'reason_text':"VARCHAR(250) NOT NULL DEFAULT 'Guard verification required'",
        'status':"VARCHAR(20) NOT NULL DEFAULT 'open'",'review_note':"VARCHAR(500) NOT NULL DEFAULT ''",
        'reviewed_by':"VARCHAR(40)",'version':"INTEGER NOT NULL DEFAULT 1"}
    for name,definition in definitions.items():
        if name not in fields:connection.execute(text(f'ALTER TABLE plate_detections ADD COLUMN {name} {definition}'))
    connection.execute(text("UPDATE plate_detections SET plate_raw=plate WHERE plate_raw=''"))
def downgrade():raise RuntimeError('Destructive downgrade disabled')
