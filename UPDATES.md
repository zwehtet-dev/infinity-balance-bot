# Bot Updates - Staff-Specific Balance Tracking

## New Features

### 1. Staff-Specific Balance Format
The bot now supports a new balance message format with staff prefixes:

```
San(Kpay P) -2639565
San(CB M) -0
San(KBZ)-11044185
San(AYA M )-0
San(Wave) -0
San(Wave M )-1220723
San(Wave Channel) - 1970347
NDT (Wave) -2864900
MMM (Kpay p)-8839154

USDT
San(Swift) -81.99
MMN(Binance)-(15.86)
NDT(Binance)-6.96
TZT (Binance)-(222.6)
PPK (Binance) - 0
```

### 2. User-to-Prefix Mapping (SQLite Database)
- Bot now uses SQLite database to store user-to-prefix mappings
- Database file: `bot_data.db`
- Automatically created on first run

### 3. `/set_user` Command
Admin can map staff members to their prefix names:

**Usage:**
```
Reply to a staff member's message with:
/set_user San

Or use user ID:
/set_user 123456789 San
```

**Examples:**
- `/set_user San` - Maps user to "San" prefix
- `/set_user TZT` - Maps user to "TZT" (Thin Zar Htet)
- `/set_user MMN` - Maps user to "MMN"
- `/set_user NDT` - Maps user to "NDT" (Nandar)

### 4. Staff-Specific Transaction Processing
When a staff member replies with a receipt:
1. Bot checks their user ID in the database
2. Gets their prefix name (e.g., "San", "TZT", "MMN", "NDT")
3. Updates only their banks in the balance message

**Example:**
- If staff "San" replies with KBZ receipt → Updates `San(KBZ)-11044185`
- If staff "TZT" replies with Binance receipt → Updates `TZT (Binance)-(222.6)`

### 5. Internal Bank Transfers (Accounts Matter Topic)
New topic for internal transfers between staff accounts.

**Format:**
```
San(Wave Channel) to NDT (Wave)
[attach receipt photo]
```

**How it works:**
1. Staff sends message with format: `Prefix(Bank) to Prefix(Bank)`
2. Attaches receipt photo
3. Bot detects amount from receipt using OCR
4. Reduces amount from source bank
5. Increases amount in destination bank
6. Posts updated balance to Auto Balance topic

### 6. USDT Tolerance
- USDT amount tolerance increased to **0.03** (from 0.01)
- Allows for small discrepancies in USDT transactions

## Configuration

Add to your `.env` file:
```env
ACCOUNTS_MATTER_TOPIC_ID=789  # Topic ID for internal transfers
```

## Database Schema

```sql
CREATE TABLE user_prefixes (
    user_id INTEGER PRIMARY KEY,
    prefix_name TEXT NOT NULL,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Setup Instructions

1. **Update environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add ACCOUNTS_MATTER_TOPIC_ID
   ```

