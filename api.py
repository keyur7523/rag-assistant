from agent import run_agent
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

# 1. Define the incoming request shape
class AgentRequest(BaseModel):
    message: str = Field(
        ..., 
        description="The prompt or question for the AI agent."
    )

class AgentResponse(BaseModel):
    answer: str = Field(
        ..., 
        description="The final textual response from the agent."
    )
    tools_used: List[str] = Field(
        default_factory=list, 
        description="List of tools invoked during the execution."
    )
    iterations: int = Field(
        ..., 
        ge=0, 
        description="The number of reasoning loops or steps taken."
    )
    tool_details: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Detailed trace of tool inputs and outputs."
    )

@app.get("/health")
def health_status():
    return {"status": "ok"}

@app.post("/chat", response_model=AgentResponse)
def chat_endpoint(request: AgentRequest):
    try:
        answer, tools_used, iterations, hit_cap = run_agent(request.message)
        tool_names = [name for name, _ in tools_used]
        tool_details = [{"tool": name, "input": value} for name, value in tools_used]
        
        # 3. Construct and return the verified response structure.
        return AgentResponse(
            answer=answer,
            tools_used=tool_names,
            iterations=iterations,
            tool_details=tool_details,
        )
        
    except RuntimeError as err:
        # Map your agent execution failures to proper HTTP codes
        raise HTTPException(status_code=500, detail=str(err))