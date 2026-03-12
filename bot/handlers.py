"""Telegram message handlers for Bot Lovecraft.

Routes:
  /start  → on_start()    — register player, start new game
  <text>  → on_message()  → SessionManager → GameEngine → response
"""
import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.portrait_service import get_portrait

logger = logging.getLogger(__name__)

# These are set by lovecraft.py at startup
session_manager = None
portrait_root: Path = Path("game_data/images/npcs")
DEFAULT_CASE_ID = "The Invisible Cadaver"


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register player and initialise a new game session."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"

    await update.message.reply_text(
        f"Bienvenido/a, {player_name}. El caso te espera.\n\n"
        "Escribe cualquier cosa para comenzar a investigar."
    )

    await session_manager.get_or_create(
        chat_id=chat_id,
        player_name=player_name,
        case_id=DEFAULT_CASE_ID,
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a player text command."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"
    text = update.message.text

    try:
        engine = await session_manager.get_or_create(
            chat_id=chat_id,
            player_name=player_name,
            case_id=DEFAULT_CASE_ID,
        )
    except Exception as e:
        logger.error("Session error for chat_id=%s: %s", chat_id, e)
        await update.message.reply_text("Error iniciando sesión. Intenta /start.")
        return

    # Run sync GameEngine in a thread (GameEngine is not async)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, engine.process_command, text)
    except Exception as e:
        logger.error("Engine error for chat_id=%s: %s", chat_id, e)
        await update.message.reply_text("Error procesando comando.")
        return

    # Send portrait if this is NPC dialogue and NPC has a portrait
    npc_portrait = _extract_npc_portrait(engine, response)
    if npc_portrait:
        portrait_path = get_portrait(
            npc_id=npc_portrait["npc_id"],
            npc_portrait_filename=npc_portrait["filename"],
            portrait_root=portrait_root,
        )
        if portrait_path:
            with open(portrait_path, "rb") as f:
                await update.message.reply_photo(photo=f)

    await update.message.reply_text(response)

    # Auto-save delta
    try:
        await session_manager.save(chat_id=chat_id, engine=engine)
    except Exception as e:
        logger.error("Save error for chat_id=%s: %s", chat_id, e)
        # Don't crash the bot on save failure; player already got their response


def _extract_npc_portrait(engine, response: str) -> dict | None:
    """Check if response came from NPC dialogue and return portrait info.

    Returns {"npc_id": str, "filename": str} or None.
    This is a best-effort heuristic: check if current location has an NPC
    whose name appears in the response.
    """
    if not engine.current_player or not engine.npcs:
        return None
    current_loc_id = engine.current_player.current_location
    current_loc = engine.locations.get(current_loc_id)
    if not current_loc:
        return None
    for npc_id in getattr(current_loc, "npcs", []):
        npc = engine.npcs.get(npc_id)
        if npc and npc.name in response:
            portrait_filename = getattr(npc, "portrait", None)
            if portrait_filename:
                return {"npc_id": npc_id, "filename": portrait_filename}
    return None
