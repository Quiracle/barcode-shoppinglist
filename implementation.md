# Implementation Spec — Always-On Barcode Scanner Shopping List (Raspberry Pi + Python Backend + React Frontend)

## 1) Overview
Build a Raspberry Pi “always-on” shopping-list system where a USB barcode scanner (HID keyboard-wedge style) is **always active**. The user simply swipes a barcode; the system automatically adds it to a shopping list. A small React UI runs on the Pi (kiosk-friendly) to show the current list in real time.

**Key idea:** Most USB barcode scanners act like a keyboard and “type” the barcode followed by an Enter key. The backend listens globally for these inputs and processes complete scans.

## 2) Target environment
- Hardware: Raspberry Pi (Pi 3/4/5), USB barcode scanner (keyboard wedge)
- OS: Raspberry Pi OS (or other Linux)
- Backend: Python service (FastAPI recommended)
- Frontend: React SPA served locally (via backend or separate static server)
- Persistence: SQLite on the Pi
- Optional: run everything in Docker Compose

## 3) Core user flows

### 3.1 Always-on scan → add item
1. Scanner “types” barcode digits and ends with Enter (typical).
2. Backend collects keystrokes into a buffer until it sees Enter.
3. Backend treats buffered string as a barcode.
4. Backend immediately add-or-increments the item in the active list.
5. Backend broadcasts an update event to the UI (WebSocket or SSE).
6. UI updates instantly: item appears or quantity increments.

### 3.2 List management in UI
- View items grouped by:
  - To buy
  - Purchased
- Toggle purchased status
- Adjust quantity (+ / -)
- Rename item (if unknown or incorrect)
- Delete item
- Select active list (optional MVP+; can default to one list)

### 3.3 Product lookup (optional but supported)
- After adding the item, backend optionally tries to resolve barcode → product name/brand/image.
- If lookup fails/offline, item remains “Unknown item” until user edits it.

## 4) Functional requirements (MVP)

### 4.1 Scanner input
- Must support HID keyboard-wedge scanners.
- Scanner is “always on” — no need to focus a specific input box.
- Debounce/lock to prevent duplicate rapid triggers (some scanners send repeats).
- Validate barcode string:
  - numeric string length typically 8/12/13/14, but allow configurable patterns
  - ignore empty/whitespace scans
- Configurable “terminator” key:
  - default: Enter

### 4.2 Items and lists
- Default list exists on first boot: “My Shopping List”
- Scanning adds to default list (or currently selected list)
- Dedup logic:
  - If an unpurchased item with same barcode exists → quantity += 1
  - If it exists but purchased=true → create a new unpurchased line item (recommended)

### 4.3 Persistence
- SQLite database stored locally
- Data survives restarts
- Startup ensures schema exists and default list is created

### 4.4 Realtime UI updates
- When scan adds/increments item, UI reflects change immediately without refresh
- Use WebSocket preferred (bi-directional), or SSE (server → client)

## 5) System architecture

### 5.1 Components
1. **Python backend service**
   - Reads barcode scans continuously
   - Exposes REST API for list operations
   - Broadcasts realtime updates (WebSocket/SSE)
   - Optional product lookup provider(s)
2. **React frontend**
   - Displays list + controls
   - Connects to backend (REST + WebSocket/SSE)
   - Kiosk-friendly full-screen layout
3. **SQLite database**
   - Stores lists + items + events metadata

### 5.2 Scanner reading approach (Linux)
Recommended approach: read from the scanner’s **evdev** input device (more reliable than global keyboard hooks), or capture input via a focused hidden input as fallback.

**Option A (recommended): evdev (python-evdev)**
- Pros: robust; doesn’t depend on UI focus; isolates scanner from normal keyboard if you choose device-grab.
- Cons: requires identifying correct `/dev/input/eventX` device; needs permissions (udev rules).

**Option B (fallback): focused hidden input in React**
- Pros: simplest; no Linux input permissions.
- Cons: breaks if focus changes; not truly global.

For “always active,” implement **Option A**.

## 6) Data model

### 6.1 Entities

#### ShoppingList
- id: TEXT (UUID)
- name: TEXT
- createdAt: INTEGER (ms epoch)
- updatedAt: INTEGER (ms epoch)

#### ShoppingItem
- id: TEXT (UUID)
- listId: TEXT (FK)
- barcode: TEXT (nullable)
- name: TEXT
- brand: TEXT (nullable)
- imageUrl: TEXT (nullable)
- quantity: INTEGER (>= 1)
- purchased: INTEGER (0/1)
- createdAt: INTEGER
- updatedAt: INTEGER
- lastAddedAt: INTEGER
- userEditedName: INTEGER (0/1) — optional but recommended

### 6.2 SQLite schema (example)
```sql
CREATE TABLE IF NOT EXISTS lists (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  createdAt INTEGER NOT NULL,
  updatedAt INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  listId TEXT NOT NULL,
  barcode TEXT,
  name TEXT NOT NULL,
  brand TEXT,
  imageUrl TEXT,
  quantity INTEGER NOT NULL,
  purchased INTEGER NOT NULL,
  userEditedName INTEGER NOT NULL DEFAULT 0,
  createdAt INTEGER NOT NULL,
  updatedAt INTEGER NOT NULL,
  lastAddedAt INTEGER NOT NULL,
  FOREIGN KEY (listId) REFERENCES lists(id)
);

CREATE INDEX IF NOT EXISTS idx_items_listId ON items(listId);
CREATE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode);
CREATE INDEX IF NOT EXISTS idx_items_purchased ON items(purchased);
```

## 7) Domain logic

### 7.1 Add-or-increment algorithm
Input: `listId`, `barcode`

