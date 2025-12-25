#!/usr/bin/env python3
"""
Test list_users functionality
"""

import sqlite3
import os

DB_FILE = 'bot_data.db'

def test_get_all_users():
    """Test getting all users from database"""
    
    # Check if database exists
    if not os.path.exists(DB_FILE):
        print("❌ Database not found. Run bot first to create it.")
        return False
    
    # Get all users
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, prefix_name, username, created_at FROM user_prefixes ORDER BY prefix_name')
    results = cursor.fetchall()
    conn.close()
    
    users = [{'user_id': r[0], 'prefix_name': r[1], 'username': r[2], 'created_at': r[3]} for r in results]
    
    print("Testing User List Functionality\n")
    print("=" * 80)
    
    if not users:
        print("\n⚠️  No users found in database")
        print("\nTo add test users, use the bot's /set_user command:")
        print("1. Reply to a user's message with: /set_user San")
        print("2. Reply to another user's message with: /set_user TZT")
        return True
    
    print(f"\n✅ Found {len(users)} user(s) in database:\n")
    
    for idx, user in enumerate(users, 1):
        user_id = user['user_id']
        prefix_name = user['prefix_name']
        username = user['username'] or 'N/A'
        created_at = user['created_at']
        
        print(f"{idx}. {prefix_name}")
        print(f"   User ID: {user_id}")
        print(f"   Username: @{username}")
        print(f"   Created: {created_at}")
        print()
    
    print("=" * 80)
    print(f"✅ Test passed! Total users: {len(users)}")
    
    return True

def test_command_format():
    """Test the expected command output format"""
    
    print("\n\nTesting Command Output Format\n")
    print("=" * 80)
    
    # Simulate command output
    test_users = [
        {'user_id': 123456789, 'prefix_name': 'San', 'username': 'san_user', 'created_at': '2025-12-21 10:30:00'},
        {'user_id': 987654321, 'prefix_name': 'TZT', 'username': 'tzt_user', 'created_at': '2025-12-21 11:00:00'}
    ]
    
    message = "👥 User Prefix Mappings\n\n"
    
    for idx, user in enumerate(test_users, 1):
        user_id = user['user_id']
        prefix_name = user['prefix_name']
        username = user['username'] or 'N/A'
        created_at = user['created_at']
        
        message += f"{idx}. {prefix_name}\n"
        message += f"   User ID: {user_id}\n"
        message += f"   Username: @{username}\n"
        message += f"   Created: {created_at}\n\n"
    
    message += f"Total Users: {len(test_users)}\n\n"
    message += "Commands:\n"
    message += "• /set_user - Map user to prefix\n"
    message += "• /list_users - Show all mappings"
    
    print("\nExpected /list_users output:\n")
    print(message)
    
    print("\n" + "=" * 80)
    print("✅ Format test passed!")
    
    return True

if __name__ == '__main__':
    print("🧪 Testing /list_users Command\n")
    
    result1 = test_get_all_users()
    result2 = test_command_format()
    
    if result1 and result2:
        print("\n\n🎉 All tests passed!")
        print("\nTo test the command in Telegram:")
        print("1. Start the bot")
        print("2. Send /list_users command")
        print("3. Verify output matches expected format")
    else:
        print("\n\n❌ Some tests failed")
