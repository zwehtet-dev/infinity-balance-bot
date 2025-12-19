# Alert Topic Feature

## Overview
All error (❌) and warning (⚠️) messages are now sent to a dedicated alert topic instead of cluttering the transaction topics.

## Configuration

### Environment Variable
Add to your `.env` file:
```
ALERT_TOPIC_ID=0  # Set to your alert topic ID (0 = disabled, sends to reply instead)
```

### Setup
1. Create a dedicated "Alerts" topic in your Telegram group
2. Get the topic ID (you can see it in the URL or by forwarding a message from that topic)
3. Update `ALERT_TOPIC_ID` in your `.env` file with the topic ID
4. Restart the bot

## Behavior

### When ALERT_TOPIC_ID is set (non-zero)
- All error messages (❌) are sent to the alert topic
- All warning messages (⚠️) are sent to the alert topic
- Balance updates continue to go to Auto Balance topic
- Status messages remain commented out (silent operation)

### When ALERT_TOPIC_ID is 0 or not set
- Error and warning messages are sent as replies to the original message (legacy behavior)

## Alert Message Types

### Error Messages (❌)
- Balance not loaded
- No receipt photo
- User prefix not set
- Could not detect bank/amount
- Bank not found
- Insufficient balance
- USDT amount mismatch
- Transfer amount detection failed
- And more...

### Warning Messages (⚠️)
- Receiving USDT account not found in balance

## Benefits
1. **Clean transaction topics**: USDT Transfers and Accounts Matter topics remain clean
2. **Centralized monitoring**: All errors and warnings in one place
3. **Easy troubleshooting**: Staff can quickly see what went wrong
4. **No noise**: Only balance updates are sent to Auto Balance topic

## Example Alert Messages

```
❌ Balance not loaded. Post balance message in auto balance topic first.
```

```
❌ You don't have a prefix set. Admin needs to use /set_user command.
```

```
⚠️ Warning: Receiving USDT account 'ACT(Wallet)' not found in balance. USDT not added.
```

```
❌ Could not detect bank/amount from user receipt
```

## Implementation Details
- Uses `send_alert()` helper function
- Automatically routes to alert topic if configured
- Falls back to reply if alert topic not configured
- All error/warning messages updated to use this system
