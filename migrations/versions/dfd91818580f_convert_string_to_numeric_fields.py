"""convert_string_to_numeric_fields

Revision ID: dfd91818580f
Revises: 
Create Date: 2025-06-06 11:36:23.127319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfd91818580f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert string columns to numeric types for exact precision in financial calculations."""
    
    # Convert strategies table columns
    print("Converting strategies table string columns to numeric...")
    
    # For buy_condition_threshold
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN buy_condition_threshold_new NUMERIC(20,8);
    """)
    
    # Convert existing string values to numeric, handling NULL and invalid values
    op.execute("""
        UPDATE strategies 
        SET buy_condition_threshold_new = 
            CASE 
                WHEN buy_condition_threshold IS NULL OR buy_condition_threshold = '' THEN NULL
                WHEN buy_condition_threshold ~ '^-?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$' THEN buy_condition_threshold::NUMERIC(20,8)
                ELSE NULL
            END;
    """)
    
    # Drop old column and rename new one
    op.drop_column('strategies', 'buy_condition_threshold')
    op.execute('ALTER TABLE strategies RENAME COLUMN buy_condition_threshold_new TO buy_condition_threshold')
    
    # For sell_condition_threshold
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN sell_condition_threshold_new NUMERIC(20,8);
    """)
    
    op.execute("""
        UPDATE strategies 
        SET sell_condition_threshold_new = 
            CASE 
                WHEN sell_condition_threshold IS NULL OR sell_condition_threshold = '' THEN NULL
                WHEN sell_condition_threshold ~ '^-?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$' THEN sell_condition_threshold::NUMERIC(20,8)
                ELSE NULL
            END;
    """)
    
    op.drop_column('strategies', 'sell_condition_threshold')
    op.execute('ALTER TABLE strategies RENAME COLUMN sell_condition_threshold_new TO sell_condition_threshold')
    
    # For position_size
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN position_size_new NUMERIC(20,8);
    """)
    
    op.execute("""
        UPDATE strategies 
        SET position_size_new = 
            CASE 
                WHEN position_size IS NULL OR position_size = '' THEN NULL
                WHEN position_size ~ '^-?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$' THEN position_size::NUMERIC(20,8)
                ELSE NULL
            END;
    """)
    
    op.drop_column('strategies', 'position_size')
    op.execute('ALTER TABLE strategies RENAME COLUMN position_size_new TO position_size')
    
    # For max_position_value
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN max_position_value_new NUMERIC(20,2);
    """)
    
    op.execute("""
        UPDATE strategies 
        SET max_position_value_new = 
            CASE 
                WHEN max_position_value IS NULL OR max_position_value = '' THEN NULL
                WHEN max_position_value ~ '^-?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$' THEN max_position_value::NUMERIC(20,2)
                ELSE NULL
            END;
    """)
    
    op.drop_column('strategies', 'max_position_value')
    op.execute('ALTER TABLE strategies RENAME COLUMN max_position_value_new TO max_position_value')
    
    # Convert backtest_histories table columns
    print("Converting backtest_histories table float columns to numeric...")
    
    # For total_return (previously FLOAT)
    op.execute("""
        ALTER TABLE backtest_histories 
        ADD COLUMN total_return_new NUMERIC(15,8);
    """)
    
    op.execute("""
        UPDATE backtest_histories 
        SET total_return_new = total_return::NUMERIC(15,8)
        WHERE total_return IS NOT NULL;
    """)
    
    op.drop_column('backtest_histories', 'total_return')
    op.execute('ALTER TABLE backtest_histories RENAME COLUMN total_return_new TO total_return')
    
    # For avg_return (previously FLOAT)
    op.execute("""
        ALTER TABLE backtest_histories 
        ADD COLUMN avg_return_new NUMERIC(15,8);
    """)
    
    op.execute("""
        UPDATE backtest_histories 
        SET avg_return_new = avg_return::NUMERIC(15,8)
        WHERE avg_return IS NOT NULL;
    """)
    
    op.drop_column('backtest_histories', 'avg_return')
    op.execute('ALTER TABLE backtest_histories RENAME COLUMN avg_return_new TO avg_return')
    
    # For win_rate (previously FLOAT) - adjusted precision for percentage values (0-100)
    op.execute("""
        ALTER TABLE backtest_histories 
        ADD COLUMN win_rate_new NUMERIC(6,4);
    """)
    
    op.execute("""
        UPDATE backtest_histories 
        SET win_rate_new = win_rate::NUMERIC(6,4)
        WHERE win_rate IS NOT NULL;
    """)
    
    op.drop_column('backtest_histories', 'win_rate')
    op.execute('ALTER TABLE backtest_histories RENAME COLUMN win_rate_new TO win_rate')
    
    print("Migration completed successfully!")


