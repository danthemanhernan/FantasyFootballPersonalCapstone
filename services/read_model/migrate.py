from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg


async def migrate() -> None:
    connection = await asyncpg.connect(os.environ["POSTGRES_DSN"])
    try:
        await connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version TEXT PRIMARY KEY,
                   checksum TEXT NOT NULL,
                   applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
               )"""
        )
        root = Path(__file__).parent
        files = [root / "schema.sql", *sorted((root / "migrations").glob("*.sql"))]
        for path in files:
            sql = path.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            existing = await connection.fetchrow(
                "SELECT checksum FROM schema_migrations WHERE version = $1", path.name
            )
            if existing:
                if existing["checksum"] != checksum:
                    raise RuntimeError(f"applied migration changed: {path.name}")
                continue
            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                    path.name,
                    checksum,
                )
            print(f"applied {path.name}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(migrate())
