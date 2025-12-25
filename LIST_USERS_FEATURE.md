# /list_users Command

## Overview
The `/list_users` command displays all user prefix mappings in the system, showing user IDs, usernames, prefixes, and creation dates.

---

## Usage

Simply send the command:
```
/list_users
```

---

## Output Example

```
👥 User Prefix Mappings

1. San
   User ID: 123456789
   Username: @san_username
   Created: 2025-12-21 10:30:00

2. TZT
   User ID: 987654321
   Username: @tzt_username
   Created: 2025-12-21 11:00:00

3. MMN
   User ID: 555666777
   Username: @mmn_username
   Created: 2025-12-21 12:00:00

Total Users: 3

Commands:
• /set_user - Map user to prefix
• /list_users - Show all mappings
```

---

## Information Displayed

For each user, the command shows:

1. **Prefix Name** - The staff prefix (e.g., San, TZT, MMN)
2. **User ID** - Telegram user ID (useful for troubleshooting)
3. **Username** - Telegram username (with @ symbol)
4. **Created Date** - When the mapping was created

---

## Use Cases

### 1. View All Staff Members
Quickly see all staff members who have access to the bot and their assigned prefixes.

### 2. Troubleshooting
When a transaction fails, check the user ID to verify the correct user is mapped.

### 3. Audit User Access
Review who has access to the system and when they were added.

### 4. Verify Prefix Assignments
Confirm that users are mapped to the correct prefixes before processing transactions.

### 5. Onboarding New Staff
Show new administrators which users are already in the system.

---

## Empty State

If no users are mapped yet:

```
👥 User Prefix Mappings

No users mapped yet.

Use /set_user to map users to prefixes.
```

---

## Related Commands

- **`/set_user <prefix>`** - Map a user to a prefix (reply to their message)
- **`/start`** - Show all available commands
- **`/test`** - Test bot configuration

---

## Technical Details

### Database Query
```sql
SELECT user_id, prefix_name, username, created_at 
FROM user_prefixes 
ORDER BY prefix_name
```

### Function
```python
def get_all_users():
    """Get all user prefix mappings"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, prefix_name, username, created_at FROM user_prefixes ORDER BY prefix_name')
    results = cursor.fetchall()
    conn.close()
    return [{'user_id': r[0], 'prefix_name': r[1], 'username': r[2], 'created_at': r[3]} for r in results]
```

---

## Security Considerations

- User IDs are displayed (not sensitive information)
- Usernames are public Telegram information
- No passwords or sensitive data exposed
- Command can be restricted to admin users if needed

---

## Testing

Run the test script:
```bash
python test_list_users.py
```

Expected output:
```
✅ Found X user(s) in database
✅ Test passed! Total users: X
✅ Format test passed!
🎉 All tests passed!
```

---

## Examples

### Example 1: Small Team
```
👥 User Prefix Mappings

1. San
   User ID: 123456789
   Username: @san
   Created: 2025-12-21 10:30:00

Total Users: 1
```

### Example 2: Multiple Staff
```
👥 User Prefix Mappings

1. MMN
   User ID: 111222333
   Username: @mmn_staff
   Created: 2025-12-20 09:00:00

2. NDT
   User ID: 444555666
   Username: @ndt_staff
   Created: 2025-12-20 10:00:00

3. OKM
   User ID: 777888999
   Username: @okm_staff
   Created: 2025-12-20 11:00:00

4. San
   User ID: 123456789
   Username: @san_staff
   Created: 2025-12-19 08:00:00

5. TZT
   User ID: 987654321
   Username: @tzt_staff
   Created: 2025-12-20 12:00:00

Total Users: 5
```

### Example 3: User Without Username
```
👥 User Prefix Mappings

1. San
   User ID: 123456789
   Username: @N/A
   Created: 2025-12-21 10:30:00

Total Users: 1
```
(Some users don't have Telegram usernames)

---

## Troubleshooting

### Command Not Responding
- Check bot is running
- Verify you're in the correct group
- Check bot has permission to send messages

### No Users Shown
- Users need to be mapped first with `/set_user`
- Check database file exists: `bot_data.db`
- Verify database table: `user_prefixes`

### Wrong Information Displayed
- Database may be out of sync
- Restart bot to reload data
- Check database directly:
  ```bash
  sqlite3 bot_data.db "SELECT * FROM user_prefixes;"
  ```

---

## Future Enhancements

Possible improvements:
1. Add user removal command
2. Show last transaction date per user
3. Filter by prefix
4. Export to CSV
5. Show transaction count per user
6. Add user roles/permissions

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.3.0 | 2025-12-21 | Initial release of /list_users command |

---

## See Also

- [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) - All commands
- [FEATURES_OVERVIEW.md](FEATURES_OVERVIEW.md) - Complete features
- [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) - Testing guide
