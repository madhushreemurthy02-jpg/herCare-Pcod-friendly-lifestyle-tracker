import sqlite3

conn = sqlite3.connect('instance/hercare.db')
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables found:", tables)

for (table,) in tables:
    print(f"\n--- {table} ---")
    cur.execute(f"PRAGMA table_info({table})")
    cols = cur.fetchall()
    print("Columns:", [c[1] for c in cols])
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"Row count: {count}")

conn.close()
print("\nAll done.")
