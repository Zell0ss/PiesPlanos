# game_data/handlers/jazz_club.py
"""
Lifecycle hooks for the jazz_club location.
Loaded and registered automatically by the GameEngine on startup.

Hook signatures:
    on_enter(location, player, engine) -> None
    on_look(location, player, engine) -> None
    on_before_command(location, player, action, engine) -> str | None
    on_after_command(location, player, action, result, engine) -> None
"""
import logging

logger = logging.getLogger(__name__)


def on_enter(location, player, engine) -> None:
    """
    Called when player enters the jazz club.
    On first visit: activate blood_trail local-global in club and backstage.
    """
    if not location.visited:
        logger.debug("jazz_club: first visit — activating blood_trail")
        engine.global_registry.activate_local_global(
            "blood_trail", ["jazz_club", "backstage_corridor"]
        )


def on_look(location, player, engine) -> None:
    """
    Called when player examines the room description.
    Could vary description based on investigation state — placeholder for now.
    """
    pass


def on_before_command(location, player, action: dict, engine) -> str | None:
    """
    Called before any command executes in this location.
    Return a string to intercept the command result, or None to continue normally.
    """
    return None


def on_after_command(location, player, action: dict, result: str, engine) -> None:
    """
    Called after any command executes in this location.
    Can trigger follow-up events based on player actions.
    """
    pass
