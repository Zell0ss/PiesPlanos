"""Tests for bot/db.py using mocked aiomysql connections."""
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# We'll mock at the aiomysql level — no real DB required
from bot.db import (
    init_db,
    get_player,
    upsert_player,
    get_player_state,
    upsert_player_state,
    get_npc_conversations,
    upsert_npc_conversation,
)


def make_mock_pool(fetchone_result=None, fetchall_result=None):
    """Build a mock aiomysql pool that returns preset query results."""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=fetchone_result)
    cursor.fetchall = AsyncMock(return_value=fetchall_result or [])
    cursor.execute = AsyncMock()
    cursor.lastrowid = 1
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=False)

    conn = AsyncMock()
    conn.cursor = MagicMock(return_value=cursor)
    conn.commit = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=conn)
    return pool, conn, cursor


@pytest.mark.asyncio
async def test_get_player_returns_none_when_missing():
    pool, conn, cursor = make_mock_pool(fetchone_result=None)
    result = await get_player(pool, telegram_id=12345)
    assert result is None


@pytest.mark.asyncio
async def test_get_player_returns_dict_when_found():
    row = (12345, "Lola", "The Invisible Cadaver", "2026-01-01", "2026-01-02")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player(pool, telegram_id=12345)
    assert result is not None
    assert result["telegram_id"] == 12345
    assert result["player_name"] == "Lola"
    assert result["case_id"] == "The Invisible Cadaver"


@pytest.mark.asyncio
async def test_upsert_player_calls_execute():
    pool, conn, cursor = make_mock_pool()
    await upsert_player(pool, telegram_id=12345, player_name="Lola",
                        case_id="The Invisible Cadaver")
    cursor.execute.assert_called_once()
    call_sql = cursor.execute.call_args[0][0]
    assert "INSERT" in call_sql or "REPLACE" in call_sql


@pytest.mark.asyncio
async def test_get_player_state_returns_none_when_missing():
    pool, conn, cursor = make_mock_pool(fetchone_result=None)
    result = await get_player_state(pool, telegram_id=12345)
    assert result is None


@pytest.mark.asyncio
async def test_get_player_state_deserializes_json():
    inv_json = json.dumps(["old_lighter"])
    visited_json = json.dumps(["jazz_street"])
    row = (12345, "jazz_street", inv_json, visited_json, "{}", "{}", "[]", "[]", "2026-01-01")
    pool, conn, cursor = make_mock_pool(fetchone_result=row)
    result = await get_player_state(pool, telegram_id=12345)
    assert result["inventory"] == ["old_lighter"]
    assert result["visited"] == ["jazz_street"]


@pytest.mark.asyncio
async def test_upsert_player_state_serializes_json():
    pool, conn, cursor = make_mock_pool()
    delta = {
        "current_location": "jazz_street",
        "inventory": ["old_lighter"],
        "visited": ["jazz_street"],
        "object_flags": {},
        "engine_flags": {},
        "discovered_clues": [],
        "clue_connections": [],
    }
    await upsert_player_state(pool, telegram_id=12345, delta=delta)
    cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_npc_conversations_returns_empty_dict_when_none():
    pool, conn, cursor = make_mock_pool(fetchall_result=[])
    result = await get_npc_conversations(pool, telegram_id=12345)
    assert result == {}


@pytest.mark.asyncio
async def test_get_npc_conversations_deserializes_history():
    history_json = json.dumps([{"timestamp": "t", "player_input": "hi",
                                "npc_response": "hello", "mood_state": "neutral",
                                "clues_revealed": []}])
    rows = [("jack", history_json)]
    pool, conn, cursor = make_mock_pool(fetchall_result=rows)
    result = await get_npc_conversations(pool, telegram_id=12345)
    assert "jack" in result
    assert result["jack"][0]["player_input"] == "hi"


@pytest.mark.asyncio
async def test_upsert_npc_conversation():
    pool, conn, cursor = make_mock_pool()
    history = [{"timestamp": "t", "player_input": "hi",
                "npc_response": "hello", "mood_state": "neutral", "clues_revealed": []}]
    await upsert_npc_conversation(pool, telegram_id=12345, npc_id="jack", history=history)
    cursor.execute.assert_called_once()
