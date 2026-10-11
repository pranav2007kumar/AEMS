from alembic import op
from sqlalchemy import inspect, text

revision = '0007_passenger_counts'
down_revision = '0006_monitoring'
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    for table in ('visits', 'registered_passages'):
        fields = {c['name'] for c in inspect(connection).get_columns(table)}
        for column in ('entry_person_count', 'exit_person_count'):
            if column not in fields:
                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} INTEGER'))

def downgrade():
    raise RuntimeError('Destructive downgrade disabled')
