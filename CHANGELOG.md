# Changelog

## Version 2.3.9 - Complete Alert Notifications

### 🐛 Bug Fixes

#### Added Missing Alert Notifications for All Error Cases
- **Fixed**: All error messages now send notifications to alert topic
- **Added alerts for**:
  - Insufficient MMK balance in buy transactions
  - Insufficient balance in internal transfers
  - Insufficient MMK balance in bulk buy transactions
  - USDT amount mismatch in bulk sell transactions (now warns but continues)

#### Changed Bulk Sell USDT Mismatch Behavior
- **Before**: Transaction would fail and stop if USDT amounts didn't match
- **After**: Sends warning to alert topic but continues processing with OCR detected amount
- **Tolerance**: Uses flexible tolerance (0.5 USDT or 0.5% of amount)

**All notifications now sent to alert topic:**
- ✅ Success messages (Buy, Sell, P2P Sell, Internal Transfer, Coin Transfer)
- ⚠️ Warning messages (Amount mismatches, Invalid amounts)
- ❌ Error messages (Insufficient balance, Bank not found, OCR failures)

## Version 2.3.8 - Coin Transfer Notifications

### 🐛 Bug Fixes

#### Added Missing Success Notification for Coin Transfers
- **Fixed**: Coin transfers now send success notifications to alert topic
- **Shows**: Source account, destination account, sent amount, fee, received amount, and new balances
- **Format**: HTML formatted message with clear breakdown

**What was missing:**
- Coin transfers were processing correctly
- Balance was updating correctly
- But no notification was sent to alert topic

**What's fixed:**
- Success message now sent to alert topic after every coin transfer
- Shows complete transfer details including fee breakdown
- Includes new balances for both accounts

**Example notification:**
```
✅ Coin Transfer Processed

From: San(Binance)
To: San(Swift)
Sent: 9.4919 USDT
Fee: 0.0019 USDT
Received: 9.4900 USDT

New Balances:
San(Binance): 254.8162 USDT
San(Swift): 2586.8862 USDT
```

## Version 2.3.7 - Internal Transfer Notifications

### 🐛 Bug Fixes

#### Added Missing Success Notification for Internal Transfers
- **Fixed**: Internal transfers now send success notifications to alert topic
- **Shows**: Source account, destination account, transfer amount, and new balances
- **Currency Detection**: Automatically detects if transfer is MMK, USDT, or THB
- **Format**: HTML formatted message with clear breakdown

**What was missing:**
- Internal transfers were processing correctly
- Balance was updating correctly
- But no notification was sent to alert topic

**What's fixed:**
- Success message now sent to alert topic after every internal transfer
- Shows complete transfer details for verification
- Includes new balances for both accounts

**Example notification:**
```
✅ Internal Transfer Processed

From: San(Binance)
To: MMN(Binance)
Amount: 387.5300 USDT

New Balances:
San(Binance): 1234.5678 USDT
MMN(Binance): 5678.9012 USDT
```

## Version 2.3.6 - Buy Transaction USDT Detection

### ✨ Improvements

#### USDT Amount Detection from User Receipt in Buy Transactions
- **New**: Bot now detects USDT amount from user's original receipt using OCR
- **Benefit**: Works even when message amount is 0 or invalid (e.g., when other bot has errors)
- **Applies to**: Both single and bulk buy transactions
- **Fallback**: If OCR fails, uses message amount as before

**How it works:**
1. Staff replies to user's USDT receipt with MMK receipt
2. Bot detects MMK amount from staff's receipt (as before)
3. **NEW**: Bot also detects USDT amount from user's original receipt
4. If message amount is 0 or invalid, uses OCR detected amount
5. If amounts don't match, sends warning but uses OCR amount
6. Updates receiving USDT account with detected amount

**Example scenario:**
- User sends USDT receipt showing 100.23 USDT
- Other bot sends message: "Buy 0 x 3923 = 0" (error)
- Staff replies with MMK receipt
- Bot detects: 392,850 MMK from staff receipt
- Bot detects: 100.23 USDT from user receipt (OCR)
- Bot updates: -392,850 MMK, +100.23 USDT ✅

**Warnings sent to alert topic:**
- When message amount is 0/invalid and OCR is used
- When message amount doesn't match OCR detected amount
- Shows both amounts and difference for verification

