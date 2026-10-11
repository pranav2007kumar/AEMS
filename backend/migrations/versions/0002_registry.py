"""Registered faculty staff and daily vehicle access."""
from alembic import op
from backend.registry import RegisteredVehicle, RegisteredPassage
revision='0002_registry'
down_revision='0001_normalized'
branch_labels=None
depends_on=None
def upgrade():
    RegisteredVehicle.__table__.create(op.get_bind(),checkfirst=True)
    RegisteredPassage.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():raise RuntimeError('Destructive downgrade disabled')
