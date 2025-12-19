#!/usr/bin/env python3
"""
Quick setup script to add user-prefix mappings to the database
"""

import sqlite3

DB_FILE = 'bot_data.db'

def init_database():
    """Initialize database if it doesn't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_prefixes (
            user_id INTEGER PRIMARY KEY,
            prefix_name TEXT NOT NULL,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def add_user(user_id, prefix_name, username=None):
    """Add or update user prefix"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_prefixes (user_id, prefix_name, username)
        VALUES (?, ?, ?)
    ''', (user_id, prefix_name, username))
    conn.commit()
    conn.close()
    print(f"✅ Added: {user_id} → {prefix_name} (@{username})")

def list_users():
    """List all user mappings"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, prefix_name, username FROM user_prefixes')
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print("No users found")
        return
    
    print("\n📋 Current User Mappings:")
    print("-" * 50)
    for user_id, prefix_name, username in results:
        print(f"{user_id:12} → {prefix_name:10} (@{username})")
    print("-" * 50)

def main():
    """Main setup function"""
    print("🤖 Infinity Balance Bot - User Setup")
    print("=" * 50)
    
    init_database()
    
    # Default user mappings
    print("\n📝 Adding default users...")
    add_user(5087953529, "OKM", "ohkkamyo")
    add_user(7852335435, "MMN", "Min Myat")
    add_user(1703851340, "San", "itsnonchalantsan")
    
    print("\n💡 To add more users, use the /set_user command in Telegram (reply to user's message)")
    
    list_users()

if __name__ == '__main__':
    main()