## Version 2.3.5 - Improved USDT Bank Detection

### ✨ Improvements

#### Enhanced USDT Bank Detection in Sell Transactions
- **Improved**: Bot now constructs the exact USDT bank name based on detected type and staff prefix
- **Example**: If receipt shows "Swift" and staff is "San", bot updates "San(Swift)" account
- **Bank Types**: Automatically detects Binance, Swift, or Wallet from receipt
- **Format**: Constructs bank name as `{Prefix}({BankType})` - e.g., "San(Swift)", "OKM(Wallet)", "NDT(Binance)"
- **Applies to**: Both single and bulk sell transactions

**How it works:**
1. Bot detects bank type from USDT receipt (binance/swift/wallet)
2. Gets staff prefix from replier (e.g., "San")
3. Constructs expected bank name: "San(Swift)"
4. Updates the correct USDT account in balance

**Benefits:**
- More accurate bank matching
- Clear logging shows which bank is being updated
- Better error messages when bank not found
- Success messages show detected bank type

## Version 2.3.4 - Alert Notification Fix

### 🐛 Bug Fixes

#### Fixed Missing send_status_message Function
- **Fixed**: Added missing `send_status_message()` function that was being called but not defined
- **Impact**: All transaction status messages and warnings now properly send to alert topic (ID: 1310)
- **Affected**: Buy transactions, Sell transactions, P2P sell, Internal transfers, and all mismatch warnings
- **Symptoms**: Bot was crashing when trying to send status messages due to undefined function

**What was broken:**
- Bot called `send_status_message()` for warnings and success messages
- Function was never defined, causing crashes
- Warnings about amount mismatches were not being sent to alert topic

**What's fixed:**
- Added `send_status_message()` function that sends to alert topic
- All transaction status messages now work correctly
- Mismatch warnings properly appear in alert topic

## Version 2.3.3 - BNB Transfer Support

### 🐛 Bug Fixes

#### Increased MMK Tolerance to 1000 MMK
- **Fixed**: MMK tolerance increased from 100 to 1000 MMK to handle rounding differences
- **Example**: Transaction with 99,749 MMK expected and 100,000 MMK detected will now process successfully
- **Applies to**: Buy transactions, Sell transactions, Bulk transactions, and P2P sell transactions
- **Reason**: OCR may round amounts differently than the original transaction message

### ✨ Improvements

#### Multiple MMK Receipts Support for Sell Transactions
- **New**: Sell transactions now support multiple MMK receipts in the original message
- **Example**: User sends 2 receipts of 1,000,000 MMK each = 2,000,000 MMK total
- **How it works**: Bot detects media group in original message and processes all MMK receipts
- **Applies to**: Both single and bulk sell transactions

**Before:**
- User sends 2 MMK receipts (1M + 1M = 2M)
- Bot only detects first receipt: 1M
- Transaction fails: Expected 2M, Detected 1M

**After:**
- User sends 2 MMK receipts (1M + 1M = 2M)
- Bot detects both receipts: 1M + 1M = 2M
- Transaction succeeds!

#### Internal Transfer Now Supports BNB and Crypto Transfers
- **Fixed**: Bot now correctly detects USD amounts from BNB and other crypto receipts
- **Example**: BNB receipt showing "9.49 $" + network fee "0.001868 $" = 9.491868 total
- **Improved**: OCR prompts now handle crypto transfers that display USD equivalent values
- **Enhanced**: Better error handling when AI cannot extract amounts from receipts

**How it works:**
- Bot detects if transfer is BNB/ETH/other crypto with USD value
- Extracts the USD amount shown on receipt
- Adds network fee (if shown separately in USD)
- Uses total USD amount for balance update

### ✨ Improvements

#### Coin Transfer Photo Now Optional
- **Changed**: Photo is now optional for coin transfers in Accounts Matter topic
- **Benefit**: Faster processing - bot uses amounts from text, not OCR
- **Format**: `San(binance) to OKM(swift) 10 USDT-0.47 USDT(fee) = 9.53 USDT`
- **Photo**: Can be attached for reference/proof, but amounts come from text

**Example:**
```
San(binance) to OKM(swift) 10 USDT-0.47 USDT(fee) = 9.53 USDT
```
Bot will:
- Reduce 10 USDT from San(binance)
- Add 9.53 USDT to OKM(swift)
- No OCR needed!

