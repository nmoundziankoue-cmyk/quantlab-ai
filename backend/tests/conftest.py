"""Shared pytest fixtures for M5–M7 tests that require a real database.

Uses the running PostgreSQL container (same as development).
Each test that requests ``db`` runs inside a SAVEPOINT that is rolled back
after the test, so tests don't accumulate data across runs.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from models.base import Base
from models.portfolio import Portfolio
from models.trading import CommissionTypeEnum, PaperAccount

# Ensure all models are imported so their tables are in metadata
import models.portfolio   # noqa: F401
import models.watchlist   # noqa: F401
import models.research    # noqa: F401
import models.analytics   # noqa: F401
import models.trading     # noqa: F401
import models.research_workspace   # noqa: F401
import models.document_intelligence  # noqa: F401
import models.alternative_data   # noqa: F401
import models.screener    # noqa: F401
import models.options     # noqa: F401
import models.orchestrator  # noqa: F401
import models.knowledge_graph  # noqa: F401
import models.economic_calendar  # noqa: F401
import models.auth        # noqa: F401
import models.sessions    # noqa: F401
import models.notifications  # noqa: F401


@pytest.fixture(scope="session")
def pg_engine():
    """Create a PostgreSQL engine for the full test session."""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db(pg_engine):
    """Provide a database session wrapped in a savepoint.

    All writes made during the test are rolled back when the test ends.
    This keeps the database clean without dropping/re-creating tables.
    """
    connection = pg_engine.connect()
    trans = connection.begin()

    session = Session(bind=connection)

    # Use nested transaction (SAVEPOINT) so we can rollback without
    # affecting the outer transaction boundary.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if nested.is_active:
            nested.rollback()
        trans.rollback()
        connection.close()


@pytest.fixture
def test_portfolio(db) -> Portfolio:
    """Insert a test portfolio and return it (rolled back after each test)."""
    portfolio = Portfolio(
        name="Test Portfolio",
        currency="USD",
        benchmark="SPY",
    )
    db.add(portfolio)
    db.flush()
    return portfolio


@pytest.fixture
def test_paper_account(db) -> PaperAccount:
    """Insert a test paper account and return it (rolled back after each test)."""
    account = PaperAccount(
        name="Test Paper Account",
        initial_cash=Decimal("100000"),
        cash_balance=Decimal("100000"),
        buying_power=Decimal("100000"),
        total_equity=Decimal("100000"),
        commission_type=CommissionTypeEnum.FLAT,
        commission_rate=Decimal("1.00"),
        min_commission=Decimal("0"),
        slippage_bps=10,
    )
    db.add(account)
    db.flush()
    return account