2. **Install dependencies** (no new dependencies needed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the bot:**
   ```bash
   python bot.py
   ```

4. **Set up user mappings:**
   - Have each staff member send a message in the group
   - Admin replies to their message with: `/set_user <prefix_name>`
   - Example: Reply to San's message with `/set_user San`

## Usage Examples

### Setting Up Staff Members
```
Admin: (replies to San's message)
/set_user San

Bot: ✅ Set prefix 'San' for @san_username (ID: 123456789)
```

### Buy Transaction (Staff sends MMK)
```
Customer: Buy 100 USDT = 2,500,000 MMK
[photo of customer's USDT receipt]

San: (replies with KBZ receipt photo)

Bot: ✅ Buy processed!
MMK: -2,500,000 (San(KBZ))
USDT: +100.0000

(Posts updated balance to Auto Balance topic)
```

### Internal Transfer
```
In Accounts Matter topic:

Staff: San(Wave Channel) to NDT (Wave)
[photo of transfer receipt showing 1,000,000 MMK]

Bot: ✅ Internal transfer processed!
From: San(Wave Channel)
To: NDT (Wave)
Amount: 1,000,000

New balances:
San(Wave Channel): 970,347
NDT (Wave): 3,864,900

(Posts updated balance to Auto Balance topic)
```

## Migration from Old Format

If you have existing balance messages in the old format:
```
MMK
Kpay P -13,205,369
KBZ -11,044,185
...
USDT
Wallet -5607.1401
```

You need to convert them to the new format with staff prefixes:
```
San(Kpay P) -13205369
San(KBZ) -11044185
...
USDT
San(Wallet) -5607.14
```

## Troubleshooting

### Staff gets "You don't have a prefix set" error
- Admin needs to use `/set_user` command to map the staff member
- Reply to the staff member's message with `/set_user <prefix_name>`

### Balance not updating correctly
- Check that the balance message in Auto Balance topic uses the new format
- Verify staff prefix matches exactly (case-sensitive)
- Use `/balance` command to check current loaded balance

### Internal transfer not working
- Verify message is in Accounts Matter topic
- Check format: `Prefix(Bank) to Prefix(Bank)`
- Ensure both banks exist in the balance message
- Verify receipt photo is attached

## Notes

- Prefix names are case-sensitive
- Bank names must match exactly as they appear in the balance message
- USDT amounts are formatted with 2 decimal places in balance messages
- MMK amounts are integers (no decimals)
- Database file `bot_data.db` is created automatically
- All staff mappings persist across bot restarts


---

## Latest Updates (December 12, 2025)

### 7. THB (Thai Baht) Currency Support
The bot now supports THB currency in addition to MMK and USDT.

**Balance Format:**
```
MMK
San(Kpay P) -2639565
...

USDT
San(Swift) -81.99
...

THB
ACT(Bkk B) -13223
```

- THB section appears after USDT
- Formatted with 2 decimal places
- All transaction types support THB accounts
- Internal transfers work with THB accounts

### 8. Configurable USDT Receiving Account
Buy transactions now add USDT to a single configurable receiving account instead of staff-specific accounts.

**New Command: `/set_receiving_usdt_acc`**
```
/set_receiving_usdt_acc ACT(Wallet)
```

**Default:** `ACT(Wallet)`

**How it works:**
- Buy transactions: USDT added to receiving account (e.g., `ACT(Wallet)`)
- Sell transactions: USDT still reduced from staff-specific accounts
- Can be changed anytime with `/set_receiving_usdt_acc` command

### 9. MMK Bank Account Verification System
Enhanced accuracy for buy transactions with account verification.

**New Command: `/set_mmk_bank`**
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
```

**Format:** `Bank Name | Account Number | Account Holder Name`

**How it works:**
1. Register bank accounts with account numbers and holder names
2. When processing receipts, bot verifies:
   - Recipient account number (supports partial matching with last 4 digits)
   - Recipient name (case-insensitive, partial matching)
3. Only processes transaction if verification passes

**Default Banks (Auto-registered):**
- San(CB) | 0225100900026042 | Chaw Su Thu Zar
- San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
- San(Yoma) | 007011118014339 | Daw Chaw Su Thu Zar
- San(Kpay P) | 300948464 | Chaw Su
- San(AYA) | 40038204256 | CHAW SU THU ZAR

### 10. Confidence-Based Bank Matching
Advanced OCR system that checks ALL registered banks and returns confidence scores.

**How it works:**
1. Bot sends receipt + all registered bank info to OCR
2. OCR analyzes receipt and calculates confidence for each bank:
   - Account number match (last 4 digits): 50 points
   - Name match (case-insensitive, partial): 50 points
   - Total: 100 points maximum
3. Bot selects bank with highest confidence
4. Requires minimum 50% confidence to proceed

**Response Format:**
```json
{
    "amount": 23000,
    "banks": {
        1: 100,  // Bank ID 1: 100% confidence (perfect match)
        2: 0,    // Bank ID 2: 0% confidence (no match)
        3: 50    // Bank ID 3: 50% confidence (partial match)
    }
}
```

**Benefits:**
- More accurate bank detection
- Handles partial account numbers (xxxx-xxxx-xxxx-2957)
- Handles partial phone numbers (******3777)
- Prevents wrong bank selection
- Shows confidence scores for debugging

### 11. Edit and Remove MMK Bank Commands
Manage registered bank accounts easily.

**New Commands:**

**`/edit_mmk_bank`** - Edit existing bank account
```
/edit_mmk_bank San(KBZ) | 27251127201844999 | NEW HOLDER NAME
```

**`/remove_mmk_bank`** - Remove bank account
```
/remove_mmk_bank San(KBZ)
```

**Features:**
- Edit account number or holder name
- Remove banks that are no longer used
- View all registered banks with `/set_mmk_bank` (no parameters)

### 12. Enhanced Wave Channel Recognition
Improved OCR to distinguish between Wave, Wave M, and Wave Channel.

**Bank Recognition:**
- **Wave**: Yellow header with "Wave Money" logo
- **Wave M**: Wave mobile app interface
- **Wave Channel**: Green "Successful" with "Cash In" text and phone number

**Critical Notes:**
- These are THREE DIFFERENT accounts
- Bot will not confuse them anymore
- OCR prompt includes specific indicators for each

### 13. Insufficient Balance Checks
All transactions now check for sufficient balance before processing.

**Error Message Example:**
```
❌ Insufficient balance!

San(KBZ): 1,000,000 MMK
Required: 2,500,000 MMK
Shortage: 1,500,000 MMK
```

**Applied to:**
- Buy transactions (single and bulk)
- Sell transactions (single and bulk)
- Internal transfers

### 14. Balance Format Clarification
The hyphen (-) in balance messages is a **separator**, not a minus sign.

**Correct Format:**
```
San(KBZ) -11044185
```

**Not:**
```
San(KBZ) 11044185  ❌ (missing separator)
San(KBZ) - -11044185  ❌ (double negative)
```

**All amounts are positive** - the hyphen is just formatting.

## Updated Commands List

```
/start - Status and help
/balance - Show current balance
/load - Load balance from message
/set_user - Set user prefix (reply to user's message)
/set_receiving_usdt_acc - Set USDT receiving account
/set_mmk_bank - Register MMK bank account details
/edit_mmk_bank - Edit existing MMK bank account
/remove_mmk_bank - Remove MMK bank account
/test - Test connection and configuration
```

## Database Schema Updates

```sql
-- Settings table for receiving USDT account
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- MMK bank accounts table for verification
CREATE TABLE mmk_bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name TEXT NOT NULL UNIQUE,
    account_number TEXT NOT NULL,
    account_holder TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Documentation Files

- `THB_SUPPORT.md` - THB currency implementation details
- `RECEIVING_USDT_ACCOUNT.md` - USDT receiving account configuration
- `MMK_ACCOUNT_VERIFICATION.md` - Bank account verification system
- `CONFIDENCE_MATCHING.md` - Confidence-based bank matching system
- `BANK_RECOGNITION_GUIDE.md` - Bank recognition indicators for OCR

## Migration Notes

### From Previous Version
1. Database will auto-migrate with new tables
2. Default banks will be auto-registered on first run
3. Default receiving USDT account set to `ACT(Wallet)`
4. No manual migration needed

### Testing Checklist
- [ ] Test buy transaction with single photo
- [ ] Test buy transaction with multiple photos (bulk)
- [ ] Test sell transaction
- [ ] Test internal transfer
- [ ] Test THB transactions
- [ ] Test confidence-based matching
- [ ] Test insufficient balance errors
- [ ] Test `/edit_mmk_bank` command
- [ ] Test `/remove_mmk_bank` command
- [ ] Test `/set_receiving_usdt_acc` command

## Known Issues & Solutions

### Issue: Low confidence in bank detection
**Solution:** Register the bank account with `/set_mmk_bank` including correct account number and holder name

### Issue: Wrong bank selected
**Solution:** Check registered bank accounts match the actual accounts being used. Edit with `/edit_mmk_bank` if needed.

### Issue: USDT not added to correct account
**Solution:** Use `/set_receiving_usdt_acc` to set the correct receiving account

## Performance Notes

- Confidence-based matching adds ~1-2 seconds to OCR processing
- Bulk photo processing is sequential (not parallel) to avoid rate limits
- Database queries are optimized with indexes on primary keys
- All OCR calls use GPT-4o model for best accuracy


---

## Latest Updates (December 12, 2025 - Part 2)

### 15. Binance/Swift/Wallet Network Fee Support

The bot now automatically detects and correctly handles network fees for USDT transactions from Binance, Swift, or Wallet accounts.

**Key Features:**

1. **Automatic Bank Type Detection**
   - Detects if receipt is from Binance, Swift, or Wallet
   - Binance: Shows "Withdrawal Details" with network fee listed separately (fee already included in amount)
   - Swift: Shows "USDT Sent" with dark theme and network fee in BNB (need to add fee)
   - Wallet: Other wallet interfaces like Trust Wallet, MetaMask, etc. (need to add fee if shown)

2. **Smart Network Fee Handling**
   - **Binance**: Uses displayed amount as-is (fee already included by Binance)
   - **Swift/Wallet**: Adds network fee to transaction amount
   - Automatically detects network fee from receipt
   - Example (Binance): Shows 47.84175 USDT with 0.01 fee → Bot uses 47.84175 USDT
   - Example (Swift): Shows 24.813896 USDT with 0.12 fee → Bot uses 24.933896 USDT (24.813896 + 0.12)

3. **Staff-Specific Account Matching**
   - For sell transactions, matches receipt to staff's Binance, Swift, or Wallet account
   - Reduces USDT from the correct account based on receipt type
   - Example: Binance receipt → reduces from `San(Binance)`, Swift receipt → reduces from `San(Swift)`

**Balance Format:**
```
USDT
San(Binance) -50.00
San(Swift) -81.99
San(Wallet) -1104.9051
MMN(Binance) -(15.86)
NDT(Binance) -6.96
```

**Use Cases:**

**Sell Transaction (Binance):**
```
Customer: Sell 47.84 USDT = 1,200,000 MMK
Staff: [replies with Binance receipt showing 47.84175 USDT with 0.01 fee]
Bot: Detects 47.84175 USDT (fee already included), reduces from San(Binance)
```

**Sell Transaction (Swift):**
```
Customer: Sell 100 USDT = 2,500,000 MMK
Staff: [replies with Swift receipt showing 99.88 USDT + 0.12 fee]
Bot: Detects total 100.00 USDT (99.88 + 0.12), reduces from San(Swift)
```

**Internal Transfer (Swift to Binance):**
```
Message: San(Swift) to San(Binance)
Receipt: 99.88 USDT + 0.12 fee
Bot: Reduces 100.00 USDT from San(Swift), adds 99.88 to San(Binance)
```

**OCR Response Format:**

Binance:
```json
{
    "amount": 47.84175,
    "network_fee": 0.01,
    "total_amount": 47.84175,
    "bank_type": "binance"
}
```

Swift:
```json
{
    "amount": 24.813896,
    "network_fee": 0.12,
    "total_amount": 24.933896,
    "bank_type": "swift"
}
```

**Functions Updated:**
- `ocr_extract_usdt_with_fee()` - New function for USDT + fee detection with Binance support
- `ocr_extract_usdt_amount()` - Updated to use new function (backward compatible)
- `process_sell_transaction()` - Updated with Binance/Swift/Wallet bank type matching
- `process_sell_transaction_bulk()` - Updated with Binance/Swift/Wallet bank type matching
- `process_internal_transfer()` - Updated to include network fees for Swift/Wallet transfers

**Important Notes:**
- **Binance**: Amount shown already includes fee, bot uses as-is (does NOT add fee again)
- **Swift/Wallet**: Network fee is separate, bot adds it to get total
- Network fee is automatically detected (uses 0 if not shown)
- Bank type matching is case-insensitive (checks for "binance", "swift", or "wallet" in account name)
- For internal transfers from Swift/Wallet to Binance, network fee is included in deduction
- USDT tolerance remains 0.03 for amount matching

**Documentation:** See `SWIFT_WALLET_NETWORK_FEE.md` for detailed guide

**Testing Checklist:**
- [ ] Test sell transaction with Binance receipt (fee already included)
- [ ] Test sell transaction with Swift receipt (with network fee to add)
- [ ] Test sell transaction with Wallet receipt (without network fee)
- [ ] Test bulk sell transaction with multiple Binance receipts
- [ ] Test bulk sell transaction with multiple Swift receipts
- [ ] Test internal transfer from Swift to Binance (with network fee)
- [ ] Test internal transfer from Binance to Swift (without network fee)
- [ ] Test internal transfer from Wallet to Binance (with network fee)
- [ ] Verify correct account matching (Binance vs Swift vs Wallet)
- [ ] Verify Binance fee is NOT added again
- [ ] Verify Swift/Wallet fee IS added
- [ ] Test with receipts that don't show network fee


---

## Latest Updates (December 12, 2025 - Part 3)

### 16. P2P Sell Feature

Added support for P2P (peer-to-peer) sell transactions where staff sells USDT to another exchange (not to customers).

**Key Features:**

1. **Direct Posting Format**
   - Staff posts directly to USDT Transfers topic (not a reply)
   - Includes fee in the message
   - Format: `sell 13000000/3222.6=4034.00981 fee-6.44`

2. **Message Components**
   - `sell` - Transaction type
   - `13000000` - MMK amount received
   - `3222.6` - USDT amount sent (without fee)
   - `4034.00981` - Exchange rate
   - `fee-6.44` - Transaction fee in USDT

3. **Processing**
   - Detects MMK bank from receipt (confidence-based matching)
   - Adds MMK to detected bank
   - Reduces USDT + fee from staff's account
   - Posts updated balance

**Example:**

```
[CB Bank receipt showing 13,000,000 MMK]
sell 13000000/3222.6=4034.00981 fee-6.44
```

**Bot processes:**
```
✅ P2P Sell processed!

MMK: +13,000,000 (San(CB))
USDT: -3,229.04 (Amount: 3,222.6 + Fee: 6.44)
Rate: 4034.00981
```

**Balance update:**
- MMK: San(CB) increases by 13,000,000
- USDT: San(Binance) decreases by 3,229.04 (3,222.6 + 6.44)

**Differences from Regular Sell:**

| Feature | Regular Sell | P2P Sell |
|---------|-------------|----------|
| Initiated by | Customer posts | Staff posts directly |
| Message type | Staff replies | Staff posts with photo |
| Fee handling | No fee in message | Fee in message |
| MMK receipt | From customer | From exchange |
| USDT receipt | Required | Not required |

**Format Variations:**
```
sell 13000000/3222.6=4034.00981 fee-6.44
sell 13000000 / 3222.6 = 4034.00981 fee-6.44
sell 13,000,000/3222.6=4034.00981 fee -6.44
```

**Detection:**
- Bot detects P2P sell by presence of "fee-" or "fee -" in message
- Message must have photo attached
- Message must NOT be a reply (direct post)
- Pattern: `sell MMK/USDT=RATE fee-FEE`

**Bank Detection:**
- Uses same confidence-based matching as buy transactions
- Analyzes MMK receipt for account number and holder name
- Requires minimum 50% confidence
- Shows warning if confidence < 50%

**Error Handling:**
- Insufficient USDT balance check
- MMK amount mismatch detection
- Low confidence bank detection warning
- Staff prefix validation

**Functions Added:**
- `process_p2p_sell_transaction()` - New function for P2P sell processing
- `extract_transaction_info()` - Updated to detect P2P sell format
- `handle_message()` - Updated to detect and route P2P sell transactions

**Use Cases:**
- Selling USDT on Binance P2P
- Selling USDT to local exchanges
- Any USDT sale where staff receives MMK

**Requirements:**
- Staff must have prefix set (`/set_user`)
- Staff must have USDT account
- MMK bank should be registered (`/set_mmk_bank`)
- Balance must be loaded
- Message must be in USDT Transfers topic

**Documentation:** See `P2P_SELL.md` for detailed guide

**Testing Checklist:**
- [ ] Test P2P sell with CB Bank receipt
- [ ] Test P2P sell with KBZ Bank receipt
- [ ] Test with different format variations
- [ ] Test with insufficient USDT balance
- [ ] Test with low confidence bank detection
- [ ] Test with MMK amount mismatch
- [ ] Test with staff who has no prefix set
- [ ] Test multiple P2P sells in sequence
- [ ] Verify MMK added to correct bank
- [ ] Verify USDT + fee deducted from staff account
- [ ] Verify balance posted to Auto Balance topic


---

## Latest Updates (December 12, 2025 - Part 4)

### 17. New Information Commands

Added two new commands for easier information access:

**1. `/list_mmk_bank` - List All Registered MMK Banks**

Shows all registered MMK bank accounts with masked account numbers for security.

**Example Output:**
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

4. San(Kpay P)
   Account: 3009****8464
   Holder: Chaw Su

5. San(AYA)
   Account: 4003****4256
   Holder: CHAW SU THU ZAR

Commands:
• /set_mmk_bank - Register new bank
• /edit_mmk_bank - Edit existing bank
• /remove_mmk_bank - Remove bank
```

**Features:**
- Shows all registered banks with index numbers
- Masks middle digits of account numbers (shows first 4 and last 4)
- Displays full account holder names
- Includes quick links to related commands
- Shows "No banks registered" message if empty

**2. `/show_receiving_usdt_acc` - Show Receiving USDT Account**

Displays the current USDT receiving account configuration for buy transactions.

**Example Output:**
```
💰 USDT Receiving Account Configuration

Current Account: ACT(Wallet)

Purpose:
This account receives USDT when customers buy USDT from us.

How it works:
• Customer: Buy 100 USDT = 2,500,000 MMK
• Staff sends MMK to customer
• Bot adds 100 USDT to ACT(Wallet)

Note: For sell transactions, USDT is reduced from staff-specific accounts 
(Binance/Swift/Wallet) based on the receipt type.

Change Account:
Use /set_receiving_usdt_acc to change the receiving account.
Example: /set_receiving_usdt_acc ACT(Wallet)
```

**Features:**
- Shows current receiving account
- Explains the purpose and how it works
- Provides example transaction flow
- Clarifies difference between buy and sell transactions
- Includes command to change the account

**Updated `/start` Command:**

The help text is now organized into sections:
- General commands
- USDT Configuration
- MMK Bank Management
- System commands

**Benefits:**
- Easier to view registered banks without using `/set_mmk_bank`
- Quick access to USDT receiving account info
- Better user experience with organized help text
- Security: Account numbers are masked in list view

**Commands Added:**
- `/list_mmk_bank` - List all registered MMK banks
- `/show_receiving_usdt_acc` - Show current receiving USDT account

**Functions Added:**
- `list_mmk_bank_command()` - Handler for listing banks
- `show_receiving_usdt_acc_command()` - Handler for showing USDT config

**Testing Checklist:**
- [ ] Test `/list_mmk_bank` with no banks registered
- [ ] Test `/list_mmk_bank` with default banks
- [ ] Test `/list_mmk_bank` after adding custom banks
- [ ] Verify account numbers are properly masked
- [ ] Test `/show_receiving_usdt_acc` with default account
- [ ] Test `/show_receiving_usdt_acc` after changing account
- [ ] Verify `/start` command shows updated help text
- [ ] Test that commands work in group chat


---

## Latest Updates (December 12, 2025 - Part 5)

### 18. Updated Number Formatting

Standardized number formatting across all currencies for better precision and consistency.

**Changes:**

1. **USDT Formatting: 4 Decimal Places**
   - Changed from 2 decimals to 4 decimals
   - Example: `1104.9051` instead of `1104.91`
   - Applies to all USDT displays (balance, transactions, logs)

2. **MMK Formatting: No Decimals (Integer)**
   - Already using integer format with commas
   - Example: `11,044,185` (no change)
   - Consistent across all MMK displays

3. **THB Formatting: No Decimals (Integer)**
   - Changed from 2 decimals to integer format
   - Example: `13,223` instead of `13,223.00`
   - Matches MMK formatting style

**Balance Format Examples:**

**Before:**
```
USDT
San(Swift) -81.99
ACT(Wallet) -1104.91

THB
ACT(Bkk B) -13,223.00
```

**After:**
```
USDT
San(Swift) -81.9900
ACT(Wallet) -1104.9051

THB
ACT(Bkk B) -13,223
```

**Transaction Messages:**

**Buy Transaction:**
```
✅ Buy processed!

MMK: -2,500,000 (San(KBZ))
USDT: +100.0000
```

**Sell Transaction:**
```
✅ Sell processed!

MMK: +2,500,000 (San(KBZ))
USDT: -99.9900
```

**P2P Sell Transaction:**
```
✅ P2P Sell processed!

MMK: +13,000,000 (San(CB))
USDT: -3,229.0400 (Amount: 3,222.6000 + Fee: 6.4400)
Rate: 4034.00981
```

**Benefits:**

1. **Better USDT Precision**
   - Accurately displays small amounts
   - Matches blockchain precision
   - Prevents rounding errors

2. **Cleaner THB Display**
   - No unnecessary decimals
   - Consistent with MMK format
   - Easier to read

3. **Consistent Formatting**
   - Cryptocurrencies: 4 decimals (USDT)
   - Fiat currencies: No decimals (MMK, THB)
   - Clear visual distinction

**Files Updated:**
- `bot.py` - format_balance_message() function
- `test_balance_parsing.py` - format_balance_message() function

**Backward Compatibility:**
- Existing balances will be reformatted automatically
- No data migration needed
- Parser handles both old and new formats

**Testing Checklist:**
- [ ] Verify USDT shows 4 decimal places in balance
- [ ] Verify MMK shows no decimals with commas
- [ ] Verify THB shows no decimals with commas
- [ ] Test buy transaction message formatting
- [ ] Test sell transaction message formatting
- [ ] Test P2P sell transaction message formatting
- [ ] Test internal transfer message formatting
- [ ] Verify balance parsing still works with old format
- [ ] Verify balance display in /balance command
