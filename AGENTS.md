# Repository Guidelines

## Role And Workflow

- Work as a Solution Architect / developer assistant for this standalone BLUETTI Venus Gateway repository.
- Communicate, reason, and plan in Ukrainian. Run terminal commands in English.
- Before starting changes, read the latest block in `ChangeLog.md` for current context.
- Every code, config, script, or documentation change must add a new `ChangeLog.md` entry.
- Use `## [YYYY-MM-DD HH:MM] ...` headings in `ChangeLog.md`, with short bullets for touched files and behavior.
- After each completed bug fix, refactor, feature, or documentation cycle, create a separate git commit with a short imperative subject.
- Do not depend on sibling repositories or any previous application stack; this repository must
  remain usable as an independent Codex workspace.

## Project Scope

This project is a native Venus OS gateway for BLUETTI EP760 / PBOX systems on Raspberry Pi 5.

The runtime target is intentionally small:

- no Docker on the Pi
- no MongoDB, backend API, PWA, web push, or rules engine dependency
- no `pip` dependency on Venus OS
- BLUETTI credentials and runtime config live only in `/data/bluetti-gateway/bluetti-gateway.env`
- the volatile telemetry snapshot lives in `/run/bluetti-gateway/latest.json`

## Runtime Services

The installer manages these runit services on Venus OS:

- `bluetti-collector`
- `bluetti-dbus-bridge`
- `bluetti-repair-on-boot`

The bridge publishes Victron-compatible D-Bus services for Battery, Grid / AC Input, AC Loads,
Inverter, and Multi compatibility paths. Keep Victron path contracts aligned with
`docs/validation/20260504-victron-model-audit.md` when changing telemetry projection logic.

## Repository Layout

- `src/bluetti_venus_gateway/` contains runtime Python code.
- `venus/` contains Venus OS installer, service definitions, update, status, log, restart, repair,
  and offline-bundle scripts.
- `tests/` contains local unit tests.
- `docs/deploy/` contains Raspberry Pi / Venus OS deployment notes.
- `docs/research/` contains BLUETTI telemetry and polling reference material.
- `docs/validation/` contains local, hardware, and Victron model validation records.
- `docs/plans/completed/` contains completed implementation plans retained for project history.

## Build And Test Commands

Run these before committing when relevant:

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src
git diff --check
bash -n venus/*.sh venus/services/*/run
```

For live Venus OS checks on Raspberry Pi:

```bash
cd /data/bluetti-venus-gateway
./venus/install-venus.sh
./venus/restart.sh
./venus/status.sh
./venus/logs.sh 120
```

Use the Codex in-app browser / browser-use plugin for local Venus GUI checks at
`http://venus.local/gui-v2/`.

## Coding Rules

- Prefer Python standard library APIs for runtime code.
- Keep Venus OS compatibility assumptions explicit; do not introduce package requirements that
  official Venus OS cannot satisfy without documenting installer support.
- Do not fabricate telemetry. If BLUETTI does not expose a Victron field reliably, leave it absent,
  `None`, or stale-safe rather than publishing misleading values.
- Preserve service names and D-Bus path contracts unless the deployment docs, validation docs, tests,
  and status tooling are updated together.
- Keep comments short and only where they clarify non-obvious Victron or BLUETTI behavior.

## Security And Configuration

- Never commit BLUETTI credentials, local `.env` files, device tokens, cookies, certs, cache, logs, or
  generated runtime snapshots.
- Keep `/data/bluetti-gateway/bluetti-gateway.env` local to the target device.
- Offline bundles must not include local config or secrets.
