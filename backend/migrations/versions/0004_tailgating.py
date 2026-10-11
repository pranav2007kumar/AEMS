from alembic import op
from backend.tailgating import BarrierCycle
revision='0004_tailgating'
down_revision='0003_occupancy'
branch_labels=None
depends_on=None
def upgrade():BarrierCycle.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():raise RuntimeError('Destructive downgrade disabled')
