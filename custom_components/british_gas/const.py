"""Constants for the British Gas integration."""

DOMAIN = "british_gas"

AUTH_URL = "https://www.britishgas.co.uk/uaa/login"
API_BASE_URL = "https://api-account.britishgas.co.uk/v1"
PREMISES_ENDPOINT = f"{API_BASE_URL}/proxy/premises"
BALANCE_ENDPOINT_TEMPLATE = (
    f"{API_BASE_URL}/proxy/payg/Accounts/{{account_id}}"
    "/MeterPoints/{meter_point_id}/Balances"
)

COMMODITY_GAS = "Gas"
COMMODITY_ELECTRICITY = "Electricity"

PAYMENT_TYPE_PAYG = "Payg"
METER_STATUS_ACTIVE = "Active"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # minutes
MIN_SCAN_INTERVAL = 60  # minutes
MAX_SCAN_INTERVAL = 1440  # minutes (24 hours)
