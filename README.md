# British Gas PAYG — Home Assistant Integration

A Home Assistant integration for **British Gas prepayment (Pay As You Go) meters**. It exposes your current credit balance and the timestamp of the last balance reading as sensors for both Gas and Electricity meters.

## What it does

For each active PAYG meter on your British Gas account it creates two sensors:

| Sensor | Example value | Notes |
|--------|--------------|-------|
| Balance | £39.86 | Current credit balance in GBP |
| Last updated | 2026-03-03 00:02:20 UTC | Timestamp of the last balance reading from British Gas |

Only meter points where `paymentType = Payg` and `status = Active` are imported. Credit meters and inactive meter points are ignored.

## Requirements

- A British Gas account with at least one active PAYG meter
- Home Assistant 2024.1 or later
- HACS installed

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant sidebar.
2. Go to **Integrations** → **⋮** (top right) → **Custom repositories**.
3. Enter `https://github.com/damien-alt-sudo/ha-british-gas-payg` and select category **Integration**, then click **Add**.
4. Find **British Gas PAYG** in the list and click **Download**.
5. Restart Home Assistant.

### Manual

Copy the `custom_components/british_gas/` folder into your Home Assistant `config/custom_components/` directory, then restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **British Gas PAYG**.
3. Enter the email address and password you use to sign in to [britishgas.co.uk](https://www.britishgas.co.uk).

The integration polls British Gas once per hour by default. You can change the interval (60–1440 minutes) via the integration's **Configure** button.

## Sensors

Both sensors are grouped under a single device per meter (identified by your meter point reference number).

### Balance sensor

- **Device class**: `monetary`
- **Unit**: GBP
- **Extra attributes**:
  - `meter_point_reference` — your meter point reference number
  - `commodity` — `Gas` or `Electricity`
  - `debt` — any outstanding debt balance, or `null`

### Last updated sensor

- **Device class**: `timestamp`
- Reports the UTC timestamp at which British Gas last updated the balance on their system.

## Reauthentication

If your session expires or your password changes, Home Assistant will prompt you to re-enter your credentials via the standard reauthentication flow.

## Issues

Please report bugs and feature requests at [GitHub Issues](https://github.com/damien-alt-sudo/ha-british-gas-payg/issues).
