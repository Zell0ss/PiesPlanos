# tests/models/test_item.py
import pytest
from src.models.models import Item
from src.models.core_data import GameFlag


def test_item_inherits_gameobject():
    item = Item(id="gun", name="pistola", base_description="Un revólver.")
    assert item.has_flag(GameFlag.TAKEABLE) == False


def test_item_fixed_flag_replaces_bool():
    item = Item(id="piano", name="piano", base_description="Un piano viejo.")
    item.add_flag(GameFlag.FIXED)
    assert item.has_flag(GameFlag.FIXED)
    assert not hasattr(item, "fixed")  # old attribute gone


def test_item_examined_flag():
    item = Item(id="body", name="cuerpo", base_description="Un cuerpo.")
    assert not item.has_flag(GameFlag.EXAMINED)
    item.add_flag(GameFlag.EXAMINED)
    assert item.has_flag(GameFlag.EXAMINED)


def test_item_clues_empty_by_default():
    item = Item(id="gun", name="pistola", base_description="Un revólver.")
    assert item.clues == []


def test_item_properties_dict():
    item = Item(
        id="gun",
        name="pistola",
        base_description="Un revólver.",
        properties={"ammo": "9mm", "bullets": "one fired"},
    )
    assert item.properties["ammo"] == "9mm"
