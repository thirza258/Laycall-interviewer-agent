"""The request-scoped database session dependency.

Every endpoint test overrides `get_db`, so the real dependency is never
exercised by them. It is short, but a mistake in it would leak a connection
per request — which is exactly the kind of fault that only shows up under
load, long after the tests pass.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


class TestGetDb:
    @pytest.mark.asyncio
    async def test_yields_exactly_one_session(self):
        sessions = [session async for session in get_db()]

        assert len(sessions) == 1
        assert isinstance(sessions[0], AsyncSession)

    @pytest.mark.asyncio
    async def test_closes_the_session_when_the_request_ends(self):
        """The `async with` must close the session on the way out.

        Asserted on the close call rather than on session state, because
        `is_active` describes the transaction and stays true after a close.
        A session left open holds its connection, so a leak here would
        exhaust the pool under load rather than fail any single request.
        """
        with patch.object(
            AsyncSession, "close", AsyncMock(return_value=None)
        ) as close:
            async for _session in get_db():
                close.assert_not_awaited()  # still open while the request runs

        close.assert_awaited_once()
