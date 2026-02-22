"""IBKR connection manager wrapping ib_insync.IB with retry and reconnect logic."""

import logging

from ib_insync import IB
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import Settings

logger = logging.getLogger(__name__)


class IBKRConnectionError(Exception):
    pass


class IBKRClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ib = IB()
        self._ib.disconnectedEvent += self._on_disconnected

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._ib.isConnected()

    def get_ib(self) -> IB:
        if not self.is_connected:
            raise IBKRConnectionError("Not connected to IBKR. Call connect() first.")
        return self._ib

    async def connect(self) -> None:
        if self.is_connected:
            return
        await self._connect_with_retry()

    async def disconnect(self) -> None:
        if self.is_connected:
            self._ib.disconnect()
            logger.info("Disconnected from IBKR.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        reraise=True,
    )
    async def _connect_with_retry(self) -> None:
        logger.info(
            "Connecting to IBKR at %s:%s (clientId=%s)...",
            self._settings.ibkr_host,
            self._settings.ibkr_tws_port,
            self._settings.ibkr_client_id,
        )
        await self._ib.connectAsync(
            host=self._settings.ibkr_host,
            port=self._settings.ibkr_tws_port,
            clientId=self._settings.ibkr_client_id,
            readonly=True,
        )
        logger.info("Connected to IBKR.")

    def _on_disconnected(self) -> None:
        logger.warning("IBKR disconnected — will retry on next sync cycle.")
