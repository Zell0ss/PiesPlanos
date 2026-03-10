from src.models.models import Door
from src.models.core_data import GameFlag


def test_door_connects_two_locations():
    door = Door(
        id="main_door", name="puerta principal",
        base_description="Una puerta de madera.",
        connects=("jazz_street", "jazz_club")
    )
    assert "jazz_street" in door.connects
    assert "jazz_club" in door.connects


def test_door_open_by_default_via_flag():
    door = Door(
        id="d", name="d", base_description="d",
        connects=("a", "b"),
        flags={GameFlag.OPEN}
    )
    assert door.has_flag(GameFlag.OPEN)


def test_door_locked_with_condition():
    door = Door(
        id="trap", name="trampilla",
        base_description="Una trampilla.",
        connects=("living_room", "cellar"),
        unlock_condition="found_secret_lever"
    )
    door.add_flag(GameFlag.LOCKED)
    assert door.has_flag(GameFlag.LOCKED)
    assert door.unlock_condition == "found_secret_lever"


def test_door_other_side():
    door = Door(
        id="d", name="d", base_description="d",
        connects=("room_a", "room_b")
    )
    assert door.other_side("room_a") == "room_b"
    assert door.other_side("room_b") == "room_a"
    assert door.other_side("room_c") is None
