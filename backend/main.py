from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import canvas_router, user_router, message_router, visualization_router, mcp_router, signal_router
from backend.database.init_db import init_db

# Initialize the database
init_db()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(canvas_router)
app.include_router(user_router)
app.include_router(message_router)
app.include_router(visualization_router)
app.include_router(mcp_router)
app.include_router(signal_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)