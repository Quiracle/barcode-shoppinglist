from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data.db import DEFAULT_LIST_ID, Database
from app.data.repositories import ShoppingRepository
from app.domain.add_or_increment import add_or_increment_item
from app.domain.models import ScanDebouncer
from app.domain.schemas import ItemPatch, ManualItemCreate, ShoppingListCreate
from app.providers.noop import NoopLookupProvider
from app.scanner.evdev_reader import EvdevScannerReader, scanner_config_from_env

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class WebSocketHub:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self.connections)
        stale = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    self.connections.discard(ws)


app = FastAPI(title="Barcode Shopping List")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("SQLITE_PATH", str(Path(__file__).resolve().parents[2] / "data" / "shopping.db"))
BARCODE_LENGTHS = tuple(int(v) for v in os.getenv("BARCODE_LENGTHS", "8,12,13,14").split(",") if v.strip())


db = Database(DB_PATH)
repo = ShoppingRepository(db)
debouncer = ScanDebouncer(window_ms=int(os.getenv("SCAN_DEBOUNCE_MS", "800")))
ws_hub = WebSocketHub()
lookup_provider = NoopLookupProvider()

scanner_reader = EvdevScannerReader(
    config=scanner_config_from_env(),
    on_scan=lambda code: handle_scanned_barcode(code),
)


def maybe_enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    barcode = item.get("barcode")
    if not barcode:
        return item
    info = lookup_provider.lookup(barcode)
    if info is None:
        return item

    patch_fields: dict[str, Any] = {}
    if item.get("userEditedName", 0) == 0 and item.get("name") == "Unknown item":
        patch_fields["name"] = info.name
    if info.brand:
        patch_fields["brand"] = info.brand
    if info.image_url:
        patch_fields["imageUrl"] = info.image_url

    if not patch_fields:
        return item

    updated = repo.update_item(item["id"], **patch_fields)
    return updated or item


def handle_scanned_barcode(barcode: str) -> None:
    item = add_or_increment_item(
        repository=repo,
        debouncer=debouncer,
        list_id=DEFAULT_LIST_ID,
        barcode=barcode,
        allowed_lengths=BARCODE_LENGTHS,
    )
    if item is None:
        return

    enriched = maybe_enrich_item(item)

    async def _broadcast() -> None:
        event_type = "item_updated" if enriched["id"] == item["id"] and enriched["quantity"] > 1 else "item_added"
        await ws_hub.broadcast({"type": event_type, "listId": enriched["listId"], "item": enriched})

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_broadcast())
    except RuntimeError:
        # Scanner callback runs in thread; fallback to main loop scheduling.
        app_loop = getattr(app.state, "loop", None)
        if app_loop is not None:
            asyncio.run_coroutine_threadsafe(_broadcast(), app_loop)


@app.on_event("startup")
async def startup_event() -> None:
    app.state.loop = asyncio.get_running_loop()
    scanner_reader.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    scanner_reader.stop()


@app.get("/api/lists")
def get_lists() -> list[dict[str, Any]]:
    return repo.list_lists()


@app.post("/api/lists")
def create_list(payload: ShoppingListCreate) -> dict[str, Any]:
    return repo.create_list(payload.name)


@app.get("/api/lists/{list_id}/items")
def get_items(list_id: str) -> list[dict[str, Any]]:
    existing = repo.get_list(list_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="List not found")
    return repo.get_items(list_id)


@app.post("/api/lists/{list_id}/items/manual")
async def add_manual_item(list_id: str, payload: ManualItemCreate) -> dict[str, Any]:
    existing = repo.get_list(list_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="List not found")

    item = repo.create_item(
        list_id=list_id,
        name=payload.name,
        quantity=payload.quantity,
        barcode=payload.barcode,
        purchased=0,
        user_edited_name=1,
    )
    await ws_hub.broadcast({"type": "item_added", "listId": list_id, "item": item})
    return item


@app.patch("/api/items/{item_id}")
async def patch_item(item_id: str, payload: ItemPatch) -> dict[str, Any]:
    fields = payload.model_dump(exclude_unset=True)
    updated = repo.update_item(item_id, **fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    await ws_hub.broadcast({"type": "item_updated", "listId": updated["listId"], "item": updated})
    return updated


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: str) -> dict[str, Any]:
    deleted = repo.delete_item(item_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Item not found")
    await ws_hub.broadcast({"type": "item_deleted", "listId": deleted["listId"], "item": deleted})
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_hub.disconnect(websocket)
    except Exception:
        await ws_hub.disconnect(websocket)


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "backend_running", "message": "Build frontend to serve UI from this endpoint."}
