# BLUETTI Venus Gateway On Raspberry Pi 5

This guide installs the standalone BLUETTI Venus Gateway on Raspberry Pi 5 running official Venus OS.
The v1 runtime publishes an EP760 as native Venus D-Bus Battery, AC Input, AC Load, and Inverter
services.

## Fresh Venus OS Setup

1. Flash the official Venus OS Raspberry Pi 5 image to microSD.
2. Boot the Raspberry Pi 5 with stable power and network.
3. Open local Venus GUI or Remote Console and confirm the system is healthy before adding custom services.
4. Enable or confirm SSH access.
5. Add the Venus OS device to VRM and record the VRM Portal ID.
6. Confirm system time/NTP is correct.

Correct system time is required for BLUETTI TLS/auth behavior and for telemetry stale-age decisions.
The installer manages `ntp` by default through `opkg install ntp`, configures external NTP servers,
and restarts `ntpd`. Set `BLUETTI_INSTALL_NTP=0` before running the installer only if time sync is
managed separately.

Confirmed production target:

```text
Venus OS: v3.72
architecture: aarch64
Python: 3.12.12
VRM Portal ID: 2ccf672c2794
```

## Prerequisites

The gateway does not use `pip` in production. Required packages/imports must come from Venus OS/opkg:

```text
git
openssl
openssl-ossl-module-legacy
mosquitto-clients
python3-core
python3-dbus
python3-paho-mqtt
python3-pygobject
python3-cryptography
ntp
```

The installer checks the required commands/imports and reports missing items explicitly.

## Install From Git

```bash
cd /data
git clone https://github.com/mvadim-/bluetti-venus-gateway.git bluetti-venus-gateway
cd /data/bluetti-venus-gateway
mkdir -p /data/bluetti-gateway
cp venus/config/bluetti-gateway.env.example /data/bluetti-gateway/bluetti-gateway.env
chmod 600 /data/bluetti-gateway/bluetti-gateway.env
vi /data/bluetti-gateway/bluetti-gateway.env
./venus/install-venus.sh
```

The installer preserves existing `/data/bluetti-gateway/bluetti-gateway.env`.

## Configuration

Config path:

```text
/data/bluetti-gateway/bluetti-gateway.env
```

Required fields:

```bash
BLUETTI_EMAIL=your-email@example.com
BLUETTI_PASSWORD=your-password
BLUETTI_DEVICE_SN=your-device-sn
```

Runtime defaults:

```bash
BLUETTI_REGION=de
BLUETTI_POLL_PROFILE=vrm-minimal
BLUETTI_POLL_INTERVAL_SECONDS=5
BLUETTI_STALE_AFTER_SECONDS=20
BLUETTI_MQTT_PAYLOAD_FORMAT=new
BLUETTI_MQTT_CIPHERS=DEFAULT:@SECLEVEL=0
BLUETTI_MQTT_TLS_VERIFY_SERVER=0
BLUETTI_ENABLE_PV=0
BLUETTI_ENABLE_PACK_DIAGNOSTICS=0
BLUETTI_ENABLE_INVERTER_SERVICE=1
BLUETTI_ENABLE_MULTI_COMPAT=1
BLUETTI_ENABLE_VEBUS_COMPAT=0
BLUETTI_GUI_GAUGE_AUTO_MAX=0
BLUETTI_GUI_GRID_MAX_CURRENT_A=50
BLUETTI_GUI_LOAD_MAX_CURRENT_A=33
```

`BLUETTI_MQTT_TLS_VERIFY_SERVER=0` is intentional for the current BLUETTI/PowerOak MQTT broker. The
broker presents a private PowerOak-issued server certificate without the issuer chain. TLS and client
certificate authentication still remain enabled.

`BLUETTI_GUI_GAUGE_AUTO_MAX=0` keeps Venus GUIv2 side gauges on EP760 fixed current ranges instead
of letting Venus auto-scale them from recent live values. The defaults match EP760 AC interface
ratings: Grid input `50A` and inverter/load output `33A` at `230V`. Set `BLUETTI_GUI_LOAD_MAX_CURRENT_A=20`
for Germany-limited `4.6kW` installations, or adjust these values if the physical installation is
limited below the inverter rating.

Device instances and labels:

```bash
BLUETTI_BATTERY_DEVICE_INSTANCE=41
BLUETTI_GRID_DEVICE_INSTANCE=30
BLUETTI_ACLOAD_DEVICE_INSTANCE=31
BLUETTI_INVERTER_DEVICE_INSTANCE=32
BLUETTI_BATTERY_CUSTOM_NAME="BLUETTI EP760"
BLUETTI_GRID_CUSTOM_NAME="BLUETTI EP760 AC Input"
BLUETTI_ACLOAD_CUSTOM_NAME="BLUETTI EP760 AC Loads"
BLUETTI_INVERTER_CUSTOM_NAME="BLUETTI EP760 Inverter"
```

