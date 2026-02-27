import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../api/client";

const DEFAULT_LIST_ID = "default";

export function useShoppingList() {
  const [lists, setLists] = useState([]);
  const [items, setItems] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const activeList = useMemo(
    () => lists.find((list) => list.id === DEFAULT_LIST_ID) ?? lists[0] ?? null,
    [lists]
  );

  const activeListId = activeList?.id ?? DEFAULT_LIST_ID;

  const load = useCallback(async () => {
    const fetchedLists = await apiGet("/api/lists");
    setLists(fetchedLists);

    const listId = fetchedLists.find((list) => list.id === DEFAULT_LIST_ID)?.id ?? fetchedLists[0]?.id;
    if (!listId) {
      setItems([]);
      return;
    }
    const fetchedItems = await apiGet(`/api/lists/${listId}/items`);
    setItems(fetchedItems);
  }, []);

  useEffect(() => {
    load().catch(() => {
      setConnectionStatus("error");
    });
  }, [load]);

  const applyEvent = useCallback((event) => {
    const { type, item } = event;
    if (!item) return;

    setItems((current) => {
      if (type === "item_added" || type === "item_updated") {
        const idx = current.findIndex((it) => it.id === item.id);
        if (idx === -1) return [item, ...current];
        const clone = [...current];
        clone[idx] = item;
        return clone;
      }
      if (type === "item_deleted") {
        return current.filter((it) => it.id !== item.id);
      }
      return current;
    });
  }, []);

  useEffect(() => {
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setConnectionStatus("connecting");

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus("connected");
        ws.send("ping");
      };

      ws.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          applyEvent(event);
        } catch {
          // ignore malformed events
        }
      };

      ws.onclose = () => {
        setConnectionStatus("reconnecting");
        reconnectTimer.current = setTimeout(connect, 1500);
      };

      ws.onerror = () => {
        setConnectionStatus("error");
        ws.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [applyEvent]);

  const updateItem = useCallback(async (itemId, patch) => {
    const updated = await apiPatch(`/api/items/${itemId}`, patch);
    setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }, []);

  const deleteItem = useCallback(async (itemId) => {
    await apiDelete(`/api/items/${itemId}`);
    setItems((current) => current.filter((item) => item.id !== itemId));
  }, []);

  const submitScan = useCallback(
    async (barcode) => {
      if (!barcode || !barcode.trim()) return { accepted: false, item: null };
      const result = await apiPost("/api/scans", {
        barcode: barcode.trim(),
        listId: activeListId,
      });
      if (result?.item) {
        setItems((current) => {
          const idx = current.findIndex((it) => it.id === result.item.id);
          if (idx === -1) return [result.item, ...current];
          const clone = [...current];
          clone[idx] = result.item;
          return clone;
        });
      }
      return result;
    },
    [activeListId]
  );

  const toBuy = useMemo(
    () => items.filter((item) => item.purchased === 0 || item.purchased === false),
    [items]
  );

  const purchased = useMemo(
    () => items.filter((item) => item.purchased === 1 || item.purchased === true),
    [items]
  );

  return {
    activeList,
    activeListId,
    items,
    toBuy,
    purchased,
    connectionStatus,
    updateItem,
    deleteItem,
    submitScan,
    reload: load,
  };
}
