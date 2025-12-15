# Receiving USDT Account Configuration

## Overview

For buy transactions, USDT is now added to a single **receiving account** instead of being distributed based on staff prefixes. This simplifies USDT management and allows you to designate one account to receive all incoming USDT.

## Default Setting

**Default receiving account:** `ACT(Wallet)`

This is automatically set when the bot starts for the first time.

## Commands

### View Current Setting

```
/set_receiving_usdt_acc
```

Shows the current receiving USDT account.

**Response:**
```
📊 Current Receiving USDT Account:
ACT(Wallet)

Usage:
/set_receiving_usdt_acc <account_name>

Example:
/set_receiving_usdt_acc ACT(Wallet)
/set_receiving_usdt_acc San(Swift)
```

### Change Receiving Account

```
/set_receiving_usdt_acc ACT(Wallet)
/set_receiving_usdt_acc San(Swift)
/set_receiving_usdt_acc MMN(Binance)
```

**Response:**
```
✅ Receiving USDT Account Updated!

New account: ACT(Wallet)

All buy transactions will now add USDT to this account.
```

## How It Works

### Buy Transaction Flow

1. **Customer posts:** `Buy 100 = 2,500,000`
2. **Staff (San) replies** with MMK receipt photo
3. **Bot processes:**
   - Reduces MMK from `San(KBZ)` (staff's bank)
   - Adds USDT to `ACT(Wallet)` (receiving account)
4. **Balance updated:**
   - `San(KBZ)`: -2,500,000 MMK
   - `ACT(Wallet)`: +100 USDT

### Sell Transaction Flow

Sell transactions remain **staff-specific**:

1. **Customer posts:** `Sell 100 = 2,500,000` with MMK receipt
2. **Staff (San) replies** with USDT receipt photo
3. **Bot processes:**
   - Adds MMK to `San(KBZ)` (staff's bank)
   - Reduces USDT from `San(Swift)` (staff's USDT account)
4. **Balance updated:**
   - `San(KBZ)`: +2,500,000 MMK
   - `San(Swift)`: -100 USDT

## Database Storage

The receiving USDT account is stored in the SQLite database:

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Record:**
```
key: 'receiving_usdt_account'
value: 'ACT(Wallet)'
```

## Examples

### Example 1: Set to ACT(Wallet)

```
/set_receiving_usdt_acc ACT(Wallet)
```

**Result:**
- All buy transactions add USDT to `ACT(Wallet)`

### Example 2: Set to San(Swift)

```
/set_receiving_usdt_acc San(Swift)
```

**Result:**
- All buy transactions add USDT to `San(Swift)`

### Example 3: Set to MMN(Binance)

```
/set_receiving_usdt_acc MMN(Binance)
```

**Result:**
- All buy transactions add USDT to `MMN(Binance)`

## Important Notes

### 1. Account Must Exist in Balance

The receiving account **must exist** in your balance message:

```
USDT
San(Swift) -81.99
MMN(Binance) -15.86
ACT(Wallet) -1104.91  ← Must be present
```

If the account doesn't exist, you'll see a warning:
```
⚠️ Warning: Receiving USDT account 'ACT(Wallet)' not found in balance. USDT not added.
```

### 2. Single Receiving Account

Only **one account** receives USDT from buy transactions. This makes it easier to:
- Track incoming USDT
- Manage USDT distribution
- Monitor total USDT received

### 3. Sell Transactions Unchanged

Sell transactions still use **staff-specific** USDT accounts based on who processes the transaction.

## Use Cases

### Use Case 1: Centralized USDT Management

Set receiving account to a main wallet:
```
/set_receiving_usdt_acc ACT(Wallet)
```

All incoming USDT goes to `ACT(Wallet)`, making it easy to:
- Track total USDT received
- Distribute to staff as needed
- Manage liquidity

### Use Case 2: Staff-Specific Receiving

Set receiving account to a specific staff member:
```
/set_receiving_usdt_acc San(Swift)
```

All incoming USDT goes to San's account.

### Use Case 3: Exchange Account

Set receiving account to an exchange:
```
/set_receiving_usdt_acc MMN(Binance)
```

All incoming USDT goes directly to Binance for trading.

## Migration

### From Old System

**Old behavior:**
- USDT added to staff member's account based on who processed the transaction

**New behavior:**
- USDT added to designated receiving account
- Default: `ACT(Wallet)`

### No Action Required

The bot automatically:
1. Creates the settings table
2. Sets default to `ACT(Wallet)`
3. Uses the receiving account for all buy transactions

### Optional: Change Default

If you want a different receiving account:
```
/set_receiving_usdt_acc YourAccount(YourBank)
```

## Troubleshooting

### Issue: USDT Not Added

**Symptom:**
```
⚠️ Warning: Receiving USDT account 'ACT(Wallet)' not found in balance. USDT not added.
```

**Solution:**
1. Check your balance message includes the account:
   ```
   USDT
   ACT(Wallet) -1104.91
   ```
2. Or change to an existing account:
   ```
   /set_receiving_usdt_acc San(Swift)
   ```

### Issue: Wrong Account Receiving USDT

**Solution:**
Change the receiving account:
```
/set_receiving_usdt_acc CorrectAccount(Bank)
```

### Issue: Want to Check Current Setting

**Solution:**
Run command without arguments:
```
/set_receiving_usdt_acc
```

## Summary

✅ **Buy transactions:** USDT → Receiving account (configurable)
✅ **Sell transactions:** USDT → Staff's account (based on who processes)
✅ **Default:** `ACT(Wallet)`
✅ **Configurable:** Use `/set_receiving_usdt_acc` command
✅ **Persistent:** Stored in database
✅ **Flexible:** Change anytime

This feature simplifies USDT management while maintaining staff-specific tracking for sell transactions.
