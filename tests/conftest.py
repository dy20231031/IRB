from datetime import date

import pytest

from src.agent import engine
from src.agent.catalog import CATALOG


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 1)
    monkeypatch.setattr(engine, "date", FixedDate)


@pytest.fixture
def scoped():
    return {f: "yes" for f in CATALOG.scope_fields}
