from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.config import ROOT, load_settings
from backend.app.db import Database


@pytest.fixture()
def demo_app():
    db_path = ROOT / "var" / "pytest_demo.sqlite3"
    if db_path.exists():
        db_path.unlink()
    settings = replace(load_settings(ROOT), database_path=db_path)
    Database(settings).seed_demo()
    app = create_app(settings)
    try:
        yield app
    finally:
        if db_path.exists():
            db_path.unlink()


@pytest.fixture()
def client(demo_app):
    with TestClient(demo_app) as value:
        yield value
