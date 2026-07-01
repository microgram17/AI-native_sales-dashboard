from pydantic import BaseModel


class AgentRequest(BaseModel):
    supplier_code: str
    question: str


class AgentResponse(BaseModel):
    answer: str
    visualization: dict
    source: dict