---

## Version 2.3.2 - Status Messages to Alert Topic

### 🎉 New Features

#### All Transaction Status Messages Sent to Alert Topic
- **New behavior**: All transaction status messages now sent to alert topic
- **Messages included**:
  - ✅ Buy transaction success
  - ✅ Sell transaction success
  - ✅ P2P sell transaction success
  - ✅ Internal transfer success
  - ❌ All error messages (already working)
  - ⚠️ All warning messages (already working)

**Message Format:**
```
✅ Buy Transaction Processed

Staff: San
MMK: -2,500,000 (San(KBZ))
USDT: +100.0000 (ACT(Wallet))
Photos: 1
```

**Benefits:**
- Centralized monitoring in alert topic
- Easy to track all transactions
- No need to search through chat history
- Clear status updates for all operations

### 🔧 Technical Changes
- Added `send_status_message()` function
- Updated buy transaction to send success message
- Updated sell transaction to send success message
- Updated P2P sell to send success message
- Updated internal transfer to send success message
- All messages use HTML formatting for clarity

---

## Version 2.3.1 - Improved USDT Tolerance

### 🔧 Bug Fixes

#### Flexible USDT Tolerance
- **Fixed**: USDT amount matching now uses flexible tolerance
- **Old behavior**: Fixed 0.03 USDT tolerance (too strict for large amounts)
- **New behavior**: 0.5 USDT or 0.5% of amount, whichever is larger
- **Example**: For 1019 USDT transaction, tolerance is 5.095 USDT (0.5%)
- **Benefit**: Handles OCR rounding differences for large transactions

**Why This Matters:**
- OCR may detect `1019.0` instead of `1019.124308`
- Difference of 0.12 USDT is tiny (0.01%) but was rejected
- New tolerance allows reasonable OCR variations
- Still strict enough to catch real errors

**Tolerance Examples:**
- 10 USDT → 0.5 USDT tolerance (5%)
- 100 USDT → 0.5 USDT tolerance (0.5%)
- 1000 USDT → 5.0 USDT tolerance (0.5%)
- 10000 USDT → 50.0 USDT tolerance (0.5%)

### 📝 Technical Details
- Updated `process_sell_transaction()` tolerance check
- Updated `process_sell_transaction_bulk()` tolerance check
- Formula: `tolerance = max(0.5, amount * 0.005)`
- Logs now show calculated tolerance for debugging

---

## Version 2.3.0 - User Management Enhancement

### 🎉 New Features

#### `/list_users` Command
- **New command**: List all user prefix mappings
- Shows user ID, username, prefix, and creation date
- Useful for managing staff access and troubleshooting
- Displays total user count
- Formatted output with clear information

**Example Output:**
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

