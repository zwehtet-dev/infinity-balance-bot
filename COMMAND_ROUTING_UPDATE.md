# Command Routing Update

## Summary
Updated all bot commands to send responses to the **Alert Topic** instead of replying in the general chat or wherever the command was sent.

## Changes Made

### 1. New Helper Function
Added `send_command_response()` function that:
- Sends all command responses to the Alert Topic (if configured)
- Falls back to general chat if Alert Topic is not configured
- Supports HTML/Markdown parse modes

### 2. Updated Commands
All command handlers now use `send_command_response()`:
- `/start` - Bot status and help
- `/balance` - Show current balance
- `/load` - Load balance from message
- `/set_user` - Set user prefix mapping
- `/set_receiving_usdt_acc` - Configure USDT receiving account
- `/show_receiving_usdt_acc` - Show current USDT account
- `/set_mmk_bank` - Register MMK bank account
- `/list_mmk_bank` - List all registered banks
- `/edit_mmk_bank` - Edit existing bank
- `/remove_mmk_bank` - Remove bank
- `/test` - Test configuration

## Message Routing

### Auto Balance Topic
- Balance updates after transactions
- New balance messages

### Alert Topic
- All command responses
- Error messages
- Warning messages
- Transaction alerts

## Benefits
1. **Cleaner general chat** - No command spam
2. **Organized topics** - Commands in Alert, balances in Auto Balance
3. **Better tracking** - All admin commands in one place
4. **Consistent behavior** - All commands follow same routing

## Configuration
Ensure `.env` has:
```
ALERT_TOPIC_ID=<your_alert_topic_id>
AUTO_BALANCE_TOPIC_ID=<your_balance_topic_id>
```
