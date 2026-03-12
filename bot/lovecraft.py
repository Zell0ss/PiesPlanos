"""Bot Lovecraft — entry point.

Usage (from /data/PiesPlanos directory):
    source .venv/bin/activate
    export TELEGRAM_TOKEN=... DB_HOST=... DB_USER=... DB_PASSWORD=... DB_NAME=...
    python -m bot.lovecraft
"""
import asyncio
import logging
import os
from pathlib import Path

import aiomysql
import yaml
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import bot.handlers as handlers
from bot.db import init_db
from bot.session_manager import SessionManager

logger = logging.getLogger(__name__)


def load_game_cards(cards_path: str = "game_cards.yaml") -> list:
    """Load game case definitions from YAML."""
    with open(cards_path) as f:
        return yaml.safe_load(f)


async def main(config: dict) -> None:
    """Start the bot with the given configuration dict."""
    db_config = config["db"]
    pool = await aiomysql.create_pool(
        host=db_config["host"],
        port=db_config.get("port", 3306),
        user=db_config["user"],
        password=db_config["password"],
        db=db_config["database"],
        autocommit=False,
    )
    await init_db(pool)
    logger.info("MariaDB connection pool ready.")

    game_cards = load_game_cards()
    handlers.session_manager = SessionManager(
        pool=pool,
        game_cards=game_cards,
        ttl_minutes=config.get("session_ttl_minutes", 30),
    )
    handlers.portrait_root = Path(config.get("portrait_path", "game_data/images/npcs"))

    app = Application.builder().token(config["telegram_token"]).build()
    app.add_handler(CommandHandler("start", handlers.on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_message))

    logger.info("Bot Lovecraft starting...")
    await app.run_polling()


def build_config() -> dict:
    """Build config from environment variables (primary) or bot_config.yaml (fallback)."""
    load_dotenv()

    config_path = Path("bot_config.yaml")
    base: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            base = yaml.safe_load(f) or {}

    # Environment variables override file values
    token = os.environ.get("TELEGRAM_TOKEN") or base.get("telegram_token")
    db_password = os.environ.get("DB_PASSWORD") or base.get("db", {}).get("password")
    db_user = os.environ.get("DB_USER") or base.get("db", {}).get("user")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN not set in environment or bot_config.yaml")
    if not db_password:
        raise RuntimeError("DB_PASSWORD not set (set env var DB_PASSWORD)")
    if not db_user:
        raise RuntimeError("DB_USER not set (set env var DB_USER or add to bot_config.yaml)")

    config = {
        "telegram_token": token,
        "session_ttl_minutes": int(os.environ.get("SESSION_TTL_MINUTES",
                                                    base.get("session_ttl_minutes", 30))),
        "portrait_path": os.environ.get("PORTRAIT_PATH",
                                         base.get("portrait_path", "game_data/images/npcs")),
        "db": {
            "host": os.environ.get("DB_HOST", base.get("db", {}).get("host", "localhost")),
            "port": int(os.environ.get("DB_PORT", base.get("db", {}).get("port", 3306))),
            "user": db_user,
            "password": db_password,
            "database": os.environ.get("DB_NAME", base.get("db", {}).get("database", "piesplanos")),
        },
    }
    return config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(build_config()))