def downgrade() -> None:
    """Downgrade schema by converting numeric columns back to string/float."""
    
    print("Reverting numeric columns back to original types...")
    
    # Revert strategies table columns back to string
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN buy_condition_threshold_old TEXT;
    """)
    
    op.execute("""
        UPDATE strategies 
        SET buy_condition_threshold_old = buy_condition_threshold::TEXT
        WHERE buy_condition_threshold IS NOT NULL;
    """)
    
    op.drop_column('strategies', 'buy_condition_threshold')
    op.execute('ALTER TABLE strategies RENAME COLUMN buy_condition_threshold_old TO buy_condition_threshold')
    
    # sell_condition_threshold
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN sell_condition_threshold_old TEXT;
    """)
    
    op.execute("""
        UPDATE strategies 
        SET sell_condition_threshold_old = sell_condition_threshold::TEXT
        WHERE sell_condition_threshold IS NOT NULL;
    """)
    
    op.drop_column('strategies', 'sell_condition_threshold')
    op.execute('ALTER TABLE strategies RENAME COLUMN sell_condition_threshold_old TO sell_condition_threshold')
    
    # position_size
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN position_size_old TEXT;
    """)
    
    op.execute("""
        UPDATE strategies 
        SET position_size_old = position_size::TEXT
        WHERE position_size IS NOT NULL;
    """)
    
    op.drop_column('strategies', 'position_size')
    op.execute('ALTER TABLE strategies RENAME COLUMN position_size_old TO position_size')
    
    # max_position_value
    op.execute("""
        ALTER TABLE strategies 
        ADD COLUMN max_position_value_old TEXT;
    """)
    
    op.execute("""
        UPDATE strategies 
        SET max_position_value_old = max_position_value::TEXT
        WHERE max_position_value IS NOT NULL;
    """)
    
    op.drop_column('strategies', 'max_position_value')
    op.execute('ALTER TABLE strategies RENAME COLUMN max_position_value_old TO max_position_value')
    
    # Revert backtest_histories table columns back to float
    # total_return
    op.execute("""
        ALTER TABLE backtest_histories 
        ADD COLUMN total_return_old FLOAT;
    """)
    
    op.execute("""
        UPDATE backtest_histories 
        SET total_return_old = total_return::FLOAT
        WHERE total_return IS NOT NULL;
    """)
    
    op.drop_column('backtest_histories', 'total_return')
    op.execute('ALTER TABLE backtest_histories RENAME COLUMN total_return_old TO total_return')
    
    # avg_return
    op.execute("""
        ALTER TABLE backtest_histories 
        ADD COLUMN avg_return_old FLOAT;
    """)
    
    op.execute("""
        UPDATE backtest_histories 
        SET avg_return_old = avg_return::FLOAT
        WHERE avg_return IS NOT NULL;
    """)
    
    op.drop_column('backtest_histories', 'avg_return')
    op.execute('ALTER TABLE backtest_histories RENAME COLUMN avg_return_old TO avg_return')
    
    # win_rate
    op.execute("""
        ALTER TABLE backtest_histories 
        ADD COLUMN win_rate_old FLOAT;
    """)
    
    op.execute("""
        UPDATE backtest_histories 
        SET win_rate_old = win_rate::FLOAT
        WHERE win_rate IS NOT NULL;
    """)
    
    op.drop_column('backtest_histories', 'win_rate')
    op.execute('ALTER TABLE backtest_histories RENAME COLUMN win_rate_old TO win_rate')
    
    print("Downgrade completed successfully!")
