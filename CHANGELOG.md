# Changelog

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
