# Changelog

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
