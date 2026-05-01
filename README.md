# BLUETTI Venus Gateway

Standalone native Venus OS gateway for BLUETTI systems. The v1 target is Raspberry Pi 5 running
official Venus OS, publishing EP760 Battery, AC Input, and AC Loads as native D-Bus services for
local Venus UI and VRM through the stock `vrmlogger`.

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

See [docs/deploy/venus-gateway-rpi5.md](docs/deploy/venus-gateway-rpi5.md).
