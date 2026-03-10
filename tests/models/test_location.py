# tests/models/test_location.py
from src.models.models import Location
from src.models.core_data import Exit, GameFlag


def test_location_inherits_gameobject():
    loc = Location(id="jazz_club", name="Jazz Club", base_description="El club.")
    assert loc.children == []
    assert loc.has_flag(GameFlag.LIT) == False


def test_location_items_in_children():
    loc = Location(
        id="jazz_club",
        name="Jazz Club",
        base_description="El club.",
        children=["piano", "body", "gun"],
    )
    assert "piano" in loc.children


def test_location_exits():
    exit_ = Exit(destination="jazz_street", name="puerta de entrada")
    loc = Location(
        id="jazz_club", name="Jazz Club", base_description="El club.", exits=[exit_]
    )
    assert len(loc.exits) == 1
    assert loc.exits[0].destination == "jazz_street"


def test_location_local_globals():
    loc = Location(
        id="jazz_club",
        name="Jazz Club",
        base_description="El club.",
        local_globals=["jazz_music", "main_door"],
    )
    assert "jazz_music" in loc.local_globals


def test_location_hooks_none_by_default():
    loc = Location(id="room", name="sala", base_description="Una sala.")
    assert loc.on_enter is None
    assert loc.on_look is None
    assert loc.on_before_command is None
    assert loc.on_after_command is None


def test_location_register_hook():
    loc = Location(id="room", name="sala", base_description="Una sala.")
    called = []

    def my_hook(location, player, engine):
        called.append(True)

    loc.on_enter = my_hook
    loc.on_enter(loc, None, None)
    assert called == [True]


def test_location_find_exit_by_name():
    exit_ = Exit(
        destination="jazz_street", name="puerta de entrada", aliases=["salida", "sur"]
    )
    loc = Location(
        id="jazz_club", name="Jazz Club", base_description="El club.", exits=[exit_]
    )
    found = loc.find_exit("salida")
    assert found is not None
    assert found.destination == "jazz_street"


def test_location_find_exit_not_found():
    loc = Location(id="room", name="sala", base_description="Una sala.")
    assert loc.find_exit("norte") is None
