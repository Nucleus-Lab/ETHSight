import os
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from backend.database.models import VisualizationDB

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Database operations for visualization
def create_visualization(db, canvas_id: int, json_data: str, png_path: str, file_path: str):
    new_visualization = VisualizationDB(
        canvas_id=canvas_id,
        json_data=json_data,
        png_path=png_path,
        file_path=file_path,
        created_at=datetime.utcnow()
    )
    db.add(new_visualization)
    db.commit()
    db.refresh(new_visualization)
    return new_visualization

def update_visualization(db, visualization_id: int, canvas_id: int, json_data: str, png_path: str, file_path: str):
    visualization = db.query(VisualizationDB).filter(VisualizationDB.visualization_id == visualization_id).first()
    
    if not visualization:
        raise ValueError("Visualization not found")
    
    visualization.canvas_id = canvas_id
    visualization.json_data = json_data
    visualization.png_path = png_path
    visualization.file_path = file_path
    
    db.commit()
    db.refresh(visualization)
    return visualization

def get_visualization_by_id(db, visualization_id: int) -> VisualizationDB:
    return db.query(VisualizationDB)\
        .filter(VisualizationDB.visualization_id == visualization_id)\
        .first()

def get_visualizations_for_canvas(db, canvas_id: int) -> List[VisualizationDB]:
    return db.query(VisualizationDB)\
        .filter(VisualizationDB.canvas_id == canvas_id)\
        .order_by(VisualizationDB.created_at.asc())\
        .all()