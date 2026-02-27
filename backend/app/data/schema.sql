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
