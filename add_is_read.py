import sqlite3

def upgrade():
    conn = sqlite3.connect('whatsapp.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_read BOOLEAN DEFAULT 0;")
        print("Column is_read added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error (maybe column already exists?): {e}")
    conn.commit()
    
    # Mark all old messages as read so the user isn't spammed with old unread counts
    cursor.execute("UPDATE messages SET is_read = 1;")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade()
