import { useMemo, useState } from "react";

export function ItemRow({ item, onUpdate, onDelete }) {
  const [draftName, setDraftName] = useState(item.name);

  const qty = useMemo(() => Math.max(1, item.quantity ?? 1), [item.quantity]);

  return (
    <article className={`item-row ${item.purchased ? "item-row--done" : ""}`}>
      <label className="purchase-toggle">
        <input
          type="checkbox"
          checked={Boolean(item.purchased)}
          onChange={(event) => onUpdate(item.id, { purchased: event.target.checked })}
        />
        <span>{item.purchased ? "Purchased" : "To buy"}</span>
      </label>

      <div className="item-main">
        <input
          className="item-name"
          value={draftName}
          onChange={(event) => setDraftName(event.target.value)}
          onBlur={() => {
            if (draftName.trim() && draftName !== item.name) {
              onUpdate(item.id, { name: draftName.trim(), userEditedName: true });
            }
          }}
        />
        <div className="item-meta">{item.brand || item.barcode || "No barcode"}</div>
      </div>

      <div className="qty-controls">
        <button onClick={() => onUpdate(item.id, { quantity: Math.max(1, qty - 1) })}>-</button>
        <span>{qty}</span>
        <button onClick={() => onUpdate(item.id, { quantity: qty + 1 })}>+</button>
      </div>

      <button className="delete-btn" onClick={() => onDelete(item.id)}>
        Delete
      </button>
    </article>
  );
}
