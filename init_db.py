# init_db.py
import sqlite3

def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            gold_price_per_gram REAL
        )
    ''')

    # Insert dummy data rows (optional)
    cursor.executemany('''
        INSERT INTO prices (item_name, gold_price_per_gram)
        VALUES (?, ?)
    ''', [
        ("Item A", 0.0),
        ("Item B", 0.0),
        ("Item C", 0.0)
    ])

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database and table initialized.")
