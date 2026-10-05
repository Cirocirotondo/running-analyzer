from contextlib import asynccontextmanager

import redis as redis_sync
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rq import Queue
from sqlalchemy import text

from .db import engine
from .routers import admin, auth, me, sessions
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url)
    # RQ is synchronous; enqueueing is a single round trip, fine from async handlers.
    connection = redis_sync.from_url(settings.redis_url)
    app.state.queue = Queue("analysis", connection=connection)
    app.state.checks = Queue("checks", connection=connection)  # Recording Check, answered in seconds
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Running Analyzer API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, me.router, sessions.router, admin.router):
    app.include_router(r)


@app.get("/health")
async def health():
    """Reports whether the database and the queue are reachable."""
    async with engine.connect() as conn:
        db_ok = (await conn.execute(text("select 1"))).scalar() == 1
    redis_ok = await app.state.redis.ping()
    return {"status": "ok" if db_ok and redis_ok else "degraded", "db": db_ok, "redis": redis_ok}
