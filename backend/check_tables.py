import sqlite3

conn = sqlite3.connect('test_migration.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    
    # Show columns for our tables
    if 'repository_symbols' in table[0] or 'repository_files' in table[0] or 'repositories' in table[0]:
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print(f"    Columns:")
        for col in columns:
            print(f"      {col[1]} ({col[2]})")

conn.close()