Total Users: 2
```

**Use Cases:**
- View all mapped users at a glance
- Check user IDs for troubleshooting
- Verify prefix assignments
- Audit user access and permissions

### 🔧 Technical Changes
- Added `get_all_users()` database function
- Added `list_users_command()` handler
- Updated `/start` command help text
- Registered command handler in main application

---

## Version 2.2.0 - MMK Fee Handling in Buy and Sell Transactions

### 🎉 New Features

#### MMK Fee Support in Staff Replies
- **New feature**: Staff can now include MMK fees in their buy and sell transaction replies
- Format: `[Receipt photo] fee-3039`
- Bot automatically adds the fee to the detected MMK amount from receipt
- Example: Receipt shows 15,197,246 MMK + fee-3039 = 15,200,285 MMK total
- Works with both single photo and bulk photo (media group) transactions
- Works for both buy and sell transactions
- Case-insensitive and flexible spacing: `fee-3039`, `Fee - 3039`, `FEE-3039` all work

#### How It Works - Sell Transaction
1. Customer posts sell transaction with MMK receipt
2. Staff replies with USDT receipt and optional fee text
3. Bot OCRs customer's MMK receipt (e.g., 15,197,246 MMK)
4. Bot detects fee in staff's reply (e.g., fee-3039)
5. Bot calculates total: 15,197,246 + 3,039 = 15,200,285 MMK
6. Bot verifies total matches expected amount
7. Bot adds total MMK to staff's account

#### How It Works - Buy Transaction
1. Customer posts buy transaction with USDT receipt
2. Staff replies with MMK receipt and optional fee text
3. Bot OCRs staff's MMK receipt (e.g., 2,500,000 MMK)
4. Bot detects fee in staff's reply (e.g., fee-3000)
5. Bot calculates total: 2,500,000 + 3,000 = 2,503,000 MMK
6. Bot verifies total matches expected amount
7. Bot reduces total MMK from staff's account

#### Use Cases
- Bank transfer fees not shown in receipt
- Additional charges that need to be accounted for
- Service fees added to the transaction
- Any extra MMK costs in buy or sell transactions

### 📚 Documentation
- Updated `MMK_FEE_HANDLING.md` with buy and sell examples
- Added `test_mmk_fee.py` for testing fee detection
- Includes format examples, error handling, and logging details

### 🔧 Technical Changes
- Updated `process_buy_transaction()` to detect and add MMK fees
- Updated `process_buy_transaction_bulk()` to support fees in bulk transactions
- Updated `process_sell_transaction()` to detect and add MMK fees
- Updated `process_sell_transaction_bulk()` to support fees in bulk transactions
- Added regex pattern: `r'fee\s*-\s*([\d,]+(?:\.\d+)?)'`
- Enhanced logging to show fee breakdown in all transaction types

---

## Version 2.1.0 - Coin Transfer with Network Fee

### 🎉 New Features

#### Coin Transfer Support
- **New feature**: Coin transfer between USDT accounts with network fee handling
- Format: `Prefix(Bank) to Prefix(Bank) AMOUNT USDT-FEE USDT(fee) = RECEIVED USDT`
- Example: `San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT`
- Automatically reduces sent amount from source account
- Automatically adds received amount to destination account
- Network fee is automatically calculated (sent - received)
- Works in **Accounts Matter** topic
- Useful for blockchain transfers (TRC20, BEP20, etc.)

#### How It Works
1. Staff sends receipt photo with transfer details
2. Bot parses: source account, destination account, sent amount, fee, received amount
3. Bot reduces sent amount from source USDT account
4. Bot adds received amount to destination USDT account
5. Updated balance posted to Auto Balance topic

#### Example Use Cases
- Binance to Wallet transfers via TRC20
- Wallet to Binance transfers via BEP20
- Swift to Wallet transfers with network fees
- Any USDT transfer between platforms with blockchain fees

### 📚 Documentation
- Added `COIN_TRANSFER.md` with detailed guide
- Includes format examples and error messages
- Explains difference from regular internal transfers

---

## Version 2.0.0 - Staff-Specific Balance Tracking

### 🎉 Major Features

#### 1. Staff-Specific Balance Format
- **New balance format** with staff prefixes: `Prefix(BankName) -amount`
- Supports multiple staff members with their own accounts
- Examples: `San(KBZ)`, `TZT(Binance)`, `NDT(Wave)`, `MMN(Binance)`

#### 2. SQLite Database Integration
- **User-to-prefix mapping** stored in `bot_data.db`
- Persistent storage across bot restarts
- Automatic database creation on first run
- Schema: `user_id`, `prefix_name`, `username`, `created_at`

#### 3. `/set_user` Command
- Map Telegram users to their prefix names
- Usage: Reply to user's message with `/set_user <prefix>`
- Example: `/set_user San`, `/set_user TZT`
- Stores user_id → prefix_name mapping in database

#### 4. Staff-Specific Transaction Processing
- Bot identifies staff member from their user_id
- Retrieves their prefix from database
- Updates only their specific banks in balance
- Filters OCR results by staff prefix

#### 5. Internal Bank Transfers
- **New topic**: Accounts Matter
- Format: `Prefix(Bank) to Prefix(Bank)` + receipt photo
- Bot detects amount via OCR
- Transfers between staff accounts
- Posts updated balance to Auto Balance topic
- Example: `San(Wave Channel) to NDT (Wave)`

#### 6. USDT Tolerance Adjustment
- Increased tolerance from **0.01** to **0.03**
- Allows for small discrepancies in USDT transactions
- Better handling of crypto transaction fees

### 🔧 Technical Changes

#### Database
- Added SQLite support (`import sqlite3`)
- New functions: `init_database()`, `get_user_prefix()`, `set_user_prefix()`
- Database file: `bot_data.db`

#### Balance Parsing
- Updated `parse_balance_message()` to handle new format
- Regex pattern: `([A-Za-z\s]+?)\s*\(([^)]+)\)\s*-\s*\(?([\d,]+(?:\.\d+)?)\)?`
- Extracts: prefix, bank name, amount
- Returns: `{'mmk_banks': [...], 'usdt_banks': [...]}`

#### Balance Formatting
- Updated `format_balance_message()` to accept `usdt_banks` list
- Formats USDT with 2 decimal places
- Formats MMK as integers with commas

#### OCR Functions
- Updated `ocr_detect_mmk_bank_and_amount()` to accept `user_prefix` parameter
- Filters banks by staff prefix before OCR
- Better bank recognition for crypto exchanges (Binance)

#### Transaction Processing
- All transaction functions now check user prefix
- `process_buy_transaction()` - updates staff's MMK and USDT
- `process_sell_transaction()` - updates staff's MMK and USDT
- `process_buy_transaction_bulk()` - bulk photo support with staff prefix
- `process_sell_transaction_bulk()` - bulk photo support with staff prefix

#### Internal Transfers
- New function: `process_internal_transfer()`
- Parses transfer format with regex
- OCR detects transfer amount
- Updates both source and destination accounts
- Validates sufficient balance before transfer

#### Message Handler
- Added Accounts Matter topic handling
- Updated balance auto-loading for new format
- Logs MMK and USDT bank counts

### 📝 Configuration Changes

#### Environment Variables
- Added: `ACCOUNTS_MATTER_TOPIC_ID` - Topic for internal transfers

#### Commands
- Added: `/set_user` - Set user prefix mapping
- Updated: `/start` - Shows new features
- Updated: `/balance` - Uses new format
- Updated: `/load` - Parses new format

### 📚 Documentation

#### New Files
- `UPDATES.md` - Comprehensive feature documentation
- `CHANGELOG.md` - This file
- `setup_users.py` - Quick setup script for user mappings
- `test_balance_parsing.py` - Test script for balance parsing

#### Updated Files
- `README.md` - Updated with new features and format
- `.env.example` - Added `ACCOUNTS_MATTER_TOPIC_ID`
- `bot.py` - Complete rewrite of balance handling

### 🐛 Bug Fixes
- Fixed balance parsing for various spacing formats
- Improved regex to handle parentheses in amounts: `(15.86)`
- Better error handling for missing prefixes

### ⚠️ Breaking Changes

#### Balance Format
**Old format:**
```
MMK
Kpay P -13,205,369
KBZ -11,044,185
USDT
Wallet -5607.1401
```

**New format:**
```
San(Kpay P) -2639565
San(KBZ)-11044185
USDT
San(Swift) -81.99
```

#### Migration Required
- Update all balance messages to new format with staff prefixes
- Set up user-to-prefix mappings using `/set_user` command
- Configure `ACCOUNTS_MATTER_TOPIC_ID` in `.env`

### 🔄 Upgrade Path

1. **Backup current data**
   - Save current balance messages
   - Note user IDs and their staff names

2. **Update code**
   ```bash
   git pull
   pip install -r requirements.txt  # No new dependencies
   ```

3. **Update configuration**
   ```bash
   # Add to .env
   ACCOUNTS_MATTER_TOPIC_ID=789
   ```

4. **Convert balance format**
   - Reformat balance messages with staff prefixes
   - Post new format to Auto Balance topic

5. **Set up user mappings**
   ```bash
   # Option 1: Use setup script
   python setup_users.py
   
   # Option 2: Use Telegram command
   # Reply to each staff member's message with:
   /set_user San
   /set_user TZT
   /set_user MMN
   /set_user NDT
   ```

6. **Test**
   ```bash
   # Test balance parsing
   python test_balance_parsing.py
   
   # Test bot
   python bot.py
   ```

### 📊 Statistics

- **Lines changed**: ~500+
- **New functions**: 5
- **Updated functions**: 8
- **New files**: 4
- **Database tables**: 1

### 🙏 Credits

Developed for internal bank transfer management with multi-staff support.

---

## Version 1.0.0 - Initial Release

- Basic buy/sell transaction processing
- OCR bank detection
- Auto balance loading
- Multi-bank support
- Media group support for multiple receipts
