from __future__ import annotations

from backend.app.db import Database


def test_seed_counts_and_idempotency(demo_app):
    db: Database = demo_app.state.db
    first = db.verify_demo()
    db.seed_demo()
    second = db.verify_demo()
    assert first["counts"] == {"sources": 2, "areas": 8, "places": 40, "price_bundles": 40, "area_metrics": 768}
    assert second["counts"] == first["counts"]
    assert second["foreign_key_errors"] == 0


def test_seed_rejects_non_demo_path(demo_app):
    settings = demo_app.state.settings
    bad = settings.__class__(**{**settings.__dict__, "database_path": settings.root / "data" / "production.sqlite3"})
    allowed, reason = Database(bad).can_seed_demo()
    assert not allowed
    assert "var/" in reason
