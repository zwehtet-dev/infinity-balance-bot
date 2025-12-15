# Command Reference - Infinity Balance Bot

Quick reference guide for all available commands.

---

## General Commands

### `/start`
Show bot status and help information.

**Usage:**
```
/start
```

**Output:**
- Bot description
- Feature highlights
- Complete command list organized by category

---

### `/balance`
Display current balance for all currencies (MMK, USDT, THB).

**Usage:**
```
/balance
```

**Output:**
```
📊 Balance:

MMK
San(KBZ) -11,044,185
San(Wave) -1,220,723
...

USDT
San(Binance) -50.00
San(Swift) -81.99
...

THB
ACT(Bkk B) -13,223
```

---

### `/load`
Load balance from a message.

**Usage:**
```
Reply to a balance message with: /load
```

**Example:**
1. Find balance message in Auto Balance topic
2. Reply to it with `/load`
3. Bot loads the balance

---

### `/test`
Test bot configuration and connection.

**Usage:**
```
/test
```

**Output:**
- Current chat and thread information
- Bot configuration (group ID, topic IDs)
- Connection status checks
- Location verification

---

## User Management

### `/set_user`
Map a staff member to their prefix name.

**Usage (Reply Method):**
```
Reply to user's message with: /set_user San
```

**Usage (Direct Method):**
```
/set_user @username San
/set_user 123456789 San
```

**Parameters:**
- `prefix_name` - Staff prefix (e.g., San, NDT, MMN, TZT)

**Example:**
```
Admin replies to San's message:
/set_user San

Bot: ✅ Set prefix 'San' for @san_username (ID: 123456789)
```

---

## USDT Configuration

### `/set_receiving_usdt_acc`
Set the USDT receiving account for buy transactions.

**Usage:**
```
/set_receiving_usdt_acc ACT(Wallet)
```

**Parameters:**
- `account_name` - USDT account name (must exist in balance)

**Example:**
```
/set_receiving_usdt_acc ACT(Wallet)

Bot: ✅ Receiving USDT account set to: ACT(Wallet)
```

**Default:** `ACT(Wallet)`

---

### `/show_receiving_usdt_acc`
Show the current USDT receiving account configuration.

**Usage:**
```
/show_receiving_usdt_acc
```

**Output:**
```
💰 USDT Receiving Account Configuration

Current Account: ACT(Wallet)

Purpose:
This account receives USDT when customers buy USDT from us.

How it works:
• Customer: Buy 100 USDT = 2,500,000 MMK
• Staff sends MMK to customer
• Bot adds 100 USDT to ACT(Wallet)

Note: For sell transactions, USDT is reduced from staff-specific 
accounts (Binance/Swift/Wallet) based on the receipt type.

Change Account:
Use /set_receiving_usdt_acc to change the receiving account.
```

---

## MMK Bank Management

### `/set_mmk_bank`
Register a new MMK bank account for verification.

**Usage:**
```
/set_mmk_bank Bank_Name | Account_Number | Account_Holder_Name
```

**Parameters:**
- `Bank_Name` - Bank name with prefix (e.g., San(KBZ))
- `Account_Number` - Full account number
- `Account_Holder_Name` - Account holder's full name

**Example:**
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR

Bot: ✅ MMK bank account registered!

Bank: San(KBZ)
Account: 27251127201844001
Holder: CHAW SU THU ZAR
```

**Default Banks (Auto-registered):**
- San(CB) | 0225100900026042 | Chaw Su Thu Zar
- San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
- San(Yoma) | 007011118014339 | Daw Chaw Su Thu Zar
- San(Kpay P) | 300948464 | Chaw Su
- San(AYA) | 40038204256 | CHAW SU THU ZAR

---

### `/list_mmk_bank`
List all registered MMK bank accounts.

**Usage:**
```
/list_mmk_bank
```

**Output:**
```
📋 Registered MMK Bank Accounts

1. San(CB)
   Account: 0225****6042
   Holder: Chaw Su Thu Zar

2. San(KBZ)
   Account: 2725****4001
   Holder: CHAW SU THU ZAR

3. San(Yoma)
   Account: 0070****4339
   Holder: Daw Chaw Su Thu Zar

Commands:
• /set_mmk_bank - Register new bank
• /edit_mmk_bank - Edit existing bank
• /remove_mmk_bank - Remove bank
```

**Features:**
- Shows all registered banks
- Masks account numbers (first 4 + last 4 digits shown)
- Displays full holder names
- Includes quick command links

---

### `/edit_mmk_bank`
Edit an existing MMK bank account.

**Usage:**
```
/edit_mmk_bank Bank_Name | New_Account_Number | New_Holder_Name
```

**Parameters:**
- `Bank_Name` - Existing bank name (must match exactly)
- `New_Account_Number` - Updated account number
- `New_Holder_Name` - Updated holder name

**Example:**
```
/edit_mmk_bank San(KBZ) | 27251127201844999 | NEW HOLDER NAME

