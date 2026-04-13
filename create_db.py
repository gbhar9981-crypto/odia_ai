import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def create_database():
    try:
        # Connect to default postgres database to create odia_ai
        sys_conn = await asyncpg.connect(
            user='postgres',
            password='Prasant2457',
            host='localhost',
            port=5432,
            database='postgres'
        )
        
        db_name = "odia_ai"
        # Check if database exists
        exists = await sys_conn.fetchval(
            f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"
        )
        if not exists:
            print(f"Creating database {db_name}...")
            # create database cannot run inside a transaction block
            await sys_conn.execute(f'CREATE DATABASE "{db_name}"')
            print("Database created successfully!")
        else:
            print(f"Database {db_name} already exists.")
            
        await sys_conn.close()
    except Exception as e:
        print(f"Failed to create database: {e}")

if __name__ == "__main__":
    asyncio.run(create_database())
