from src.models.core_data import Exit


def test_exit_has_name():
    exit_ = Exit(destination="jazz_street", name="puerta de entrada")
    assert exit_.name == "puerta de entrada"


def test_exit_aliases_optional():
    exit_ = Exit(destination="jazz_street", name="puerta de entrada")
    assert exit_.aliases == []


def test_exit_aliases_set():
    exit_ = Exit(
        destination="jazz_street",
        name="puerta de entrada",
        aliases=["salida", "calle", "sur", "s"]
    )
    assert "sur" in exit_.aliases


def test_exit_matches_name():
    exit_ = Exit(
        destination="jazz_street",
        name="puerta de entrada",
        aliases=["salida", "calle"]
    )
    assert exit_.matches("puerta de entrada")
    assert exit_.matches("salida")
    assert exit_.matches("calle")
    assert not exit_.matches("norte")


def test_exit_door_id_optional():
    exit_ = Exit(destination="jazz_street", name="salida")
    assert exit_.door_id is None