Secrets, tokens, and private keys are not printed by status/log scripts.

## Validate Runtime

```bash
/data/bluetti-venus-gateway/venus/status.sh
/data/bluetti-venus-gateway/venus/logs.sh 120
```

Expected status:

```text
bluetti-collector: running
bluetti-dbus-bridge: running
bluetti-repair-on-boot: running
vrmlogger: running
latest telemetry age: below 20s
D-Bus battery service: present
D-Bus grid service: present
D-Bus acload service: present
D-Bus inverter service: present
```

Expected D-Bus service names:

```text
com.victronenergy.battery.ep760_41
com.victronenergy.grid.ep760_30
com.victronenergy.acload.ep760_31
com.victronenergy.inverter.ep760_32
```

`com.victronenergy.inverter.ep760_32` is enabled by default because Venus OS v3.72 systemcalc and
GUIv2 consume inverter AC output from `/Ac/Out/L1/P`, `/Ac/Out/L1/V`, `/Ac/Out/L1/I`, and
`/Ac/Out/L1/F`. The standalone `acload` service remains published for VRM logging compatibility.

Expected battery alarm state for the current EP760 default configuration:

```text
/Alarms/HighVoltage: 0
/Alarms/LowVoltage: 0
```

Voltage alarms are disabled by default until verified EP760-specific thresholds are configured.

## Update From Git

```bash
cd /data/bluetti-venus-gateway
git pull --ff-only
./venus/update-venus.sh
./venus/status.sh
```

Restart services explicitly if runtime modules changed and the update did not restart them:

```bash
./venus/restart.sh
```

## Offline Bundle

Build a recovery artifact on a development machine:

```bash
./venus/build-offline-bundle.sh
```

Default artifact:

```text
dist/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz
```

Validate without applying:

```bash
./venus/update-venus.sh --dry-run --offline-bundle /data/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz
```

Apply from an existing checkout:

```bash
cd /data/bluetti-venus-gateway
./venus/update-venus.sh --offline-bundle /data/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz
```

The bundle contains `app/`, `manifest.json`, `system-packages.txt`, and `checksums.txt`. It is
checksum-verified before files are applied.

The bundle excludes:

```text
/data/bluetti-gateway/bluetti-gateway.env
generated certs
runtime cache
logs
Python bytecode
supervise state
macOS metadata
```

## Repair After Venus OS Update Or Reflash

Forced repair:

```bash
/data/bluetti-venus-gateway/venus/repair-if-needed.sh --force
```

Repair preserves:

```text
/data/bluetti-gateway/bluetti-gateway.env
/data/bluetti-gateway/cache/
/data/bluetti-gateway/certs/
/data/bluetti-gateway/logs/
```

Boot-time repair is installed as `bluetti-repair-on-boot` and restores service links after Venus OS
updates when needed.

The installer also adds a persistent `/data/rc.local` repair hook. This is required on the validated
Raspberry Pi image because `/service` is a tmpfs and service symlinks disappear across reboot.

## Troubleshooting

Template config values:

```text
Invalid gateway config: replace template config values
```

Edit `/data/bluetti-gateway/bluetti-gateway.env`.

Missing OpenSSL legacy provider:

```text
missing required OpenSSL legacy provider
```

Install `openssl-ossl-module-legacy` through opkg.

Disable installer-managed NTP:

```bash
BLUETTI_INSTALL_NTP=0 ./venus/install-venus.sh
```

Override NTP servers:

```bash
BLUETTI_NTP_SERVERS="time.cloudflare.com time.google.com 0.pool.ntp.org" ./venus/install-venus.sh
```

Snapshot missing:

```text
latest telemetry age: unavailable
```

Check `bluetti-collector` logs. The collector must authenticate, connect to BLUETTI MQTT, and receive
decoded replies before `/run/bluetti-gateway/latest.json` appears.

D-Bus services missing:

Check `bluetti-dbus-bridge` logs and verify the snapshot exists. The bridge registers services once a
valid snapshot is available.

## Future Notes

PV/Solar and pack diagnostics are present as disabled future capabilities:

```bash
BLUETTI_ENABLE_PV=0
BLUETTI_ENABLE_PACK_DIAGNOSTICS=0
```

Native Venus GUI modification is out of v1 scope. The production path uses D-Bus services and the
stock Venus GUI/VRM pipeline.
