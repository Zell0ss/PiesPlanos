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
    def __init__(self, pool, game_cards: list, ttl_minutes: int = 30,
                 admin_id: int = None, pending_limit: int = 3):
        self._pool = pool
        self._game_cards = {card["name"]: card for card in game_cards}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict = {}  # {chat_id: {"engine": GameEngine, "last_active": datetime}}
        self._admin_id = admin_id
        self._pending: dict[int, int] = {}
        self._pending_limit = pending_limit

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

    async def has_session(self, chat_id: int) -> bool:
        """Return True if a session exists in memory or in the DB."""
        if chat_id in self._sessions:
            return True
        player_row = await db.get_player(self._pool, telegram_id=chat_id)
        return player_row is not None

    async def load_pending(self) -> None:
        """Populate _pending cache from DB. Call once at startup after init_db."""
        pending_ids = await db.get_pending_players(self._pool)
        self._pending = {chat_id: 0 for chat_id in pending_ids}

    async def handle_pending(self, chat_id: int) -> bool:
        """Increment attempt counter. Returns True if bot should reply, False for silence."""
        self._pending[chat_id] = self._pending.get(chat_id, 0) + 1
        return self._pending[chat_id] <= self._pending_limit

    async def get_player_status(self, chat_id: int) -> Optional[str]:
        """Return player status string ('pending'/'active') or None if no DB row."""
        row = await db.get_player(self._pool, telegram_id=chat_id)
        return row["status"] if row else None

    async def activate(self, chat_id: int, bot) -> str:
        """Activate a pending player. Notifies them via bot. Returns player_name.
        Raises ValueError if not found or already active.
        """
        name = await db.activate_player(self._pool, chat_id)
        self._pending.pop(chat_id, None)
        await bot.send_message(
            chat_id=chat_id,
            text="¡Tu acceso ha sido activado! Escribe /start para comenzar.",
        )
        return name

    async def reset(self, chat_id: int) -> None:
        """Wipe saved state for chat_id. Next get_or_create starts a fresh game."""
        self._sessions.pop(chat_id, None)
        await db.reset_player(self._pool, telegram_id=chat_id)

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
