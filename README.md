# BLUETTI Venus Gateway

Standalone native Venus OS gateway for BLUETTI systems. The v1 target is Raspberry Pi 5 running
official Venus OS, publishing EP760 Battery, AC Input, AC Loads, and Inverter services for local
Venus UI and VRM through the stock `vrmlogger`.

Production runtime is intentionally small:

- no Docker on the Pi
- no MongoDB, PWA, backend API, web push, or rules engine
- no `pip` dependency on Venus OS
- local config in `/data/bluetti-gateway/bluetti-gateway.env`
- volatile telemetry snapshot in `/run/bluetti-gateway/latest.json`

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
env PYTHONPATH=src python3 -m unittest discover -s tests
```

Runtime modules use only the Python standard library unless the process is running on Venus OS, where
`dbus`, `gi`, `vedbus`, and `paho.mqtt.client` are expected from system packages.

## Raspberry Pi 5 Install

After installing and validating official Venus OS:

```bash
cd /data
git clone <gateway-repo-url> bluetti-venus-gateway
cd /data/bluetti-venus-gateway
cp venus/config/bluetti-gateway.env.example /data/bluetti-gateway/bluetti-gateway.env
chmod 600 /data/bluetti-gateway/bluetti-gateway.env
vi /data/bluetti-gateway/bluetti-gateway.env
./venus/install-venus.sh
./venus/status.sh
```

Expected services after BLUETTI credentials are configured:

- `com.victronenergy.battery.ep760_41`
- `com.victronenergy.grid.ep760_30`
- `com.victronenergy.acload.ep760_31`
- `com.victronenergy.inverter.ep760_32`

See [docs/deploy/bluetti-venus-gateway-rpi5.md](docs/deploy/bluetti-venus-gateway-rpi5.md).

## Developer Documentation

- [AGENTS.md](AGENTS.md): standalone Codex/developer workflow rules for this repository.
- [docs/plans/completed/20260430-venus-gateway-rpi5.md](docs/plans/completed/20260430-venus-gateway-rpi5.md):
  completed Raspberry Pi 5 implementation plan and final state summary.
- [docs/research/bluetti-modbus-data-map.md](docs/research/bluetti-modbus-data-map.md):
  BLUETTI register group map for future parser and polling work.
- [docs/research/telemetry-signal-map.md](docs/research/telemetry-signal-map.md):
  normalized signal source map and fallback policy.
- [docs/research/mqtt-display-parameters.md](docs/research/mqtt-display-parameters.md):
  display/Victron projection parameter reference.

## Offline Bundle

Build a recovery artifact on a development machine:

```bash
./venus/build-offline-bundle.sh
```

Apply it on Venus OS from an existing checkout:

```bash
cd /data/bluetti-venus-gateway
./venus/update-venus.sh --offline-bundle /data/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz
```

The bundle contains source, Venus scripts, service definitions, a manifest, package prerequisites,
and checksums. It does not include local config, BLUETTI credentials, certs, cache, or logs.

## Operations

```bash
./venus/status.sh
./venus/logs.sh 120
./venus/restart.sh
./venus/repair-if-needed.sh --force
```
