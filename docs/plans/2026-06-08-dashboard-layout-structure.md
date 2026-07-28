# Dashboard layout structure for Elementary overview

**Date:** 2026-06-08

## Goal

Improve dashboard `3` layout so related charts are grouped clearly and the new reliability indicators are easier to scan.

## Planned changes

1. Inspect the current dashboard metadata and chart inventory.
2. Propose a clearer layout structure for Overview and History content.
3. After user confirmation, build `position_json` for the dashboard and place charts into aligned sections/tabs.
4. Verify the dashboard metadata update and confirm linked charts remain attached.

## Verification

- `uv run superset-cli dashboards get local 3 --json`
- `uv run superset-cli dashboards charts local 3 --json`
- visual check in local Superset UI after layout update

## Decision follow-up

No durable decision change.
