"""Initial relational campus gate schema."""
from alembic import op
from backend.database import Base
from backend import models
revision='0001_normalized'
down_revision=None
branch_labels=None
depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): raise RuntimeError('Destructive downgrade disabled; restore a verified backup instead')
