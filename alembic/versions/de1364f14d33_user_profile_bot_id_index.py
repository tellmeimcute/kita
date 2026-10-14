"""user profile bot id index

Revision ID: de1364f14d33
Revises: 300a39c811ff
Create Date: 2026-10-15 00:31:49.178253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de1364f14d33'
down_revision: Union[str, Sequence[str], None] = '300a39c811ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_user_profile_bot_id", "user_profile", ["bot_id", "id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_user_profile_bot_id", table_name="user_profile")
