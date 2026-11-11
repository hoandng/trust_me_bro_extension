import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
def metrics_db_path(monkeypatch, tmp_path):
    path = tmp_path / "metrics.db"
    monkeypatch.setattr(settings, "metrics_db_path", path)
    return path
