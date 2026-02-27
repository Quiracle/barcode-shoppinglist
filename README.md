# Barcode Shopping List (Raspberry Pi, FastAPI, React, evdev)

Local-first shopping list app for Raspberry Pi with an always-on USB barcode scanner.

## Implemented Scope

- Always-on scanner ingestion from Linux `evdev` (no UI focus dependency).
- Python backend with FastAPI, SQLite persistence, REST API, and WebSocket events.
- React kiosk-friendly frontend with live updates.
- Backend can serve built frontend from `http://localhost:8000`.
- Offline-safe flow: product lookup provider is stubbed (`NoopLookupProvider`).

## Project Structure

```text
backend/
  app/
    main.py
    scanner/
      evdev_reader.py
      barcode_parser.py
    data/
      db.py
      repositories.py
      schema.sql
    domain/
      add_or_increment.py
      models.py
      schemas.py
    providers/
      base.py
      noop.py
  tests/
frontend/
  src/
    api/
    components/
    state/
```

## Requirements

- Raspberry Pi OS (Linux)
- Python 3.11+
- Node.js 18+
- USB barcode scanner in keyboard-wedge mode

## Raspberry Pi Install

1. Install system packages:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm
```

2. Backend setup:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Frontend setup:
```bash
cd ../frontend
npm install
```

## Scanner Configuration (`SCANNER_DEVICE` / `SCANNER_NAME`)

Configure scanner discovery with environment variables before running backend.

- Explicit device path (most deterministic):
```bash
export SCANNER_DEVICE=/dev/input/event3
```

- Or name match fallback:
```bash
export SCANNER_NAME="Your Scanner Name"
```

Optional scanner settings:

- `SCANNER_TERMINATOR` (default `KEY_ENTER`)
- `SCANNER_RETRY_SECONDS` (default `5`)
- `SCAN_DEBOUNCE_MS` (default `800`)
- `BARCODE_LENGTHS` (default `8,12,13,14`)
- `SQLITE_PATH` (default `backend/data/shopping.db`)

## Run (Development)

Use two terminals.

1. Start backend:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Start frontend Vite dev server:
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

- Backend API + WS: `http://<pi-ip>:8000`
- Frontend dev UI: `http://<pi-ip>:5173`

## Run (Production Build Served by Backend)

1. Build frontend:
```bash
cd frontend
npm run build
```

2. Start backend (serves `frontend/dist`):
```bash
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

3. Open:
```text
http://localhost:8000
```

## evdev Permissions / udev

`python-evdev` requires access to `/dev/input/event*`.

Option A: Add user to input group:
```bash
sudo usermod -aG input $USER
# Log out/in after this.
```

Option B: udev rule (example):

1. Create `/etc/udev/rules.d/99-barcode-scanner.rules`:
```text
KERNEL=="event*", SUBSYSTEM=="input", GROUP="input", MODE="0660"
```

2. Reload rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## API Summary

- `GET /api/lists`
- `POST /api/lists`
- `GET /api/lists/{listId}/items`
- `POST /api/lists/{listId}/items/manual`
- `PATCH /api/items/{itemId}`
- `DELETE /api/items/{itemId}`
- WebSocket: `/ws`

WebSocket events sent:

- `item_added`
- `item_updated`
- `item_deleted`

## Domain Rules Implemented

- Default list is created at startup: `My Shopping List`.
- Add-or-increment:
  - Same barcode + unpurchased item in list -> increment quantity.
  - Same barcode only in purchased items -> create new unpurchased row.
- Debounce:
  - Same barcode scanned within `SCAN_DEBOUNCE_MS` ignored.
- Barcode validation:
  - Numeric only.
  - Length must match `BARCODE_LENGTHS`.

## Tests

Run:
```bash
python -m pytest backend/tests
```

Included tests cover:

- add-or-increment increments existing unpurchased row
- purchased-row behavior creates new unpurchased row
- debounce duplicate rejection
- barcode parser key sequence handling

## Manual QA Checklist

Checklist from `implementation.md`:

1. Swipe barcode -> item appears in "To buy"
2. Swipe same barcode again -> quantity increments
3. Toggle purchased -> item moves to "Purchased"
4. Reboot Pi / restart backend -> list and items remain in SQLite

## Troubleshooting

### Scanner not found

- Check input devices:
```bash
ls -l /dev/input/event*
```
- Identify device names:
```bash
sudo evtest
```
- Set `SCANNER_DEVICE` explicitly if auto-name matching fails.

### Permission denied on `/dev/input/eventX`

- Ensure user is in `input` group or udev rule is applied.
- Re-login after group changes.

### WebSocket reconnect behavior

- Frontend auto-reconnects every ~1.5s when backend restarts.
- Connection badge states: `Connecting`, `Connected`, `Reconnecting`, `Connection error`.

### Invalid scans ignored

- Scanner output must be numeric and match allowed lengths.
- Update `BARCODE_LENGTHS` if scanner emits uncommon barcode lengths.

## Simplifying Decisions Made (Not Explicitly Defined)

- Used a fixed default list ID (`default`) to guarantee deterministic startup behavior.
- Implemented product lookup as a no-op provider to preserve offline behavior by default.
- Manual item add is supported only via API (no dedicated UI modal in MVP UI).
