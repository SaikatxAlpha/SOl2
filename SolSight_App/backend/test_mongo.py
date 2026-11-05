import asyncio
from app.db.mongo import client

async def test():
    result = await client.admin.command("ping")
    print(result)
    print("MongoDB connected")

asyncio.run(test())