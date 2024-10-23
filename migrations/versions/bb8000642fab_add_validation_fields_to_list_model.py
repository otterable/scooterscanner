"""Add validation fields to List model

Revision ID: bb8000642fab
Revises: 
Create Date: 2024-10-10 07:42:00.360696

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb8000642fab'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('list', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_validated', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('validation_timestamp', sa.DateTime(), nullable=True))

    with op.batch_alter_table('scan', schema=None) as batch_op:
        batch_op.alter_column('scooter_id',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.String(length=200),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('scan', schema=None) as batch_op:
        batch_op.alter_column('scooter_id',
               existing_type=sa.String(length=200),
               type_=sa.VARCHAR(length=100),
               existing_nullable=True)

    with op.batch_alter_table('list', schema=None) as batch_op:
        batch_op.drop_column('validation_timestamp')
        batch_op.drop_column('is_validated')

    # ### end Alembic commands ###