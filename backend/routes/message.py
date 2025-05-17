from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import json

from backend.database import get_db
from backend.database.user import get_user, create_user
from backend.database.canvas import get_canvas, create_canvas
from backend.database.visualization import create_visualization, get_visualization_by_id, update_visualization
from backend.constants import AI_USER_ID
from backend.database.message import create_message, get_messages_for_canvas, get_message_by_id

# from agents.main import main as agent_main
from agents.controller import process_with_claude

router = APIRouter()

class MessageRequest(BaseModel):
    canvas_id: Optional[int] = None
    wallet_address: str  # Changed from user_id
    text: str
    mentioned_visualization_ids: Optional[List[int]] = None
    
    
class MessageResponse(BaseModel):
    message_id: int
    canvas_id: int
    text: str
    created_at: datetime
    user_id: int

class SignalData(BaseModel):
    signal_id: str
    signal_definition: str

class MessageResponseWithAIResponse(BaseModel):
    message_id: int
    canvas_id: int
    text: str
    created_at: datetime
    visualization_ids: List[int]
    ai_message_id: int
    signals: List[SignalData] = []
    
@router.post("/message", response_model=MessageResponseWithAIResponse)
async def send_message(
    message: MessageRequest,
    db: Session = Depends(get_db)
):
    try:
        # Get or create user from wallet address
        user = get_user(db, message.wallet_address)
        if not user:
            user = create_user(db, message.wallet_address)

        # If no canvas_id, create new canvas
        if message.canvas_id is None:
            canvas = create_canvas(db, user.user_id)
            print("created new canvas: ", canvas.canvas_id)
        else:
            # Get existing canvas
            canvas = get_canvas(db, message.canvas_id)
            if not canvas:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Canvas with id {message.canvas_id} not found"
                )
            
            # Verify user has access to this canvas
            if canvas.user_id != user.user_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to access this canvas"
                )
        
        # Get conversation history for this canvas
        conversation_history = []
        previous_messages = get_messages_for_canvas(db, canvas.canvas_id)
        for msg in previous_messages:
            role = "assistant" if msg.user_id == AI_USER_ID else "user"
            conversation_history.append({
                "role": role,
                "content": msg.text
            })
        
        # Create the message
        new_message = create_message(
            db,
            canvas_id=canvas.canvas_id,
            user_id=user.user_id,
            text=message.text
        )
        
        # Add current message to conversation history
        conversation_history.append({
            "role": "user",
            "content": message.text
        })
        
        # Process mentioned visualization IDs if provided
        mentioned_visualizations = []
        if message.mentioned_visualization_ids and len(message.mentioned_visualization_ids) > 0:
            print(f"Processing mentioned visualization IDs: {message.mentioned_visualization_ids}")
            for viz_id in message.mentioned_visualization_ids:
                visualization = get_visualization_by_id(db, viz_id)
                if visualization:
                    mentioned_visualizations.append({
                        "visualization_id": visualization.visualization_id,
                        "png_path": visualization.png_path,
                        "json_data": visualization.json_data,
                        "file_path": visualization.file_path
                    })
                    print(f"Found visualization with ID {viz_id}: {visualization.png_path}")
                else:
                    print(f"Visualization with ID {viz_id} not found")
        
        # TODO: use dummy results for now
        # Pass mentioned visualizations to the agent
        # a list of conversation
        results = process_with_claude(
            message.text,
        )
        
        ai_message_text = ""
        visualization_ids = []  # empty list for visualization ids
        for result in results:
            # if role is tool, then parse the result accordingly
            if result['role'] == 'tool':
                if result['name'] == 'visualize':
                    
                    print("result['content']: ", result['content'])
                    print("type(result['content']): ", type(result['content']))
                    print("result.keys(): ", result.keys())
                    
                    
                    json_data = json.loads(result['content'])
                    # TODO: save, get file path and output png path & change the parameters in create_visualization
                    # Save the json visualization to the database
                    visualization = create_visualization(db, canvas.canvas_id, json_data, "", "")
                    visualization_ids.append(visualization.visualization_id)
            else:
                # append all the text messages
                ai_message_text += result['content']
                    
                    
                    
        
        # results = await agent_main(
        #     message.text, 
        #     conversation_history,
        #     mentioned_visualizations=mentioned_visualizations
        # )
        
        # if results["action"] == "GENERAL_CHAT":
        #     ai_message_text = results["message"]
            
        # elif results["action"] == "RETRIEVE_AND_VISUALIZE_INFORMATION":
        #     visualization_results_list = results["visualization_results_list"]
        #     print("visualization_results_list: ", visualization_results_list)
            
        #     img_paths = []
            
        #     for viz_result in visualization_results_list:
        #         # Parse the json data
        #         json_data = json.loads(viz_result['fig_json'])
        #         # Save the json visualization to the database
        #         visualization = create_visualization(db, canvas.canvas_id, json_data, viz_result["output_png_path"], viz_result["file_path"])
        #         visualization_ids.append(visualization.visualization_id)
        #         # To be used for analysis later
        #         img_paths.append(viz_result["output_png_path"])
                
        #     # call the ai agent again to get the analysis
        #     prompt = "Please analyze the figures and reply the user. Here is the user's original prompt: " + message.text + ". Here is the img paths for the generated figures: " + ", ".join(img_paths)
        #     second_ai_results = await agent_main(prompt)
        #     ai_message_text = second_ai_results["analysis"]
            
        # elif results["action"] == "ANALYZE_GRAPH":
        #     ai_message_text = results["analysis"]
            
        # elif results["action"] == "MODIFY_VISUALIZATION":
        #     modification_results_list = results["modification_results_list"]
            
        #     img_paths = []
            
        #     for mod_result in modification_results_list:
        #         if mod_result["success"]:
        #             # Parse the json data
        #             json_data = json.loads(mod_result['fig_json'])
        #             # Save the json data to update the visualization
        #             visualization = update_visualization(db, mod_result["visualization_id"], canvas.canvas_id, json_data, mod_result["output_png_path"], mod_result["file_path"])
        #             visualization_ids.append(visualization.visualization_id)   # which is the original visualization id since this is an update
        #             # to be used for analysis later
        #             img_paths.append(mod_result["output_png_path"])
                    
        #     # call the ai agent again to get the analysis
        #     prompt = "You have already modified the figure(s). Now, please analyze the modified figure(s) and reply the user. Here is the user's original prompt: " + message.text + ". Here is the img paths for the modified figures: " + ", ".join(img_paths)
        #     second_ai_results = await agent_main(prompt)
        #     ai_message_text = second_ai_results["analysis"]
                
        # else:
        #     raise HTTPException(status_code=400, detail="Invalid action")
            
        # Save the analysis as a message from the AI to the database
        ai_message = create_message(
            db,
            canvas_id=canvas.canvas_id,
            user_id=AI_USER_ID,
            text=ai_message_text
        )
        
        # TODO:
        # Create dummy signal data for now
        # Will later be populated with real data from the AI agent
        signals = []
        if "bitcoin" in message.text.lower() or "crypto" in message.text.lower():
            # Example: Add a dummy signal if user mentions bitcoin or crypto
            signals.append({
                "signal_id": f"temp_signal_{new_message.message_id}",
                "signal_definition": f"Price crossover signal derived from {message.text}"
            })
        
        print("sending these as response: ", {
            "message_id": new_message.message_id,
            "canvas_id": canvas.canvas_id,  # Include the canvas_id here
            "text": new_message.text,
            "created_at": new_message.created_at,
            "visualization_ids": visualization_ids,
            "ai_message_id": ai_message.message_id,
            "signals": signals  # Add the signals to the response
        })
            
        # Make sure the response includes the canvas_id
        return {
            "message_id": new_message.message_id,
            "canvas_id": canvas.canvas_id,  # Include the canvas_id here
            "text": new_message.text,
            "created_at": new_message.created_at,
            "visualization_ids": visualization_ids,
            "ai_message_id": ai_message.message_id,
            "signals": signals  # Add the signals to the response
        }

    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.get("/canvas/{canvas_id}/messages", response_model=List[MessageResponse])
