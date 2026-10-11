from alembic import op
from backend.anpr import PlateDetection
revision='0005_anpr_output'
down_revision='0004_tailgating'
branch_labels=None
depends_on=None
def upgrade():PlateDetection.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():raise RuntimeError('Destructive downgrade disabled')
