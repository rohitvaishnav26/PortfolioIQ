"""Tests for IBKRClient connection manager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import Settings
from backend.services.ibkr_client import IBKRClient, IBKRConnectionError


@pytest.fixture
def settings():
    return Settings(
        ibkr_host="127.0.0.1",
        ibkr_tws_port=4002,
        ibkr_client_id=1,
    )


@pytest.fixture
def mock_ib():
    ib = MagicMock()
    ib.isConnected.return_value = False
    ib.connectAsync = AsyncMock()
    ib.disconnectedEvent = MagicMock()
    ib.disconnectedEvent.__iadd__ = MagicMock(return_value=ib.disconnectedEvent)
    return ib


async def test_is_connected_false_before_connect(settings, mock_ib):
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        assert client.is_connected is False


async def test_connect_calls_connectAsync(settings, mock_ib):
    # isConnected returns False on guard check, True after connectAsync completes
    mock_ib.isConnected.side_effect = [False, True]
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        await client.connect()
        mock_ib.connectAsync.assert_called_once_with(
            host="127.0.0.1",
            port=4002,
            clientId=1,
            readonly=True,
        )


async def test_connect_skips_if_already_connected(settings, mock_ib):
    mock_ib.isConnected.return_value = True
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        await client.connect()
        mock_ib.connectAsync.assert_not_called()


async def test_get_ib_raises_when_not_connected(settings, mock_ib):
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        with pytest.raises(IBKRConnectionError):
            client.get_ib()


async def test_get_ib_returns_ib_when_connected(settings, mock_ib):
    mock_ib.isConnected.return_value = True
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        result = client.get_ib()
        assert result is mock_ib


async def test_disconnect_calls_ib_disconnect(settings, mock_ib):
    mock_ib.isConnected.return_value = True
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        await client.disconnect()
        mock_ib.disconnect.assert_called_once()


async def test_disconnect_skips_if_not_connected(settings, mock_ib):
    mock_ib.isConnected.return_value = False
    with patch("backend.services.ibkr_client.IB", return_value=mock_ib):
        client = IBKRClient(settings)
        await client.disconnect()
        mock_ib.disconnect.assert_not_called()