Bot: ✅ MMK bank account updated!

Bank: San(KBZ)
Old Account: 27251127201844001
New Account: 27251127201844999
Old Holder: CHAW SU THU ZAR
New Holder: NEW HOLDER NAME
```

---

### `/remove_mmk_bank`
Remove a registered MMK bank account.

**Usage:**
```
/remove_mmk_bank Bank_Name
```

**Parameters:**
- `Bank_Name` - Bank name to remove (must match exactly)

**Example:**
```
/remove_mmk_bank San(KBZ)

Bot: ✅ MMK bank account removed!

Bank: San(KBZ)
Account: 27251127201844001
Holder: CHAW SU THU ZAR
```

**Warning:** This action cannot be undone. You'll need to re-register the bank if removed by mistake.

---

## Transaction Formats

### Buy Transaction
Customer buys USDT, staff sends MMK.

**Format:**
```
Customer posts:
Buy 100 USDT = 2,500,000 MMK
[Customer's USDT receipt]

Staff replies:
[MMK receipt photo]
```

---

### Sell Transaction
Customer sells USDT, staff sends USDT.

**Format:**
```
Customer posts:
Sell 100 USDT = 2,500,000 MMK
[Customer's MMK receipt]

Staff replies:
[USDT receipt photo - Binance/Swift/Wallet]
```

---

### P2P Sell Transaction
Staff sells USDT to exchange.

**Format:**
```
Staff posts directly (not a reply):
[MMK receipt photo]
sell 13000000/3222.6=4034.00981 fee-6.44
```

**Components:**
- `sell` - Transaction type
- `13000000` - MMK amount received
- `3222.6` - USDT amount sent
- `4034.00981` - Exchange rate
- `fee-6.44` - Transaction fee in USDT

---

### Internal Transfer
Transfer between staff accounts.

**Format:**
```
In Accounts Matter topic:
San(Wave Channel) to NDT(Wave)
[Transfer receipt photo]
```

---

## Command Categories

### Information Commands
- `/start` - Help and status
- `/balance` - Show balance
- `/test` - Test configuration
- `/list_mmk_bank` - List banks
- `/show_receiving_usdt_acc` - Show USDT config

### Configuration Commands
- `/load` - Load balance
- `/set_user` - Map user to prefix
- `/set_receiving_usdt_acc` - Set USDT account
- `/set_mmk_bank` - Register bank
- `/edit_mmk_bank` - Edit bank
- `/remove_mmk_bank` - Remove bank

---

## Tips

1. **Use `/list_mmk_bank` regularly** to verify registered banks
2. **Use `/show_receiving_usdt_acc`** to check USDT configuration
3. **Use `/test`** in different topics to verify bot location
4. **Use `/balance`** to check current balances before transactions
5. **Reply to user messages** when using `/set_user` for easier mapping

---

## Common Issues

### Command not working?
- Check if you're in the correct group
- Verify you're in the right topic (use `/test`)
- Ensure command syntax is correct
- Check for typos in bank names (case-sensitive)

### Bank not found?
- Use `/list_mmk_bank` to see registered banks
- Verify bank name matches exactly (including prefix)
- Register bank with `/set_mmk_bank` if missing

### USDT not added to correct account?
- Use `/show_receiving_usdt_acc` to check configuration
- Change with `/set_receiving_usdt_acc` if needed
- Ensure account exists in balance

---

## Quick Reference Table

| Command | Purpose | Usage |
|---------|---------|-------|
| `/start` | Help | `/start` |
| `/balance` | Show balance | `/balance` |
| `/load` | Load balance | Reply: `/load` |
| `/test` | Test config | `/test` |
| `/set_user` | Map user | Reply: `/set_user San` |
| `/set_receiving_usdt_acc` | Set USDT account | `/set_receiving_usdt_acc ACT(Wallet)` |
| `/show_receiving_usdt_acc` | Show USDT config | `/show_receiving_usdt_acc` |
| `/set_mmk_bank` | Register bank | `/set_mmk_bank San(KBZ) \| 123 \| Name` |
| `/list_mmk_bank` | List banks | `/list_mmk_bank` |
| `/edit_mmk_bank` | Edit bank | `/edit_mmk_bank San(KBZ) \| 456 \| Name` |
| `/remove_mmk_bank` | Remove bank | `/remove_mmk_bank San(KBZ)` |

---

## Support

For detailed information about features, see:
- `FEATURES_OVERVIEW.md` - Complete feature list
- `UPDATES.md` - Changelog and updates
- `README.md` - Setup and installation
- `QUICKSTART_V2.md` - Quick start guide
