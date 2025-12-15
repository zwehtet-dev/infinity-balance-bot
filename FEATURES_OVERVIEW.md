# Infinity Balance Bot - Complete Features Overview

## Bot Description

**Infinity Balance Bot** is an independent Telegram bot that manages MMK (Myanmar Kyat), USDT (Tether), and THB (Thai Baht) balances for a currency exchange business. It operates without a backend, storing all data in Telegram messages and a local SQLite database.

---

## Core Architecture

### Technology Stack
- **Language**: Python 3
- **Framework**: python-telegram-bot
- **AI/OCR**: OpenAI GPT-4o for receipt analysis
- **Database**: SQLite (bot_data.db)
- **Environment**: .env configuration

### Telegram Integration
- **Group-based**: Operates in Telegram groups with topic support
- **Topics**:
  - USDT Transfers Topic: Main transaction processing
  - Auto Balance Topic: Balance storage and updates
  - Accounts Matter Topic: Internal transfers between accounts

### Database Schema
```sql
-- User to prefix mappings
user_prefixes (user_id, prefix_name, username, created_at)

-- Bot settings
settings (key, value, updated_at)

-- MMK bank account verification
mmk_bank_accounts (id, bank_name, account_number, account_holder, created_at, updated_at)
```

---

## Balance Management

### Multi-Currency Support
1. **MMK (Myanmar Kyat)** - Primary currency
2. **USDT (Tether)** - Cryptocurrency
3. **THB (Thai Baht)** - Thai currency

### Staff-Specific Balance Tracking

**Balance Format:**
```
MMK
San(Kpay P) -2,639,565
San(CB M) -0
San(CB) -10,000
San(KBZ) -11,044,185
San(AYA M) -0
San(AYA) -0
San(Wave) -0
San(Wave M) -1,220,723
San(Wave Channel) -1,970,347
San(Yoma) -0
NDT(Wave) -2,864,900
MMM(Kpay p) -8,839,154

USDT
San(Binance) -50.0000
San(Swift) -81.9900
San(Wallet) -1104.9051
MMN(Binance) -15.8600
NDT(Binance) -6.9600
TZT(Binance) -222.6000
PPK(Binance) -0.0000
ACT(Wallet) -1104.9051
OKM(Swift) -5000.0000

THB
ACT(Bkk B) -13,223
```

**Key Features:**
- Each staff member has their own accounts (identified by prefix)
- Hyphen (-) is a separator, not a minus sign (all amounts are positive)
- Supports multiple accounts per staff member
- Supports multiple currencies

### Balance Operations
- **Auto-load**: Automatically loads balance from Auto Balance topic
- **Manual load**: `/load` command to load from any message
- **View balance**: `/balance` command to display current balance
- **Auto-update**: Posts updated balance after each transaction

---

## Transaction Types

### 1. Buy Transaction (Customer Buys USDT)

**Flow:**
1. Customer posts: "Buy 100 USDT = 2,500,000 MMK" with USDT receipt
2. Staff replies with MMK receipt photo
3. Bot processes:
   - Detects MMK bank and amount from staff's receipt
   - Reduces MMK from staff's bank
   - Adds USDT to receiving account (configurable)
   - Posts updated balance

**Features:**
- Supports multiple MMK receipts (accumulated)
- Confidence-based bank matching (50% minimum)
- Account verification (account number + holder name)
- Insufficient balance checks
- Configurable USDT receiving account

**Example:**
```
Customer: Buy 100 USDT = 2,500,000 MMK
[Customer's USDT receipt]

Staff (San): [Replies with KBZ receipt]

Bot: ✅ Buy processed!
MMK: -2,500,000 (San(KBZ))
USDT: +100.0000
```

### 2. Sell Transaction (Customer Sells USDT)

**Flow:**
1. Customer posts: "Sell 100 USDT = 2,500,000 MMK" with MMK receipt
2. Staff replies with USDT receipt photo (Binance/Swift/Wallet)
3. Bot processes:
   - Detects MMK bank and amount from customer's receipt
   - Adds MMK to staff's bank
   - Detects USDT amount + network fee from staff's receipt
   - Reduces USDT from staff's Binance/Swift/Wallet account
   - Posts updated balance

**Features:**
- Supports multiple USDT receipts (accumulated)
- Smart network fee handling:
  - **Binance**: Fee already included in amount
  - **Swift/Wallet**: Adds fee to amount
- Bank type detection (Binance/Swift/Wallet)
- Staff-specific account matching
- Insufficient balance checks

**Example:**
```
Customer: Sell 100 USDT = 2,500,000 MMK
[Customer's MMK receipt]

Staff (San): [Replies with Binance receipt: 99.99 USDT + 0.01 fee]

Bot: ✅ Sell processed!
MMK: +2,500,000 (San(KBZ))
USDT: -99.99 (San(Binance))
```

