from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, dashboard, health

app = FastAPI(title="Retail BI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(agent.router, prefix="/api/agent")