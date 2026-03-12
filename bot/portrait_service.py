"""Portrait service: resolve NPC portrait file paths.

Phase 1: static per-NPC images from game_data/images/npcs/
Phase 2 (future): room + portrait composite — add a compose_portrait() here.
"""
from pathlib import Path
from typing import Optional


def get_portrait(
    npc_id: str,
    npc_portrait_filename: Optional[str],
    portrait_root: Path,
) -> Optional[Path]:
    """Return the portrait file Path for an NPC, or None if unavailable.

    Args:
        npc_id: NPC identifier (used for logging only).
        npc_portrait_filename: value of the `portrait:` field in npcs.yaml, or None.
        portrait_root: directory where portrait images are stored.

    Returns:
        Path to the image file if it exists, else None.
    """
    if not npc_portrait_filename:
        return None
    path = Path(portrait_root) / npc_portrait_filename
    return path if path.exists() else None
