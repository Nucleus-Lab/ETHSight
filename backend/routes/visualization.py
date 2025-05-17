from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db 
from backend.database.visualization import get_visualizations_for_canvas, get_visualization_by_id

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import JSONResponse

router = APIRouter()

class VisualizationResponse(BaseModel):
    visualization_id: int
    json_data: dict
    png_path: str
    created_at: datetime
    
@router.get("/canvas/{canvas_id}/first-visualization", response_model=Optional[VisualizationResponse])
async def get_canvas_first_visualization(
    canvas_id: int,
    db: Session = Depends(get_db)
):
    visualizations = get_visualizations_for_canvas(db, canvas_id)
    print("visualizations in get_canvas_first_visualization: ", visualizations)
    if not visualizations:
        return None
    return visualizations[0]

@router.get("/canvas/{canvas_id}/visualizations", response_model=List[VisualizationResponse])
async def get_canvas_visualizations(
    canvas_id: int, 
    db: Session = Depends(get_db)
):
    visualizations = get_visualizations_for_canvas(db, canvas_id)
    return visualizations

@router.get("/visualization/{visualization_id}")
async def get_visualization(
    visualization_id: int,
    db: Session = Depends(get_db)
):
    # Add logging here
    print(f"Received request for visualization {visualization_id}")
    
    try:
        # Your existing code...
        visualization = get_visualization_by_id(db, visualization_id)
        
        print("visualization from db: ", visualization)
        
        if not visualization:
            return JSONResponse(
                content={"error": f"Visualization {visualization_id} not found"},
                status_code=404
            )
            
        # Log the data being sent
        # print(f"Sending visualization data: {visualization.json_data}")
        
        return JSONResponse(
            content=visualization.json_data,
            status_code=200
        )
        
    except Exception as e:
        print(f"Error getting visualization: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

