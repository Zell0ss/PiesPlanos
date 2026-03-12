"""Async MariaDB persistence layer for Bot Lovecraft.

All functions accept an aiomysql.Pool as first argument.
Schema is created by init_db() on bot startup.
"""
import json
from typing import Optional

import aiomysql


# ── Schema ─────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    telegram_id   BIGINT PRIMARY KEY,
    player_name   VARCHAR(100) NOT NULL,
    case_id       VARCHAR(50)  NOT NULL,
    created_at    DATETIME DEFAULT NOW(),
    last_active   DATETIME DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_state (
    telegram_id      BIGINT PRIMARY KEY,
    current_location VARCHAR(50) NOT NULL,
    inventory        JSON,
    visited          JSON,
    object_flags     JSON,
    engine_flags     JSON,
    discovered_clues JSON,
    clue_connections JSON,
    updated_at       DATETIME DEFAULT NOW(),
    FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
);

CREATE TABLE IF NOT EXISTS npc_conversations (
    telegram_id BIGINT,
    npc_id      VARCHAR(50),
    history     JSON,
    updated_at  DATETIME DEFAULT NOW(),
    PRIMARY KEY (telegram_id, npc_id)
);
"""


async def init_db(pool: aiomysql.Pool) -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    async with pool.acquire() as conn:
        for statement in _SCHEMA_SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                async with conn.cursor() as cursor:
                    await cursor.execute(stmt)
        await conn.commit()


# ── Players ────────────────────────────────────────────────────────────────

async def get_player(pool: aiomysql.Pool, telegram_id: int) -> Optional[dict]:
    """Return player row as dict, or None if not found."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT telegram_id, player_name, case_id, created_at, last_active "
                "FROM players WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "telegram_id": row[0],
        "player_name": row[1],
        "case_id": row[2],
        "created_at": row[3],
        "last_active": row[4],
    }


async def upsert_player(
    pool: aiomysql.Pool,
    telegram_id: int,
    player_name: str,
    case_id: str,
) -> None:
    """Insert or update player record, refreshing last_active."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO players (telegram_id, player_name, case_id) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE player_name = VALUES(player_name), "
                "last_active = NOW()",
                (telegram_id, player_name, case_id),
            )
        await conn.commit()


async def touch_player(pool: aiomysql.Pool, telegram_id: int) -> None:
    """Update last_active timestamp for a player."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE players SET last_active = NOW() WHERE telegram_id = %s",
                (telegram_id,),
            )
        await conn.commit()


# ── Player State ───────────────────────────────────────────────────────────

async def get_player_state(pool: aiomysql.Pool, telegram_id: int) -> Optional[dict]:
    """Return deserialized player state delta, or None if not found."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT telegram_id, current_location, inventory, visited, "
                "object_flags, engine_flags, discovered_clues, clue_connections, updated_at "
                "FROM player_state WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "current_location": row[1],
        "inventory": json.loads(row[2]) if row[2] else [],
        "visited": json.loads(row[3]) if row[3] else [],
        "object_flags": json.loads(row[4]) if row[4] else {},
        "engine_flags": json.loads(row[5]) if row[5] else {},
        "discovered_clues": json.loads(row[6]) if row[6] else [],
        "clue_connections": json.loads(row[7]) if row[7] else [],
    }


async def upsert_player_state(
    pool: aiomysql.Pool,
    telegram_id: int,
    delta: dict,
) -> None:
    """Persist a delta dict to player_state. Creates or replaces the row."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "REPLACE INTO player_state "
                "(telegram_id, current_location, inventory, visited, "
                "object_flags, engine_flags, discovered_clues, clue_connections) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    telegram_id,
                    delta["current_location"],
                    json.dumps(delta.get("inventory", [])),
                    json.dumps(delta.get("visited", [])),
                    json.dumps(delta.get("object_flags", {})),
                    json.dumps(delta.get("engine_flags", {})),
                    json.dumps(delta.get("discovered_clues", [])),
                    json.dumps(delta.get("clue_connections", [])),
                ),
            )
        await conn.commit()


# ── NPC Conversations ──────────────────────────────────────────────────────

async def get_npc_conversations(
    pool: aiomysql.Pool,
    telegram_id: int,
) -> dict:
    """Return {npc_id: list[entry_dict]} for all NPCs for a player."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT npc_id, history FROM npc_conversations WHERE telegram_id = %s",
                (telegram_id,),
            )
            rows = await cursor.fetchall()
    return {
        row[0]: json.loads(row[1]) if row[1] else []
        for row in rows
    }


async def upsert_npc_conversation(
    pool: aiomysql.Pool,
    telegram_id: int,
    npc_id: str,
    history: list,
) -> None:
    """Persist NPC conversation history. Creates or replaces the row."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "REPLACE INTO npc_conversations (telegram_id, npc_id, history) "
                "VALUES (%s, %s, %s)",
                (telegram_id, npc_id, json.dumps(history)),
            )
        await conn.commit()
