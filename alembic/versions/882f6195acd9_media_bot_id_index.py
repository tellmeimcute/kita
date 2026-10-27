"""media bot id index

Revision ID: 882f6195acd9
Revises: de1364f14d33
Create Date: 2026-10-27 15:57:15.247696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '882f6195acd9'
down_revision: Union[str, Sequence[str], None] = 'de1364f14d33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_media_bot_id", "media", ["bot_id", "id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_media_bot_id", table_name="media")
