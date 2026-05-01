# Raspberry Pi 5 Venus Gateway Deploy

## Preconditions

- Official Venus OS is installed and booted on Raspberry Pi 5.
- VRM Portal ID is visible and the device is added to VRM.
- SSH works and system time/NTP is correct.
- Venus OS provides `python3`, `python3-dbus`, `python3-pygobject`, `python3-paho-mqtt`,
  `openssl`, and `dbus-send`.

## Install

```bash
cd /data
git clone <gateway-repo-url> bluetti-venus-gateway
cd /data/bluetti-venus-gateway
mkdir -p /data/bluetti-gateway
cp venus/config/bluetti-gateway.env.example /data/bluetti-gateway/bluetti-gateway.env
chmod 600 /data/bluetti-gateway/bluetti-gateway.env
vi /data/bluetti-gateway/bluetti-gateway.env
./venus/install-venus.sh
```

## Validate

```bash
/data/bluetti-venus-gateway/venus/status.sh
/data/bluetti-venus-gateway/venus/logs.sh
```

Expected v1 D-Bus services:

- `com.victronenergy.battery.ep760_41`
- `com.victronenergy.grid.ep760_30`
- `com.victronenergy.acload.ep760_31`

## Current Bootstrap Limitation

This first implementation cycle installs the package, service wrappers, config validation, snapshot
contract, and D-Bus bridge payload model. The live BLUETTI cloud/MQTT collector is intentionally not
enabled yet; `bluetti-collector` supports fixture mode through `BLUETTI_COLLECTOR_FIXTURE_JSON` for
local bridge validation.

## Update

```bash
cd /data/bluetti-venus-gateway
git pull
./venus/update-venus.sh
```

## Repair

```bash
/data/bluetti-venus-gateway/venus/repair-if-needed.sh --force
```

Repair preserves `/data/bluetti-gateway/bluetti-gateway.env`, `cache/`, `certs/`, and `logs/`.