### 3. P2P Sell Transaction (Staff Sells USDT to Exchange)

**Flow:**
1. Staff posts directly: "sell 13000000/3222.6=4034.00981 fee-6.44" with MMK receipt
2. Bot processes:
   - Detects MMK bank and amount from receipt
   - Adds MMK to detected bank
   - Reduces USDT + fee from staff's account
   - Posts updated balance

**Features:**
- Direct posting (not a reply)
- Fee included in message
- Confidence-based bank matching
- Staff-specific USDT account

**Format:**
```
sell MMK/USDT=RATE fee-FEE
```

**Example:**
```
Staff (San): [CB Bank receipt]
sell 13000000/3222.6=4034.00981 fee-6.44

Bot: ✅ P2P Sell processed!
MMK: +13,000,000 (San(CB))
USDT: -3,229.04 (Amount: 3,222.6 + Fee: 6.44)
Rate: 4034.00981
```

### 4. Internal Transfer

**Flow:**
1. Staff posts in Accounts Matter topic: "San(Wave Channel) to NDT(Wave)" with receipt
2. Bot processes:
   - Detects amount from receipt
   - Reduces from source account
   - Adds to destination account
   - Posts updated balance

**Features:**
- Supports MMK, USDT, and THB transfers
- Network fee handling for Swift/Wallet to Binance
- Insufficient balance checks
- Works across different staff members

**Example:**
```
Staff: San(Wave Channel) to NDT(Wave)
[Receipt showing 1,000,000 MMK]

Bot: ✅ Internal transfer processed!
From: San(Wave Channel)
To: NDT(Wave)
Amount: 1,000,000

New balances:
San(Wave Channel): 970,347
NDT(Wave): 3,864,900
```

---

## OCR & AI Features

### 1. MMK Bank Detection

**Technology:** OpenAI GPT-4o

**Capabilities:**
- Detects transaction amount
- Identifies bank type (11+ banks supported)
- Extracts recipient details

**Supported Banks:**
1. Kpay P (RED/CORAL with "Payment Successful")
2. CB M (Blue "Account History" with CB BANK logo)
3. CB (Rainbow CB BANK logo)
4. KBZ ("INTERNAL TRANSFER - CONFIRM" with green banner)
5. AYA M ("AYA PAY" mobile app)
6. AYA ("Payment Complete" or AYA PAY logo)
7. AYA Wallet ("AYA Wallet" branding)
8. Wave (YELLOW header with Wave Money logo)
9. Wave M (Wave mobile app)
10. Wave Channel (Green "Successful" with "Cash In" and phone number)
11. Yoma ("Flexi Everyday Account")

**Critical Notes:**
- Wave, Wave M, and Wave Channel are THREE DIFFERENT accounts
- Bot uses specific indicators to distinguish them

### 2. Confidence-Based Bank Matching

**How It Works:**
1. Bot sends receipt + all registered bank info to OCR
2. OCR calculates confidence for each bank:
   - Account number match (last 4 digits): 50 points
   - Name match (case-insensitive, partial): 50 points
   - Total: 100 points maximum
3. Bot selects bank with highest confidence
4. Requires minimum 50% confidence

**Response Format:**
```json
{
    "amount": 23000,
    "banks": {
        1: 100,  // Bank ID 1: 100% confidence
        2: 0,    // Bank ID 2: 0% confidence
        3: 50    // Bank ID 3: 50% confidence
    }
}
```

**Benefits:**
- More accurate bank detection
- Handles partial account numbers
- Prevents wrong bank selection
- Shows confidence scores for debugging

### 3. USDT Receipt Analysis with Network Fee

**Technology:** OpenAI GPT-4o

**Detects:**
- Transaction amount
- Network fee (if shown)
- Bank type (Binance/Swift/Wallet)

**Bank Type Detection:**
- **Binance**: "Withdrawal Details" title, fee already included
- **Swift**: "USDT Sent" title, dark theme, fee in BNB
- **Wallet**: Various wallet interfaces (Trust Wallet, MetaMask, etc.)

**Smart Fee Handling:**
- **Binance**: Uses displayed amount as-is (fee already included)
- **Swift/Wallet**: Adds network fee to transaction amount

**Response Format:**
```json
{
    "amount": 47.84175,
    "network_fee": 0.01,
    "total_amount": 47.84175,
    "bank_type": "binance"
}
```

### 4. MMK Account Verification

**How It Works:**
1. Register bank accounts with `/set_mmk_bank`
2. Bot verifies recipient details on receipts:
   - Account number (supports partial matching with last 4 digits)
   - Holder name (case-insensitive, partial matching)
