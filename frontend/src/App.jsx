import { Header } from "./components/Header";
import { ItemRow } from "./components/ItemRow";
import { useShoppingList } from "./state/useShoppingList";

export function App() {
  const {
    activeList,
    toBuy,
    purchased,
    connectionStatus,
    updateItem,
    deleteItem,
  } = useShoppingList();

  return (
    <main className="page">
      <Header listName={activeList?.name} connectionStatus={connectionStatus} />

      <section className="list-section">
        <h2>To buy</h2>
        <div className="items-grid">
          {toBuy.length === 0 ? <p className="empty">No pending items</p> : null}
          {toBuy.map((item) => (
            <ItemRow key={item.id} item={item} onUpdate={updateItem} onDelete={deleteItem} />
          ))}
        </div>
      </section>

      <section className="list-section">
        <h2>Purchased</h2>
        <div className="items-grid">
          {purchased.length === 0 ? <p className="empty">No purchased items</p> : null}
          {purchased.map((item) => (
            <ItemRow key={item.id} item={item} onUpdate={updateItem} onDelete={deleteItem} />
          ))}
        </div>
      </section>
    </main>
  );
}
