import json
from pathlib import Path
import pytest
from rfp.db import init_db, load_criteria

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.sqlite"
    init_db(path)
    return path


@pytest.fixture
def criteria(db):
    return load_criteria(db)


@pytest.fixture
def proposal():
    return (ROOT / "samples/proposals/apex_systems.pdf").read_bytes()


@pytest.fixture
def raw():
    return json.loads((ROOT / "samples/evaluations/apex_systems.json").read_text())
