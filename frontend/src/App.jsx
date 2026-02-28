import React from "react";
import { useCallback, useMemo, useState } from "react";
import { CameraScanner } from "./components/CameraScanner";
import { useShoppingList } from "./state/useShoppingList";

export function App() {
  const {
    items,
    updateItem,
    deleteItem,
    submitScan,
    reload,
  } = useShoppingList();
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [showSummary, setShowSummary] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const isEmpty = items.length === 0;

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedItemId) ?? null,
    [items, selectedItemId]
  );

  const totalCount = useMemo(
    () => items.reduce((sum, item) => sum + (item.quantity ?? 0), 0),
    [items]
  );

  const purchasedItems = useMemo(
    () => items.filter((item) => item.purchased === 1 || item.purchased === true),
    [items]
  );

  const clearPurchased = async () => {
    if (purchasedItems.length === 0) {
      setShowSummary(false);
      return;
    }
    await Promise.all(purchasedItems.map((item) => deleteItem(item.id)));
    await reload();
    setShowSummary(false);
  };

  const clearAll = async () => {
    await Promise.all(items.map((item) => deleteItem(item.id)));
    await reload();
    setShowSummary(false);
  };

  const handleScan = useCallback(
    async (barcode) => {
      const result = await submitScan(barcode);
      if (result?.accepted) {
        setShowScanner(false);
      }
      return result;
    },
    [submitScan]
  );

  return (
    <div className="figma-shell">
      <main className="screen">
        <header className="topbar">
          <h1>GROCERIES</h1>
          <button className="topbar-scan" onClick={() => setShowScanner((v) => !v)}>
            SCAN
          </button>
        </header>

        {isEmpty ? (
          <>
            <section className="empty-state">
              <div className="empty-block" />
              <div className="empty-art">
                <pre>{`[  ALL  ]\n[ CLEAR ]`}</pre>
              </div>
              <div className="empty-copy">
                <h2>ALL CLEAR</h2>
                <p>YOUR LIST IS EMPTY</p>
              </div>
              <button className="empty-primary" onClick={() => setShowScanner(true)}>
                START SCANNING
              </button>
              <button className="empty-secondary" onClick={() => setShowScanner(true)}>
                ADD FIRST ITEM
              </button>
            </section>
            <nav className="empty-nav">
              <button>LIST</button>
              <button className="is-active">EMPTY</button>
              <button>TRIP</button>
            </nav>
          </>
        ) : (
          <>
            <section className="list-stream">
              {items.map((item) => (
                <article
                  key={item.id}
                  className={`stream-row ${item.purchased ? "stream-row--checked" : ""}`}
                  onClick={() => setSelectedItemId(item.id)}
                >
                  <div className="thumb">
                    {item.imageUrl ? (
                      <img src={item.imageUrl} alt={item.name || "Product"} loading="lazy" />
                    ) : (
                      <span>{(item.name || "?").slice(0, 1).toUpperCase()}</span>
                    )}
                  </div>
                  <div className="row-copy">
                    <h2>{item.name || "Unknown item"}</h2>
                    <p>QTY: {String(item.quantity).padStart(2, "0")}</p>
                  </div>
                  <button
                    className={`check ${item.purchased ? "check--on" : ""}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      updateItem(item.id, { purchased: !item.purchased });
                    }}
                  >
                    {item.purchased ? "X" : ""}
                  </button>
                </article>
              ))}
            </section>
            <footer className="trip-cta" onClick={() => setShowSummary(true)}>
              <span>END TRIP</span>
              <span>{String(totalCount).padStart(2, "0")} ITEMS</span>
            </footer>
          </>
        )}
      </main>

      {showScanner ? (
        <section className="overlay">
          <div className="panel">
            <button className="panel-close" onClick={() => setShowScanner(false)}>
              CLOSE
            </button>
            <CameraScanner onScan={handleScan} />
          </div>
        </section>
      ) : null}

      {selectedItem ? (
        <section className="detail detail--fullscreen">
          <header className="detail-nav">
            <button onClick={() => setSelectedItemId(null)}>BACK</button>
          </header>

          <div className="detail-hero">
            <div className="detail-hero-box">
              {selectedItem.imageUrl ? (
                <img src={selectedItem.imageUrl} alt={selectedItem.name || "Product"} />
              ) : (
                <span>{(selectedItem.name || "?").slice(0, 1).toUpperCase()}</span>
              )}
            </div>
          </div>

          <div className="detail-head">
            <h2>{selectedItem.name || "Unknown item"}</h2>
            <p>{selectedItem.barcode || "NO BARCODE"}</p>
          </div>

          <div className="stepper">
            <label>SELECT QUANTITY</label>
            <div className="stepper-control">
              <button
                onClick={() =>
                  updateItem(selectedItem.id, {
                    quantity: Math.max(1, selectedItem.quantity - 1),
                  })
                }
              >
                -
              </button>
              <strong>{String(selectedItem.quantity).padStart(2, "0")}</strong>
              <button onClick={() => updateItem(selectedItem.id, { quantity: selectedItem.quantity + 1 })}>
                +
              </button>
            </div>
          </div>

          <div className="detail-actions">
            <button onClick={() => updateItem(selectedItem.id, { purchased: !selectedItem.purchased })}>
              {selectedItem.purchased ? "MARK UNPURCHASED" : "MARK PURCHASED"}
            </button>
            <button
              onClick={async () => {
                await deleteItem(selectedItem.id);
                setSelectedItemId(null);
              }}
            >
              DELETE ITEM
            </button>
          </div>
        </section>
      ) : null}

      {showSummary ? (
        <section className="overlay overlay--dim">
          <div className="receipt">
            <div className="grabber" />
            <h3>CHECKOUT SUMMARY</h3>
            <p className="receipt-meta">TODAY</p>
            <div className="receipt-list">
              {items.map((item) => (
                <div key={item.id} className="receipt-row">
                  <span>{(item.name || "UNKNOWN").toUpperCase()}</span>
                  <span>[{String(item.quantity).padStart(2, "0")}]</span>
                </div>
              ))}
            </div>
            <div className="receipt-total">
              <span>TOTAL ITEMS:</span>
              <span>{String(totalCount).padStart(2, "0")}</span>
            </div>
            <button className="btn-primary" onClick={clearPurchased} disabled={purchasedItems.length === 0}>
              CLEAR PURCHASED
            </button>
            <button className="btn-danger" onClick={clearAll} disabled={items.length === 0}>
              DELETE ALL ITEMS
            </button>
            <button className="btn-link" onClick={() => setShowSummary(false)}>
              CANCEL
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