async def get_canvas_messages(
    canvas_id: int,
    db: Session = Depends(get_db)
):
    messages = get_messages_for_canvas(db, canvas_id)
    return [{
        "message_id": msg.message_id,
        "canvas_id": msg.canvas_id,
        "text": msg.text,
        "created_at": msg.created_at,
        "user_id": msg.user_id,  # Make sure this is included
    } for msg in messages]

@router.get("/canvas/{canvas_id}/first-message", response_model=Optional[MessageResponse])
async def get_canvas_first_message(
    canvas_id: int,
    db: Session = Depends(get_db)
):
    messages = get_messages_for_canvas(db, canvas_id)
    if not messages:
        return None
    return messages[0]


@router.get("/message/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    try:
        message = get_message_by_id(db, message_id)
        if not message:
            raise HTTPException(
                status_code=404,
                detail=f"Message with id {message_id} not found"
            )
            
        print("message.message_id: ", message.message_id)
        print("message.text: ", message.text)
        print("message.created_at: ", message.created_at)
        print("message.user_id: ", message.user_id)
        print("message.canvas_id: ", message.canvas_id)
        return {
            "message_id": message.message_id,
            "canvas_id": message.canvas_id,
            "text": message.text,
            "created_at": message.created_at,
            "user_id": message.user_id
        }
    except Exception as e:
        print(f"Error getting message: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")