"""SessionManager: per-user GameEngine instances with lazy TTL eviction.

Usage:
    manager = SessionManager(pool, game_cards, ttl_minutes=30)
    engine = await manager.get_or_create(chat_id, player_name, case_id)
    await manager.save(chat_id, engine)
"""
from datetime import datetime, timedelta
from typing import Optional

from src.engine import GameEngine
import bot.db as db


class SessionManager:
    def __init__(self, pool, game_cards: list, ttl_minutes: int = 30):
        self._pool = pool
        self._game_cards = {card["name"]: card for card in game_cards}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict = {}  # {chat_id: {"engine": GameEngine, "last_active": datetime}}

    async def get_or_create(
        self,
        chat_id: int,
        player_name: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> GameEngine:
        """Return an active GameEngine for chat_id.

        - If session is live and within TTL: return it directly.
        - If expired or missing: restore from DB (or start fresh for new players).
        """
        # Check in-memory session
        session = self._sessions.get(chat_id)
        if session and (datetime.now() - session["last_active"]) < self._ttl:
            session["last_active"] = datetime.now()
            return session["engine"]

        # Session expired or missing — restore from DB
        engine = await self._restore_or_create(chat_id, player_name, case_id)
        self._sessions[chat_id] = {"engine": engine, "last_active": datetime.now()}
        return engine

    async def save(self, chat_id: int, engine: GameEngine) -> None:
        """Persist current engine state as a delta. Called after every command."""
        delta = engine.extract_delta()
        npc_conversations = delta.pop("npc_conversations", {})

        await db.upsert_player_state(self._pool, telegram_id=chat_id, delta=delta)
        for npc_id, history in npc_conversations.items():
            await db.upsert_npc_conversation(
                self._pool, telegram_id=chat_id, npc_id=npc_id, history=history
            )
        await db.touch_player(self._pool, telegram_id=chat_id)

    # ── Private ────────────────────────────────────────────────────────────

    async def _restore_or_create(
        self,
        chat_id: int,
        player_name: Optional[str],
        case_id: Optional[str],
    ) -> GameEngine:
        player_row = await db.get_player(self._pool, telegram_id=chat_id)

        engine = GameEngine()

        if player_row is None:
            # Brand-new player
            card = self._game_cards.get(case_id)
            if card is None:
                raise ValueError(f"Unknown case_id: {case_id!r}")
            engine.start_new_game(player_name, case_id, game_data=card)
            await db.upsert_player(
                self._pool, telegram_id=chat_id,
                player_name=player_name, case_id=case_id
            )
        else:
            # Returning player — restore state
            pname = player_row["player_name"]
            pcaseid = player_row["case_id"]
            card = self._game_cards.get(pcaseid)
            if card is None:
                raise ValueError(f"Unknown case_id in DB: {pcaseid!r}")
            engine.start_new_game(pname, pcaseid, game_data=card)

            state = await db.get_player_state(self._pool, telegram_id=chat_id)
            npc_convs = await db.get_npc_conversations(self._pool, telegram_id=chat_id)

            if state:
                state["npc_conversations"] = npc_convs
                engine.apply_delta(state)

        return engine
