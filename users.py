import sqlite3
from datetime import datetime

DB_NAME = "users.db"

def connect():
    return sqlite3.connect(DB_NAME)

def create_users_table():
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        joined_at TEXT,
        last_active TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def add_user(user_id, username=None, first_name=None, last_name=None):
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return
    
    cursor.execute("""
    INSERT INTO users (id, username, first_name, last_name, joined_at, last_active)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        first_name,
        last_name,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    conn.commit()
    conn.close()

def update_activity(user_id):
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET last_active=? WHERE id=?", 
                   (datetime.now().strftime("%Y-%m-%d %H:%M"), user_id))
    
    conn.commit()
    conn.close()

def get_users_count():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, last_active FROM users ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [{'id': r[0], 'last_active': r[1]} for r in rows]
