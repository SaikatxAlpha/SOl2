import logging
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

log = logging.getLogger("solsight.db")

MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("MONGO_DB", "solsight")

# MONGO_URI=memory runs on an in-process mock (mongomock-motor). Data is lost
# on restart -- it's for demos and tests, not for real deployments.
IN_MEMORY = MONGO_URI.strip().lower() in ("memory", "mongomock://")

if IN_MEMORY:
    from mongomock_motor import AsyncMongoMockClient

    client = AsyncMongoMockClient()
    log.warning("MONGO_URI=memory: using an in-memory database, nothing will be persisted")
elif MONGO_URI:
    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
else:
    raise RuntimeError("MONGO_URI is not set (use MONGO_URI=memory for a throwaway local database)")

db = client[DB_NAME]

# Collections
users_collection = db["users"]
panels_collection = db["panels"]
inspections_collection = db["inspections"]


async def ensure_indexes():
    """Create indexes needed for fast lookups. Call once on app startup."""
    await users_collection.create_index("email", unique=True)
    await panels_collection.create_index("panel_id", unique=True)
    await panels_collection.create_index("owner_email")
    await inspections_collection.create_index(
        [("panel_id", 1), ("created_at", 1)]
    )


async def ping() -> bool:
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False
