"""convert_string_to_numeric_fields

Revision ID: 2d9b94defd5f
Revises: dfd91818580f
Create Date: 2025-06-06 11:36:38.877044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d9b94defd5f'
down_revision: Union[str, None] = 'dfd91818580f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
