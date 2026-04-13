import asyncio
from app.db.database import engine, Base
from app.models.models import User, Document, ChatThread, ChatMessage

async def main():
    async with engine.begin() as conn:
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