3. Only processes if verification passes

**Default Banks (Auto-registered):**
- San(CB) | 0225100900026042 | Chaw Su Thu Zar
- San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
- San(Yoma) | 007011118014339 | Daw Chaw Su Thu Zar
- San(Kpay P) | 300948464 | Chaw Su
- San(AYA) | 40038204256 | CHAW SU THU ZAR

---

## Commands

### User Management

**`/set_user`** - Map staff to prefix
```
Reply to user's message: /set_user San
Or: /set_user @username San
Or: /set_user 123456789 San
```

### Balance Management

**`/balance`** - Show current balance
```
/balance
```

**`/load`** - Load balance from message
```
Reply to balance message: /load
```

### USDT Configuration

**`/set_receiving_usdt_acc`** - Set USDT receiving account for buy transactions
```
/set_receiving_usdt_acc ACT(Wallet)
```

**`/show_receiving_usdt_acc`** - Show current receiving USDT account
```
/show_receiving_usdt_acc
```

### MMK Bank Management

**`/set_mmk_bank`** - Register MMK bank account
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
```

**`/list_mmk_bank`** - List all registered banks
```
/list_mmk_bank
```

**`/edit_mmk_bank`** - Edit existing bank account
```
/edit_mmk_bank San(KBZ) | 27251127201844999 | NEW HOLDER NAME
```

**`/remove_mmk_bank`** - Remove bank account
```
/remove_mmk_bank San(KBZ)
```

### System

**`/start`** - Show help and status
```
/start
```

**`/test`** - Test configuration
```
/test
```

---

## Advanced Features

### 1. Bulk Photo Processing

**Supports:**
- Multiple MMK receipts for buy transactions
- Multiple USDT receipts for sell transactions
- Media group detection
- Automatic accumulation

**How It Works:**
1. Staff sends multiple photos as media group
2. Bot collects all photos
3. Processes after short delay
4. Accumulates amounts
5. Verifies total matches expected amount

### 2. Multiple Receipt Support

**For Buy Transactions:**
- Staff can send multiple MMK receipts
- Bot accumulates amounts
- Processes when total matches expected amount

**For Sell Transactions:**
- Staff can send multiple USDT receipts
- Bot accumulates amounts
- Processes when total matches expected amount

### 3. Insufficient Balance Checks

**All transactions check balance before processing:**
```
❌ Insufficient balance!

San(KBZ): 1,000,000 MMK
Required: 2,500,000 MMK
Shortage: 1,500,000 MMK
```

### 4. Amount Tolerance

**USDT Tolerance:** 0.03 USDT
- Allows small discrepancies in USDT amounts
- Accounts for rounding differences

**MMK Tolerance:** 100 MMK
- Allows small discrepancies in MMK amounts

### 5. Staff-Specific Account Matching

**For Sell Transactions:**
- Bot detects bank type from receipt (Binance/Swift/Wallet)
- Matches to staff's corresponding account
- Example: Swift receipt → reduces from `San(Swift)`

**For Buy Transactions:**
- Bot detects MMK bank from receipt
- Matches to staff's corresponding bank
- Example: KBZ receipt → reduces from `San(KBZ)`

---

## Error Handling

### Transaction Errors

**Insufficient Balance:**
```
❌ Insufficient USDT balance!

San(Binance): 1,000.00 USDT
Required: 3,229.04 USDT (USDT: 3,222.6 + Fee: 6.44)
Shortage: 2,229.04 USDT
```

**Amount Mismatch:**
```
⚠️ MMK amount mismatch!
Expected: 2,500,000 MMK
Detected: 2,400,000 MMK
```

**Low Confidence:**
```
⚠️ Low confidence in bank detection!

Confidence scores:
• San(CB): 45%
• San(KBZ): 30%
• San(AYA): 10%

Best match: 45%

Please check the receipt and try again
```

### User Errors

**No Prefix Set:**
```
❌ You don't have a prefix set. Admin needs to use /set_user command.
```

**Balance Not Loaded:**
```
❌ Balance not loaded. Post balance message in auto balance topic first.
```

**No Receipt Photo:**
```
❌ No receipt photo
```

---

## Configuration

### Environment Variables (.env)

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
TARGET_GROUP_ID=your_group_id

# Optional (Topic IDs)
USDT_TRANSFERS_TOPIC_ID=123
AUTO_BALANCE_TOPIC_ID=456
ACCOUNTS_MATTER_TOPIC_ID=789
```

### Database (bot_data.db)

**Auto-created on first run**

**Tables:**
- `user_prefixes` - User to prefix mappings
- `settings` - Bot configuration
- `mmk_bank_accounts` - Registered bank accounts

