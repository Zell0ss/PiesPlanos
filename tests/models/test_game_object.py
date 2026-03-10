# tests/models/test_game_object.py
import pytest
from src.models.core_data import GameFlag, GameObject

def test_gameobject_has_flag():
    obj = GameObject(id="lamp", name="lámpara", base_description="Una lámpara.")
    obj.add_flag(GameFlag.TAKEABLE)
    assert obj.has_flag(GameFlag.TAKEABLE)

def test_gameobject_remove_flag():
    obj = GameObject(id="lamp", name="lámpara", base_description="Una lámpara.")
    obj.add_flag(GameFlag.TAKEABLE)
    obj.remove_flag(GameFlag.TAKEABLE)
    assert not obj.has_flag(GameFlag.TAKEABLE)

def test_gameobject_children_empty_by_default():
    obj = GameObject(id="room", name="sala", base_description="Una sala.")
    assert obj.children == []

def test_gameobject_synonyms_empty_by_default():
    obj = GameObject(id="door", name="puerta", base_description="Una puerta.")
    assert obj.synonyms == []
