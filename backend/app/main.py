from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import agent, auth, health, dashboard
from app.api.dependencies import close_agent_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_agent_service()


app = FastAPI(title="Retail BI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(agent.router)
app.include_router(dashboard.router)