**Default Data:**
- 5 default MMK bank accounts
- Default USDT receiving account: `ACT(Wallet)`

---

## Logging

### Transaction Logging

```
🔍 Received photo message - Chat: -123, Thread: 456, User: 789 (@username)
📝 Message in USDT Transfers topic 456 from user 789 (@username)
   Has photo: True, Is reply: True, Text: 'Buy 100 USDT = 2,500,000 MMK...'
   Original message: 'Buy 100 USDT = 2,500,000 MMK...'
🔄 Processing BUY transaction: 100.0 USDT = 2,500,000 MMK
Matched to San(KBZ) with 95% confidence
Reduced 2,500,000 MMK from San(KBZ)
Added 100.0000 USDT to ACT(Wallet)
```

### OCR Logging

```
USDT OCR: {'amount': 47.84175, 'network_fee': 0.01, 'total_amount': 47.84175, 'bank_type': 'binance'}
Detected USDT: 47.8418 (amount: 47.8418 + fee: 0.0100) from binance
Reduced 47.8418 USDT from San(Binance) (binance)
```

---

## Documentation Files

1. **FEATURES_OVERVIEW.md** (this file) - Complete feature list
2. **README.md** - Setup and installation guide
3. **QUICKSTART_V2.md** - Quick start guide
4. **UPDATES.md** - Changelog and update history
5. **CONFIDENCE_MATCHING.md** - Confidence-based matching system
6. **MMK_ACCOUNT_VERIFICATION.md** - Bank verification system
7. **SWIFT_WALLET_NETWORK_FEE.md** - Network fee handling
8. **P2P_SELL.md** - P2P sell feature guide
9. **THB_SUPPORT.md** - Thai Baht support
10. **RECEIVING_USDT_ACCOUNT.md** - USDT receiving account config
11. **BANK_RECOGNITION_GUIDE.md** - Bank recognition indicators
12. **DEPLOYMENT_CHECKLIST.md** - Deployment guide
13. **IMPLEMENTATION_SUMMARY.md** - Technical implementation details

---

## Use Cases

### 1. Customer Buys USDT
Customer wants to buy 100 USDT for 2,500,000 MMK.

### 2. Customer Sells USDT
Customer wants to sell 100 USDT for 2,500,000 MMK.

### 3. Staff Sells USDT to Exchange (P2P)
Staff sells 3,222.6 USDT to Binance P2P for 13,000,000 MMK with 6.44 USDT fee.

### 4. Internal Transfer Between Accounts
Staff transfers 1,000,000 MMK from Wave Channel to Wave.

### 5. Internal Transfer with Network Fee
Staff transfers 100 USDT from Swift to Binance (includes network fee).

---

## Performance & Scalability

### OCR Processing
- Average processing time: 2-3 seconds per receipt
- Confidence-based matching adds ~1-2 seconds
- Bulk photo processing is sequential (not parallel)

### Database
- SQLite for lightweight storage
- Optimized with indexes on primary keys
- No external database required

### Rate Limits
- Respects Telegram API rate limits
- Sequential processing to avoid rate limit issues
- No parallel OCR calls

---

## Security Features

1. **Group-based access control** - Only works in configured group
2. **Topic-based routing** - Transactions only in specific topics
3. **Staff verification** - Requires prefix mapping
4. **Account verification** - Verifies recipient details
5. **Confidence thresholds** - Minimum 50% confidence required
6. **Balance checks** - Prevents overdrafts

---

## Future Enhancements (Potential)

1. Multi-language support
2. Additional currencies (EUR, USD, etc.)
3. Transaction history export
4. Analytics and reporting
5. Automated reconciliation
6. Mobile app integration
7. Webhook support
8. API endpoints

---

## Support & Maintenance

### Troubleshooting
- Check logs for detailed error messages
- Verify environment variables
- Ensure database file exists
- Test with `/test` command

### Updates
- Regular updates documented in UPDATES.md
- Backward compatible changes
- Database migrations handled automatically

### Community
- GitHub repository (if applicable)
- Issue tracking
- Feature requests
- Bug reports

---

## Summary

**Infinity Balance Bot** is a comprehensive, AI-powered balance management system for currency exchange businesses. It combines:

- **Multi-currency support** (MMK, USDT, THB)
- **Staff-specific tracking** with prefix-based accounts
- **AI-powered OCR** for receipt analysis
- **Confidence-based matching** for accuracy
- **Smart network fee handling** for different platforms
- **Comprehensive error handling** and validation
- **Flexible transaction types** (Buy, Sell, P2P Sell, Internal Transfer)
- **Bulk processing** for multiple receipts
- **Account verification** for security

All without requiring a backend server, operating entirely within Telegram with local SQLite storage.
