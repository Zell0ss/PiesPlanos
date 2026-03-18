"""Tests for bot/portrait_service.py."""

from pathlib import Path
import pytest

from bot.portrait_service import get_portrait


def test_returns_path_when_file_exists(tmp_path):
    portrait_root = tmp_path
    (portrait_root / "jack_napier.jpg").write_bytes(b"fake-image")
    result = get_portrait(
        "jack_napier",
        npc_portrait_filename="jack_napier.jpg",
        portrait_root=portrait_root,
    )
    assert result is not None
    assert result.exists()


def test_returns_none_when_file_missing(tmp_path):
    result = get_portrait(
        "jack_napier", npc_portrait_filename="jack_napier.jpg", portrait_root=tmp_path
    )
    assert result is None


def test_returns_none_when_npc_has_no_portrait(tmp_path):
    result = get_portrait(
        "jack_napier", npc_portrait_filename=None, portrait_root=tmp_path
    )
    assert result is None
