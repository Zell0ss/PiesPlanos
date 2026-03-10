"""
Simple test to verify GameContext implementation
"""

from src.models.game_context import GameContext
from src.models.models import Location, Item, NPC, Player, Investigation
from src.models.core_data import Exit


class MockGameEngine:
    """Mock game engine for testing"""

    def __init__(self):
        # Create test items
        self.items = {
            "desk": Item(id="desk", name="Desk", base_description="An old wooden desk"),
            "pen": Item(id="pen", name="Pen", base_description="A blue pen")
        }

        # Create test NPCs
        self.npcs = {
            "detective": NPC(
                id="detective",
                name="Detective",
                base_description="A seasoned detective",
                personality={"trait": "serious"}
            )
        }

        # Create test location
        self.locations = {
            "office": Location(
                id="office",
                name="Office",
                base_description="A small office",
                children=["desk"],  # Only desk is in the room
                npcs=["detective"]
            )
        }

        # Create test player
        self.current_player = Player(
            id="test_player",
            name="Test Player",
            current_location="office"
        )

        # Add pen to inventory (so it should be in available_items)
        self.current_player.inventory.append(self.items["pen"])

        # Create investigation
        self.current_player.current_investigation = Investigation(
            case_id="test_case",
            title="Test Case",
            description="A test investigation"
        )


def test_context():
    """Test GameContext functionality"""
    print("Testing GameContext implementation...\n")

    # Create mock engine
    engine = MockGameEngine()

    # Create context
    context = GameContext(engine)

    # Test current_location property
    print("1. Testing current_location property:")
    assert context.current_location.id == "office"
    print("   ✓ Current location is 'office'")

    # Test available_items (should include both room items and inventory)
    print("\n2. Testing available_items property:")
    items = context.available_items
    assert "desk" in items, "Desk should be in available items (in room)"
    assert "pen" in items, "Pen should be in available items (in inventory)"
    print(f"   ✓ Available items: {list(items.keys())}")

    # Test npcs property
    print("\n3. Testing npcs property:")
    npcs = context.npcs
    assert "detective" in npcs
    print(f"   ✓ NPCs in location: {list(npcs.keys())}")

    # Test exits property
    print("\n4. Testing exits property:")
    exits = context.exits
    print(f"   ✓ Exits: {exits}")

    # Test investigation_progress property
    print("\n5. Testing investigation_progress property:")
    progress = context.investigation_progress
    assert progress == 0, "Progress should be 0 initially"
    print(f"   ✓ Investigation progress: {progress}%")

    # Test to_dict method
    print("\n6. Testing to_dict() method:")
    context_dict = context.to_dict()
    assert "location" in context_dict
    assert "items" in context_dict
    assert "exits" in context_dict
    assert "inventory" in context_dict
    assert "investigation_progress" in context_dict
    print("   ✓ to_dict() returns all required keys")
    print(f"   - Inventory in dict: {context_dict['inventory']}")

    # Test caching
    print("\n7. Testing caching:")
    items1 = context.available_items
    items2 = context.available_items
    assert items1 is items2, "Should return cached items"
    print("   ✓ Context properly caches data")

    # Test invalidation
    print("\n8. Testing invalidation:")
    context.invalidate()
    items3 = context.available_items
    assert items1 is not items3, "Should return new items after invalidation"
    print("   ✓ Context invalidation works")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_context()
