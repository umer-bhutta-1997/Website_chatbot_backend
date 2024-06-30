"""Add last_login column to users

Revision ID: da25f4031c3f
Revises: 
Create Date: 2023-08-17 12:53:39.863875

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da25f4031c3f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('mytable')
    op.drop_table('userdata')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_login', sa.DateTime(), server_default=sa.text('now()'), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_login')

    op.create_table('userdata',
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('password_hash', sa.TEXT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='userdata_pkey')
    )
    op.create_table('mytable',
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('password_hash', sa.TEXT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='mytable_pkey')
    )
    # ### end Alembic commands ###
