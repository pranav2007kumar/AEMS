"""One active campus passage per plate across both access workflows."""
from alembic import op
from sqlalchemy import text
from backend.models import VehicleOccupancy
revision='0003_occupancy'
down_revision='0002_registry'
branch_labels=None
depends_on=None
def upgrade():
    connection=op.get_bind()
    VehicleOccupancy.__table__.create(connection,checkfirst=True)
    rows=connection.execute(text("SELECT plate,id,entered_at FROM visits WHERE status IN ('inside','exit')")).all()
    rows+=connection.execute(text('SELECT r.plate,p.id,p.entered_at FROM registered_passages p JOIN registered_vehicles r ON r.id=p.vehicle_id WHERE p.exited_at IS NULL')).all()
    for plate,source,time in rows:
        if not connection.execute(text('SELECT plate FROM vehicle_occupancy WHERE plate=:p'),{'p':plate}).first():
            connection.execute(text('INSERT INTO vehicle_occupancy(plate,source_id,entered_at) VALUES(:p,:s,:t)'),{'p':plate,'s':source,'t':time})
def downgrade():raise RuntimeError('Destructive downgrade disabled')
