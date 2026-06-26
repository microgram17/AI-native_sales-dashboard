from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgentRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: AgentRequest) -> dict:
    return {
        "answer": f"Agent skeleton received: {request.message}",
        "chart": None,
    }