1. Normalize barcode: trim, ensure non-empty
2. Query existing:
   - `SELECT * FROM items WHERE listId=? AND barcode=? AND purchased=0 LIMIT 1`
3. If found:
   - `quantity += 1`
   - `lastAddedAt = now`, `updatedAt = now`
4. Else:
   - Insert:
     - `name = "Unknown item"`
     - `quantity = 1`
     - `purchased = 0`
     - timestamps

**Purchased behavior:**
- If a purchased item with same barcode exists, do **not** increment it; create a new unpurchased row.

### 7.2 Scan debouncing
Maintain an in-memory lock:
- If same barcode scanned within N milliseconds (e.g., 800ms) → ignore
- If different barcode → accept

Store:
- `lastScanBarcode`, `lastScanAt`

## 8) Scanner ingestion (Python)

### 8.1 Scanner device selection
On startup:
- Enumerate `/dev/input/event*` and match device name/vendor/product if configured.
- Support config in `.env`:
  - `SCANNER_DEVICE=/dev/input/event3` (explicit)
  - or `SCANNER_NAME=...` to match

### 8.2 Parsing keystrokes into barcodes
- Listen to key events
- Convert keycodes to characters (digits)
- Accumulate into buffer
- On Enter:
  - treat buffer as barcode
  - clear buffer
  - call `add_or_increment(listId, barcode)`
  - broadcast event to UI

### 8.3 Permissions
- Add udev rule to allow non-root access to input device
- Or run service with appropriate group membership (commonly `input` group)
- Prefer not running as root

## 9) Backend API (FastAPI)

### 9.1 REST endpoints (MVP)
- `GET /api/lists` → lists
- `POST /api/lists` → create list (optional)
- `GET /api/lists/{listId}/items` → items
- `POST /api/lists/{listId}/items/manual` → add manual item (optional)
- `PATCH /api/items/{itemId}` → update fields (name, qty, purchased)
- `DELETE /api/items/{itemId}` → delete

### 9.2 Realtime updates
Prefer WebSocket:
- `GET /ws` (WebSocket)
  - Server pushes events:
    - `item_added`
    - `item_updated`
    - `item_deleted`

Event payload example:
```json
{
  "type": "item_updated",
  "listId": "…",
  "item": { "id": "…", "barcode": "…", "name": "…", "quantity": 2, "purchased": 0 }
}
```

## 10) Product resolution provider (optional but designed-in)

### 10.1 Interface (Python)
- `lookup(barcode: str) -> ProductInfo | None`
- `ProductInfo = { name: str, brand?: str, image_url?: str }`

### 10.2 Update rule
If lookup returns info:
- Update item fields:
  - If `userEditedName=0` and name is `"Unknown item"` → replace with resolved name
  - Set `brand`, `imageUrl` if present
- Broadcast `item_updated`

## 11) Frontend (React)

### 11.1 Screens
- Single main screen for kiosk:
  - Header: list name, connection status indicator
  - Items list:
    - checkbox for purchased
    - name + brand (small)
    - quantity control (+ / -)
    - delete icon (optional)
  - Optional: manual add + edit modal

### 11.2 Data loading + live sync
- On load:
  - fetch list + items
- Open WebSocket:
  - apply updates to local state

### 11.3 Kiosk considerations
- Fullscreen layout
- Large touch targets
- Auto-reconnect if backend restarts
- Keep UI functional if websocket down (fallback polling optional)

## 12) Deployment on Raspberry Pi

### 12.1 Recommended layout
- Backend:
  - systemd service (or Docker)
- Frontend:
  - built static assets served by backend (FastAPI static) OR nginx
- Browser:
  - Chromium in kiosk mode, auto-start on boot

### 12.2 systemd services (suggested)
- `scanner-backend.service`
  - starts FastAPI + scanner loop
- Optional `kiosk.service`
  - launches Chromium to `http://localhost:8000`

### 12.3 Docker Compose (optional)
- `backend` container (needs device access to `/dev/input/eventX`)
- `frontend` container or built static served by backend
- Map volumes for SQLite db persistence

## 13) Error handling
- Scanner device missing:
  - backend starts but logs warning; UI shows “Scanner disconnected”
  - retry device discovery periodically
- Invalid scan (buffer empty / non-numeric / too short):
  - ignore and log at debug
- Database errors:
  - return 500; UI shows toast “Storage error”
- Network lookup failure:
  - silent fallback; keep placeholder

## 14) Testing plan
- Unit tests (Python):
  - add-or-increment behavior
  - purchased behavior rule
  - debounce logic
  - barcode parsing (key events → barcode)
- Integration tests:
  - SQLite repository operations
  - WebSocket event broadcast for update
- Manual QA:
  - swipe barcode → item appears
  - swipe same barcode again → qty increments
  - toggle purchased → moves section
  - reboot Pi → list remains

## 15) Suggested project structure
```text
root/
  backend/
    app/
      main.py                # FastAPI app + ws
      scanner/
        evdev_reader.py       # reads HID events → barcode strings
        barcode_parser.py
      data/
        db.py
        repositories.py
        schema.sql
      domain/
        add_or_increment.py
        models.py
      providers/
        base.py
        noop.py
        provider_x.py
    tests/
  frontend/
    src/
      api/
      components/
      screens/
      state/
    public/
  docker-compose.yml (optional)
  README.md
```

## 16) Milestones
1. Backend + SQLite schema + default list
2. React UI reads items from backend
3. evdev scanner reader emits barcode strings
4. Scan → add-or-increment + realtime UI update
5. Product lookup enrichment (optional)
6. Kiosk boot experience + hardening (reconnect, missing device)
