import sys
import os
# Add the backtest_utils directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.database.signal import get_signal_by_id, get_signal_calculation_code, signal_has_calculation_code, update_signal_calculation_code

# Import simplified interface functions
from backtest_utils.strategy_interface import (
    generate_signal_calculation_code_from_prompt,
    apply_signal_calculation_code,
    apply_condition_to_signal,
)

def get_or_generate_signal_calculation_code(db: Session, signal_id: int) -> str:
    """Get signal calculation code from database or generate if not exists (decoupled approach)"""
    # Check if signal has calculation code in database
    if signal_has_calculation_code(db, signal_id):
        print(f"✅ Using cached signal calculation code for signal {signal_id}")
        return get_signal_calculation_code(db, signal_id)
    
    # Generate new calculation code if not in database
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    print(f"🔄 Generating new signal calculation code for signal {signal_id}: {signal.signal_name}")
    
    try:
        # Generate the signal calculation code (decoupled from buy/sell logic)
        code = generate_signal_calculation_code_from_prompt(
            signal_description=signal.signal_description,
            signal_name=signal.signal_name
        )
        
        # Store the calculation code in database
        update_signal_calculation_code(db, signal_id, code)
        
        print("signal code", code)
        
        print(f"✅ Generated and cached signal calculation code for signal {signal_id}")
        return code
        
    except Exception as e:
        print(f"❌ Error generating signal calculation code for signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate signal calculation code: {str(e)}")


def prepare_signal_with_condition(df, signal_id: int, operator: str, threshold: float, condition_type: str, db: Session):
    """
    Prepare a signal by calculating signal values and applying conditions (decoupled approach)
    
    Args:
        df: DataFrame with OHLC data
        signal_id: Signal ID from database
        operator: Comparison operator
        threshold: Threshold value
        condition_type: 'buy' or 'sell'
        db: Database session
        
    Returns:
        tuple: (df_with_signals, signal_column_name)
    """
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    signal_name = signal.signal_name
    
    print(f"🔄 Preparing {condition_type} signal: {signal_name} {operator} {threshold}")
    
    # Make a copy of the DataFrame to preserve existing columns
    df_copy = df.copy()
    
    # Step 1: Get or generate signal calculation code (AI will check for existing columns)
    signal_calc_code = get_or_generate_signal_calculation_code(db, signal_id)
    
    # Step 2: Apply signal calculation code (AI will use existing column if found, or calculate new one)
    df_with_signal, signal_column = apply_signal_calculation_code(df_copy, signal_calc_code, signal_name)
    print(f"   🎯 Signal column ready: {signal_column}")
    
    # Step 3: Apply condition to generate buy/sell signals
    df_with_signal = apply_condition_to_signal(df_with_signal, signal_column, operator, threshold, condition_type)
    
    # Step 4: Verify all columns were preserved
    print(f"   📋 DataFrame columns after signal preparation: {list(df_with_signal.columns)}")
    
    return df_with_signal, signal_column