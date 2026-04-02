"""Telegram message handlers for Bot Lovecraft.

Routes:
  /start      → on_start()    — register player, start new game
  /ayuda      → on_ayuda()    — show help
  /activate   → on_activate() — admin: activate a pending player
  <text>      → on_message()  → SessionManager → GameEngine → response
"""

import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

import bot.db as db
from bot.portrait_service import get_portrait
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Set by lovecraft.py at startup
session_manager = None
portrait_root: Path = Path("game_data/images/npcs")
admin_id: int = None
DEFAULT_CASE_ID = "The Invisible Cadaver"

_PRESENTATION = (
    "🕵️ *Bot Lovecraft* — Detective noir de texto\n\n"
    "Eres un detective privado en el Chicago de los años 30.\n"
    "Un caso sin resolver. Una ciudad llena de sombras.\n\n"
    "Escribe */start* para comenzar la investigación.\n"
    "Escribe *ayuda* en cualquier momento para ver los comandos disponibles."
)

_AYUDA = (
    "*Comandos disponibles:*\n\n"
    "• *mirar* / *look* — examinar la habitación actual\n"
    "• *examinar <objeto>* — inspeccionar un objeto\n"
    "• *hablar con <personaje>* — iniciar conversación\n"
    "• *inventario* — ver lo que llevas\n"
    "• *ir <dirección/lugar>* — moverte a otro sitio\n"
    "• *coger <objeto>* — recoger un objeto\n\n"
    "Puedes escribir en español o inglés, en lenguaje natural.\n"
    "El detective interpreta tus palabras."
)


def _pending_message(chat_id: int, player_name: str) -> str:
    return (
        f"Bienvenido/a, {player_name}. Este bot es de acceso restringido.\n\n"
        f"Tu ID de Telegram es: `{chat_id}`\n"
        "Compártelo con el administrador para que te active."
    )


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register or present pending status."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"

    logger.info(f"/start from chat_id={chat_id} (admin_id={admin_id})")

    if chat_id == admin_id:
        # Admin is always active
        await db.upsert_player(
            session_manager._pool,
            chat_id,
            player_name,
            DEFAULT_CASE_ID,
            status="active",
        )
        await session_manager.get_or_create(
            chat_id=chat_id, player_name=player_name, case_id=DEFAULT_CASE_ID
        )
        await update.message.reply_text(
            f"Bienvenido/a, {player_name}. El caso te espera.\n\n"
            "Escribe *mirar* para comenzar a investigar.",
            parse_mode="Markdown",
        )
        return

    # Check if existing active player is re-starting
    player_row = await db.get_player(session_manager._pool, telegram_id=chat_id)
    if player_row and player_row["status"] == "active":
        await session_manager.get_or_create(
            chat_id=chat_id, player_name=player_name, case_id=DEFAULT_CASE_ID
        )
        await update.message.reply_text(
            f"Bienvenido/a de nuevo, {player_name}. Escribe *mirar* para continuar.",
            parse_mode="Markdown",
        )
        return

    # New or pending user
    await db.upsert_player(
        session_manager._pool, chat_id, player_name, DEFAULT_CASE_ID, status="pending"
    )
    session_manager._pending.setdefault(chat_id, 0)
    await update.message.reply_text(
        _pending_message(chat_id, player_name),
        parse_mode="Markdown",
    )


async def on_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ayuda command."""
    await update.message.reply_text(_AYUDA, parse_mode="Markdown")


async def on_activate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /activate <uid> — admin only."""
    chat_id = update.effective_chat.id

    logger.info(f"/activate from chat_id={chat_id} (admin_id={admin_id})")

    if chat_id != admin_id:
        await update.message.reply_text("No autorizado.")
        return

    if not context.args:
        await update.message.reply_text("Uso: /activate <telegram_uid>")
        return

    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("UID debe ser un número entero.")
        return

    try:
        name = await session_manager.activate(uid, context.bot)
        await update.message.reply_text(f"✅ {name} activado.")
    except ValueError as e:
        await update.message.reply_text(str(e))


async def on_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset — wipe saved state and restart from scratch."""
    chat_id = update.effective_chat.id
    await session_manager.reset(chat_id)
    await update.message.reply_text(
        "Partida reiniciada. Escribe */start* para comenzar de nuevo.",
        parse_mode="Markdown",
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a player text command."""
    chat_id = update.effective_chat.id
    player_name = update.effective_user.first_name or "Detective"
    text = update.message.text.strip()

    # 1. Help keywords — always respond, no auth required
    if text.lower() in ("ayuda", "help", "comandos", "?"):
        await update.message.reply_text(_AYUDA, parse_mode="Markdown")
        return

    # 2. Fast memory check: known pending user
    if chat_id in session_manager._pending:
        should_reply = await session_manager.handle_pending(chat_id)
        if should_reply:
            await update.message.reply_text(
                _pending_message(chat_id, player_name), parse_mode="Markdown"
            )
        return

    # 3. DB check for users not in memory
    status = await session_manager.get_player_status(chat_id)
    if status == "pending":
        session_manager._pending.setdefault(chat_id, 0)
        should_reply = await session_manager.handle_pending(chat_id)
        if should_reply:
            await update.message.reply_text(
                _pending_message(chat_id, player_name), parse_mode="Markdown"
            )
        return
    if status is None:
        await update.message.reply_text(_PRESENTATION, parse_mode="Markdown")
        return

    # 4. Active player — normal game flow
    try:
        engine = await session_manager.get_or_create(
            chat_id=chat_id, player_name=player_name, case_id=DEFAULT_CASE_ID
        )
    except Exception as e:
        logger.error(f"Session error for chat_id={chat_id}: {e}")
        await update.message.reply_text("Error iniciando sesión. Intenta /start.")
        return

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, engine.process_command, text)
    except Exception as e:
        logger.error(f"Engine error for chat_id={chat_id}: {e}")
        await update.message.reply_text("Error procesando comando.")
        return

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

    try:
        await session_manager.save(chat_id=chat_id, engine=engine)
    except Exception as e:
        logger.error(f"Save error for chat_id={chat_id}: {e}")


def _extract_npc_portrait(engine, response: str) -> dict | None:
    """Check if response came from NPC dialogue and return portrait info."""
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
