import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import mongo
from app.demo_data import seed_demo_fleet
from app.routers import auth, panels, inspections
from app.services.prediction_service import prediction_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("solsight")

# Comma-separated list, e.g. "http://localhost:5173,https://solsight.example.com"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

DEMO_EMAIL = "admin@solsight.com"
DEMO_PASSWORD = "admin123"


async def _seed_demo_user():
    """In-memory mode starts empty on every boot; give it a login to use."""
    if await mongo.users_collection.find_one({"email": DEMO_EMAIL}):
        return
    await mongo.users_collection.insert_one({
        "name": "Admin",
        "email": DEMO_EMAIL,
        "hashed_password": auth.hash_password(DEMO_PASSWORD),
        "created_at": datetime.utcnow(),
    })
    log.info("in-memory mode: created demo user %s", DEMO_EMAIL)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await mongo.ensure_indexes()
        if mongo.IN_MEMORY:
            await _seed_demo_user()
            if os.getenv("SEED_DEMO_FLEET", "true").lower() == "true":
                await seed_demo_fleet(mongo.panels_collection, mongo.inspections_collection, DEMO_EMAIL)
    except Exception as e:
        # Don't refuse to boot -- /health will report the database as down.
        log.error("database not reachable at startup: %s", e)
    yield


app = FastAPI(
    title="SolSight API",
    description="Solar panel defect detection, health monitoring, and degradation prediction.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(panels.router)
app.include_router(inspections.router)


@app.get("/")
async def root():
    return {"service": "SolSight API", "status": "running"}


@app.get("/health")
async def health_check():
    db_ok = await mongo.ping()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "in-memory" if mongo.IN_MEMORY else ("up" if db_ok else "down"),
        "models_trained": prediction_service.trained,
    }
