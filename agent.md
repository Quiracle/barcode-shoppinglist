<!-- agent.md -->
# Barcode-to-Shopping-List — Codex Agent Guide

## Mission
Build a mobile-first app that lets a user scan a product barcode and **automatically adds the item to a shopping list** with minimal friction.

## Non-negotiables
- Scanning a barcode should be **faster than typing**.
- Offline-first list: the list must work without network.
- No blocking on product lookups: if metadata fetch fails, still add the item (e.g., “Unknown item (barcode …)”).
- Clear error states (camera permission, scan failures, duplicate behavior).

## Product goals (MVP)
1. **Create/manage lists**
   - Default list: “My Shopping List”
   - Add/remove items
   - Mark items as purchased (toggle)
2. **Barcode scanning**
   - Open scanner, scan EAN/UPC
   - Add to current list immediately
3. **Item resolution**
   - If online: try to resolve barcode → product name/brand/image (pluggable provider)
   - If not: add placeholder item and allow later edit
4. **Dedup logic**
   - If item already exists in list: increment quantity
   - Otherwise: add new line item
5. **Persistence**
   - Local storage (SQLite or equivalent) so data survives restarts

## Tech constraints (choose sensible defaults)
- Prioritize a stack with strong barcode scanning support and simple local persistence.
- Keep architecture modular so providers can be swapped.

## Suggested default stack (agent can adjust if repo dictates)
- **React Native (Expo)** for speed + camera/scanner libraries
- Local persistence via **SQLite** (expo-sqlite) or **WatermelonDB** (optional)
- Networking via fetch/axios
- Simple state mgmt: React context + hooks or Zustand

> If the repository is already in another stack (Flutter, native iOS/Android, KMP), follow the repo conventions instead.

## Deliverables
- Working app:
  - Scan → item added to list
  - List persists across relaunch
  - Can toggle purchased, adjust qty, delete
- Basic UI polish (not perfect, but consistent)
- Tests where feasible:
  - Unit tests for dedup/quantity logic
  - Integration test for storage layer (if practical)
- Documentation:
  - Setup/run instructions
  - Brief architecture notes
  - Provider interface description

## How to work (execution plan)
1. **Initialize project structure**
   - /src
     - /features/lists
     - /features/scanner
     - /data (db, repositories)
     - /providers (barcode resolution)
     - /ui (shared components)
2. **Implement data model + storage**
   - Tables: lists, items
3. **Build list screen**
   - Display items, qty, purchased toggle
4. **Build scanner flow**
   - Permission handling
   - Scan event → add item
5. **Add product resolution provider**
   - Interface + default implementation
   - Async enrichment after insert
6. **Edge cases**
   - Duplicate scans
   - Scan spam prevention (debounce)
   - Offline mode
7. **Finalize**
   - Clean code, remove dead paths
   - Update README

## Quality bar
- No crashes on permission denial or scan failures
- Smooth UX: scan screen opens quickly, scans reliably
- Data integrity: no duplicate rows when quantity should increment
- Clear separation: UI ↔ domain ↔ persistence ↔ providers

## Decision rules
- If uncertain, choose the simplest solution that supports MVP.
- Prefer explicit types/schemas and predictable state transitions.
- Keep provider integration optional and fail-safe.

## Out of scope (for MVP)
- Account/login, cloud sync, multi-device sync
- Complex pantry tracking, recipe planning
- Advanced list sharing/collaboration
- Price comparisons / store-specific catalogs