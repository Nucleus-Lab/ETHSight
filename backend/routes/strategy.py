from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import traceback
from backend.database import get_db
from backend.database.signal import get_signal_by_id
from backend.database.user import get_user
from backend.database.strategy import get_strategy_by_id

router = APIRouter()

class SignalInfo(BaseModel):
    signal_id: int
    signal_name: str
    signal_description: str
    
def get_signal_info(db: Session, signal_id: int) -> SignalInfo:
    """Helper function to get signal information from database"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal with id {signal_id} not found")
    
    return SignalInfo(
        signal_id=signal.signal_id,
        signal_name=signal.signal_name,
        signal_description=signal.signal_description
    )
    
def filter_token_info(filter_signal_name: str, filter_signal_description: str):
    """Get token information based on filter signal"""
    msg = f"""Get the token name, token symbol, and token contract address for the token that meets the {filter_signal_name} condition: {filter_signal_description}. 
    No visualization. I only want the csv data of the contract address. 
    The csv data should have the following columns: token_name, token_symbol, token_contract_address (no need to mind the column order)
    """
    from agents.controller import process_with_claude
    conversation_history = [
        {
            "role": "user",
            "content": msg
        }
    ]
    response = process_with_claude(conversation_history)
    print("response", response)
    token_name = None
    token_symbol = None
    token_contract_address = None
    for item in response:
        if item["role"] == "tool" and item["name"] == "get_data":
            print("item", item)
            print("item['result']", item["content"]['file_path'])
            print("item['result']", item["content"]['df_head'])
            print("item['result']", item["content"]['description'])
            import pandas as pd
            df = pd.read_csv(item["content"]['file_path'])
            print(df.head())
            print(df.columns)
            if "token_name" in df.columns:
                token_name = df.iloc[0]['token_name']
            if "token_symbol" in df.columns:
                token_symbol = df.iloc[0]['token_symbol']
            if "token_contract_address" in df.columns:
                token_contract_address = df.iloc[0]['token_contract_address']
            # early stop the loop if all three variables are found
            if token_name and token_symbol and token_contract_address:
                break
    return token_name, token_symbol, token_contract_address

@router.get("/strategy/user/{wallet_address}")
async def get_user_strategies(wallet_address: str, db: Session = Depends(get_db)):
    """Get all strategies for a specific user"""
    try:
        # Get user from wallet address
        user = get_user(db, wallet_address)
        if not user:
            return {
                "status": "success",
                "strategies": []
            }
        
        # Get strategies for the user
        from backend.database.strategy import get_strategies_by_user
        strategies = get_strategies_by_user(db, user.user_id)
        
        # Format strategies with signal information
        formatted_strategies = []
        for strategy in strategies:
            try:
                # Get signal information for each condition
                filter_signal = get_signal_info(db, strategy.filter_signal_id)
                buy_signal = get_signal_info(db, strategy.buy_condition_signal_id)
                sell_signal = get_signal_info(db, strategy.sell_condition_signal_id)
                
                formatted_strategy = {
                    "strategy_id": strategy.strategy_id,
                    "created_at": strategy.created_at.isoformat(),
                    "position_size": strategy.position_size,
                    "max_position_value": strategy.max_position_value,
                    "filter_condition": {
                        "signal_id": filter_signal.signal_id,
                        "signal_name": filter_signal.signal_name,
                        "signal_description": filter_signal.signal_description
                    },
                    "buy_condition": {
                        "signal_id": buy_signal.signal_id,
                        "signal_name": buy_signal.signal_name,
                        "signal_description": buy_signal.signal_description,
                        "operator": strategy.buy_condition_operator,
                        "threshold": strategy.buy_condition_threshold
                    },
                    "sell_condition": {
                        "signal_id": sell_signal.signal_id,
                        "signal_name": sell_signal.signal_name,
                        "signal_description": sell_signal.signal_description,
                        "operator": strategy.sell_condition_operator,
                        "threshold": strategy.sell_condition_threshold
                    }
                }
                formatted_strategies.append(formatted_strategy)
                
            except Exception as e:
                print(f"Error formatting strategy {strategy.strategy_id}: {e}")
                continue
        
        print(f"Retrieved {len(formatted_strategies)} strategies for user {user.user_id}")
        
        return {
            "status": "success",
            "strategies": formatted_strategies
        }
        
    except Exception as e:
        print(f"Error fetching user strategies: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch strategies: {str(e)}")

@router.get("/strategy/{strategy_id}")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Get a strategy by its ID"""
    try:
        strategy = get_strategy_by_id(db, strategy_id)
        print("strategy from db: ", strategy)
        
        # get the signal information for the strategy
        filter_signal = get_signal_info(db, strategy.filter_signal_id)
        buy_signal = get_signal_info(db, strategy.buy_condition_signal_id)
        sell_signal = get_signal_info(db, strategy.sell_condition_signal_id)
        
        # format the strategy
        formatted_strategy = {
            "strategy_id": strategy.strategy_id,
            "filterSignal": filter_signal,
            "buyCondition": {
                "signal": buy_signal,
                "operator": strategy.buy_condition_operator,
                "threshold": strategy.buy_condition_threshold
            },
            "sellCondition": {
                "signal": sell_signal,
                "operator": strategy.sell_condition_operator,
                "threshold": strategy.sell_condition_threshold
            },
            "positionSize": strategy.position_size,
            "maxPositionValue": strategy.max_position_value
        }
        if not strategy:
            return {
                "status": "failed",
                "strategy": None
            }
        return {
            "status": "success",
            "strategy": formatted_strategy
        }
    except Exception as e:
        print(f"Error fetching strategy by ID: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch strategy: {str(e)}")