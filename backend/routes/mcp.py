from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

# Store current MCP server selection
current_mcp_server = "nodit"  # default to nodit

class MCPServer(BaseModel):
    name: str
    description: str

# Available MCP servers
MCP_SERVERS = [
    MCPServer(name="nodit", description="Nodit API"),
    MCPServer(name="1inch", description="1inch API"),
    MCPServer(name="zircuit", description="Zircuit API")
]

@router.get("/mcp/servers", response_model=List[MCPServer])
async def get_mcp_servers():
    """Get list of available MCP servers"""
    return MCP_SERVERS

@router.get("/mcp/current")
async def get_current_mcp():
    """Get current MCP server"""
    return {"current_server": current_mcp_server}

@router.post("/mcp/select/{server_name}")
async def select_mcp_server(server_name: str):
    """Select MCP server to use"""
    if server_name not in [server.name for server in MCP_SERVERS]:
        raise HTTPException(status_code=400, detail=f"Invalid MCP server: {server_name}")
    
    global current_mcp_server
    current_mcp_server = server_name
    return {"message": f"Switched to {server_name} MCP server"}
