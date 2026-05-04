# Raspberry Pi 5 Venus Gateway Deploy

## Preconditions

- Official Venus OS is installed and booted on Raspberry Pi 5.
- VRM Portal ID is visible and the device is added to VRM.
- SSH works and system time/NTP is correct.
- Venus OS provides `python3`, `python3-dbus`, `python3-pygobject`, `python3-paho-mqtt`,
  `python3-cryptography`, `openssl`, `openssl-ossl-module-legacy`, and `dbus-send`.

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

Expected status once BLUETTI credentials are configured:

- `bluetti-collector: running`
- `bluetti-dbus-bridge: running`
- `latest telemetry age` normally below `20s`
- Battery, Grid, and AC Load D-Bus services present

## Update

```bash
cd /data/bluetti-venus-gateway
git pull --ff-only
./venus/update-venus.sh
```

Offline bundle update:

```bash
cd /data/bluetti-venus-gateway
./venus/update-venus.sh --offline-bundle /data/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz
```

To validate a bundle without applying it:

```bash
./venus/update-venus.sh --dry-run --offline-bundle /data/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz
```

The bundle is checksum-verified before files are applied. It must not contain
`/data/bluetti-gateway/bluetti-gateway.env`, generated certs, cache, or logs.

## Repair

```bash
/data/bluetti-venus-gateway/venus/repair-if-needed.sh --force
```

Repair preserves `/data/bluetti-gateway/bluetti-gateway.env`, `cache/`, `certs/`, and `logs/`.

## Troubleshooting

Use:

```bash
/data/bluetti-venus-gateway/venus/status.sh
/data/bluetti-venus-gateway/venus/logs.sh 120
```

Common blockers:

- Template config values: edit `/data/bluetti-gateway/bluetti-gateway.env`.
- Missing OpenSSL legacy provider: install `openssl-ossl-module-legacy`.
- BLUETTI MQTT TLS CA failures: default `BLUETTI_MQTT_TLS_VERIFY_SERVER=0` is intentional for the
  private PowerOak broker while client certificate authentication remains enabled.
- Snapshot missing: collector has not yet received decoded BLUETTI MQTT replies.
