"""Data update coordinator for the British Gas integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import aiohttp

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AUTH_URL,
    BALANCE_ENDPOINT_TEMPLATE,
    COMMODITY_ELECTRICITY,
    COMMODITY_GAS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    METER_STATUS_ACTIVE,
    PAYMENT_TYPE_PAYG,
    PREMISES_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MeterPointBalance:  # pylint: disable=too-many-instance-attributes
    """Balance data for a single meter point."""

    meter_point_id: int
    meter_point_reference: str
    account_id: int
    commodity: str
    address: str
    balance: float | None
    balance_timestamp: datetime | None
    debt: float | None


class BritishGasAuthError(Exception):
    """Raised when British Gas authentication fails."""


class BritishGasApiError(Exception):
    """Raised when a British Gas API call fails."""


class BritishGasClient:
    """Client for the British Gas API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self._session = session
        self._token: str | None = None

    @property
    def has_token(self) -> bool:
        """Return whether the client has an authentication token."""
        return self._token is not None

    async def authenticate(self, username: str, password: str) -> None:
        """Authenticate with British Gas and store the bearer token."""
        form_data = {
            "_csrf": "",
            "autoLockedEmail": "true",
            "routeName": "authenticate",
            "username": username,
            "password": password,
        }
        try:
            async with self._session.post(
                AUTH_URL,
                data=form_data,
                allow_redirects=False,
            ) as response:
                # Auth returns a 302 redirect — we must not follow it.
                # The cognito_id_token cookie is set in this response.
                if response.status not in (200, 302):
                    raise BritishGasAuthError(
                        f"Unexpected authentication status: {response.status}"
                    )
                token_morsel = response.cookies.get("cognito_id_token")
                if token_morsel is None:
                    raise BritishGasAuthError(
                        "No token cookie in authentication response"
                    )
                self._token = token_morsel.value
        except aiohttp.ClientError as err:
            raise BritishGasApiError(
                f"Connection error during authentication: {err}"
            ) from err

    async def get_premises(self) -> list[dict]:
        """Fetch all premises for the authenticated account."""
        result = await self._get(PREMISES_ENDPOINT)
        if not isinstance(result, list):
            raise BritishGasApiError("Unexpected premises response format")
        return result

    async def get_balance(self, account_id: int, meter_point_id: int) -> dict:
        """Fetch the balance for a specific meter point."""
        url = BALANCE_ENDPOINT_TEMPLATE.format(
            account_id=account_id,
            meter_point_id=meter_point_id,
        )
        result = await self._get(url)
        if not isinstance(result, dict):
            raise BritishGasApiError("Unexpected balance response format")
        return result

    async def _get(self, url: str) -> dict | list:
        """Make an authenticated GET request."""
        if self._token is None:
            raise BritishGasAuthError("Client is not authenticated")

        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 401:
                    self._token = None
                    raise BritishGasAuthError("Token rejected (401)")
                if not response.ok:
                    raise BritishGasApiError(
                        f"API request to {url} failed with status {response.status}"
                    )
                return await response.json()
        except aiohttp.ClientError as err:
            raise BritishGasApiError(f"Connection error: {err}") from err


class BritishGasCoordinator(DataUpdateCoordinator[dict[int, MeterPointBalance]]):
    """Coordinator that fetches balances for all meter points."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BritishGasClient,
        config_entry_data: dict,
        config_entry,
    ) -> None:
        """Initialize the coordinator.

        The polling interval is read from config entry options so that it
        can be adjusted via the integration's Configure button.
        """
        interval_minutes: int = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
            config_entry=config_entry,
        )
        self.client = client
        self._username: str = config_entry_data[CONF_USERNAME]
        self._password: str = config_entry_data[CONF_PASSWORD]

    async def _async_update_data(self) -> dict[int, MeterPointBalance]:
        """Fetch premises and balances, re-authenticating if needed."""
        username = self._username
        password = self._password

        if not self.client.has_token:
            await self._authenticate(username, password)

        try:
            return await self._fetch_all_balances()
        except BritishGasAuthError:
            # Token may have expired — try to re-authenticate once.
            _LOGGER.debug("Token rejected, attempting re-authentication")
            await self._authenticate(username, password)
            return await self._fetch_all_balances()

    async def _authenticate(self, username: str, password: str) -> None:
        """Authenticate the client, raising appropriate HA exceptions on failure."""
        try:
            await self.client.authenticate(username, password)
        except BritishGasAuthError as err:
            raise ConfigEntryAuthFailed(
                f"British Gas credentials are invalid: {err}"
            ) from err
        except BritishGasApiError as err:
            raise UpdateFailed(
                f"Could not connect to British Gas during authentication: {err}"
            ) from err

    async def _fetch_all_balances(self) -> dict[int, MeterPointBalance]:
        """Fetch premises, then fetch balances for each meter point."""
        try:
            premises = await self.client.get_premises()
        except BritishGasApiError as err:
            raise UpdateFailed(f"Failed to fetch premises: {err}") from err

        results: dict[int, MeterPointBalance] = {}

        for premise in premises:
            address = _format_address(premise.get("address", {}))
            for meter_point in premise.get("meterPoints", []):
                commodity = meter_point.get("commodity", "")
                if commodity not in (COMMODITY_GAS, COMMODITY_ELECTRICITY):
                    continue
                if meter_point.get("paymentType") != PAYMENT_TYPE_PAYG:
                    continue
                if meter_point.get("status") != METER_STATUS_ACTIVE:
                    continue

                account_id: int = meter_point["accountId"]
                meter_point_id: int = meter_point["meterPointId"]

                try:
                    balance_data = await self.client.get_balance(
                        account_id, meter_point_id
                    )
                except BritishGasApiError as err:
                    _LOGGER.warning(
                        "Failed to fetch balance for %s meter at %s: %s",
                        commodity,
                        address,
                        err,
                    )
                    balance_data = {}

                credit = balance_data.get("credit") or {}
                debt_data = balance_data.get("debt") or {}

                balance_timestamp: datetime | None = None
                if ts_str := credit.get("timestampUtc"):
                    try:
                        balance_timestamp = datetime.fromisoformat(ts_str).replace(
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        _LOGGER.debug(
                            "Could not parse balance timestamp: %s", ts_str
                        )

                results[meter_point_id] = MeterPointBalance(
                    meter_point_id=meter_point_id,
                    meter_point_reference=meter_point["meterPointReference"],
                    account_id=account_id,
                    commodity=commodity,
                    address=address,
                    balance=credit.get("balance"),
                    balance_timestamp=balance_timestamp,
                    debt=debt_data.get("balance") if debt_data else None,
                )

        return results


def _format_address(address: dict) -> str:
    """Format an address dict into a human-readable string."""
    parts = [
        address.get("address1", ""),
        address.get("address2", ""),
        address.get("address3", ""),
        address.get("town", ""),
        address.get("postCode", ""),
    ]
    return ", ".join(p for p in parts if p)
