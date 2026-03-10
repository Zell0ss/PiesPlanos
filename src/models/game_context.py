"""
GameContext - Encapsulates game state context for command processing

This class provides a centralized way to gather and cache game state information
needed for AI command interpretation and action handling.
"""

from typing import Dict, List, Optional, Any
from src.models.models import Location, Item, NPC, Player


class GameContext:
    """
    Encapsulates the current game state context for a player's action.

    Provides cached access to:
    - Current location
    - Available items (including player inventory items in the room)
    - NPCs in the current location
    - Available exits
    - Investigation progress

    The context caches data to avoid repeated queries and can be invalidated
    when the game state changes.
    """

    def __init__(self, game_engine):
        """
        Initialize context with reference to game engine.

        Args:
            game_engine: The GameEngine instance containing game state
        """
        self.engine = game_engine
        self._cached_data = {}

    @property
    def current_location(self) -> Location:
        """Get the current location object"""
        if 'location' not in self._cached_data:
            self._cached_data['location'] = self.engine.locations[
                self.engine.current_player.current_location
            ]
        return self._cached_data['location']

    @property
    def available_items(self) -> Dict[str, Item]:
        """
        Get all items available to the player in the current location.

        This includes:
        - Items physically in the room
        - Items in the player's inventory (carried by player, also in room)

        Returns:
            Dictionary mapping item_id to Item object
        """
        if 'items' not in self._cached_data:
            location = self.current_location
            # Get items in the location
            items_in_room = {
                key: value
                for key, value in self.engine.items.items()
                if key in location.children
            }

            # Add inventory items (they are in the room, carried by player)
            for item in self.engine.current_player.inventory:
                items_in_room[item.id] = item

            self._cached_data['items'] = items_in_room

        return self._cached_data['items']

    @property
    def npcs(self) -> Dict[str, NPC]:
        """
        Get NPCs in the current location.

        Returns:
            Dictionary mapping npc_id to NPC object
        """
        if 'npcs' not in self._cached_data:
            location = self.current_location
            npcs_in_location = {
                key: value
                for key, value in self.engine.npcs.items()
                if key in location.npcs
            }
            self._cached_data['npcs'] = npcs_in_location

        return self._cached_data['npcs']

    @property
    def exits(self) -> List:
        """Get available exits from current location"""
        if 'exits' not in self._cached_data:
            self._cached_data['exits'] = self.current_location.exits
        return self._cached_data['exits']

    @property
    def investigation_progress(self) -> int:
        """Get current investigation progress percentage"""
        if 'investigation_progress' not in self._cached_data:
            self._cached_data['investigation_progress'] = \
                self.engine.current_player.current_investigation.progress_percentage
        return self._cached_data['investigation_progress']

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary format for AI API calls.

        Returns:
            Dictionary with serialized context data suitable for AI processing
        """
        return {
            'location': self.current_location,
            'exits': self.exits,
            'items': self.available_items,
            'inventory': [item.name for item in self.engine.current_player.inventory],
            'investigation_progress': self.investigation_progress
        }

    def invalidate(self):
        """Clear cached data when game state changes"""
        self._cached_data.clear()
