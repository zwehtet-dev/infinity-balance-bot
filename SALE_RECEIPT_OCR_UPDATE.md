# Sale Receipt OCR Flow Update

## Overview

Updated the bot flow to optimize receipt checking by pre-scanning sale receipts when they arrive, rather than waiting for staff reply.

## Previous Flow (Slow)

1. Sale bot sends sale message with receipt(s)
2. Staff replies with receipt(s)
3. Bot OCR scans sale receipt(s) - **takes time**
4. Bot OCR scans staff receipt(s) - **takes time**
5. Update balance
6. Send notifications

**Problem:** Staff reply processing was slow because bot had to OCR both sale and staff receipts.

## New Flow (Optimized)

1. Sale bot sends sale message with receipt(s)
2. **Bot immediately OCR scans sale receipt(s)** ← NEW
3. **Store OCR results in database** ← NEW
4. **Send notification to alert topic with detected info** ← NEW
5. When staff replies:
   - **Fetch sale receipt OCR data from database** (no re-scan needed)
   - OCR staff receipt(s) only
   - Compare and validate
   - Update balance
   - Send notifications

**Benefits:**
- Faster staff reply processing (only 1 OCR instead of 2)
- Early warning if sale receipt has issues
- Supports multiple receipts (media groups)
- OCR data persists in database

## Transaction Flow Details

### SELL Transaction
- **Sale message:** Contains MMK receipt(s) from customer
  - Bot OCR detects: MMK amount + MMK bank
  - Stores in database for later use
- **Staff reply:** Contains USDT receipt(s) showing transfer to customer
  - Bot OCR detects: USDT amount + bank type (swift/wallet/binance)
  - Fetches stored MMK data from database
  - Updates balances: +MMK to detected bank, -USDT from staff's account

### BUY Transaction
- **Sale message:** Contains USDT receipt(s) from customer
  - Bot OCR detects: USDT amount
  - Stores in database for later use
- **Staff reply:** Contains MMK receipt(s) showing transfer to customer
  - Bot OCR detects: MMK amount + MMK bank
  - Fetches stored USDT data from database
  - Updates balances: -MMK from detected bank, +USDT to receiving account

## Bug Fixes (2024-12-29)

### 1. JSON Parsing Error in USDT OCR
- **Issue:** `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
- **Cause:** OpenAI sometimes returns non-JSON responses
- **Fix:** Added proper JSON extraction with fallback to `None`

### 2. NoneType Error for bank_type
- **Issue:** `'NoneType' object has no attribute 'capitalize'`
- **Cause:** `detected_bank_type` could be `None` if no USDT receipts were processed
- **Fix:** Added default bank type check before capitalize

### 3. Missing Success Messages
- **Issue:** `process_buy_transaction` and `process_buy_transaction_bulk` were missing success messages
- **Fix:** Added success message notifications after balance updates

## Database Changes

New table `sale_receipt_ocr`:

```sql
CREATE TABLE IF NOT EXISTS sale_receipt_ocr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    media_group_id TEXT,
    receipt_index INTEGER DEFAULT 0,
    transaction_type TEXT,
    detected_amount REAL,
    detected_bank TEXT,
    detected_usdt REAL,
    ocr_raw_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, receipt_index)
)
```

## New Functions

### Storage Functions

- `save_sale_receipt_ocr()` - Save OCR result to database
- `get_sale_receipt_ocr()` - Get OCR results by message_id
- `get_sale_receipt_ocr_by_media_group()` - Get OCR results by media_group_id
- `delete_sale_receipt_ocr()` - Delete OCR results by message_id
- `delete_sale_receipt_ocr_by_media_group()` - Delete OCR results by media_group_id
- `cleanup_old_sale_receipt_ocr()` - Clean up old OCR data (48 hours)

### Processing Functions

- `process_sale_receipt_immediate()` - Process single sale receipt immediately
- `process_sale_media_group_immediate()` - Process multiple sale receipts (media group) immediately

## Alert Notifications

When a sale message arrives, bot sends notification to alert topic:

### Normal Detection
```
📥 Sale Receipt Detected

Type: SELL
Message ID: 12345
Expected MMK: 1,000,000
Detected MMK: 1,000,000
Detected Bank: San(KBZ)
Confidence: 95%
```

### Amount Mismatch Warning
```
⚠️ Sale Receipt Detected

Type: SELL
Message ID: 12345
Expected MMK: 1,000,000
Detected MMK: 950,000
Detected Bank: San(KBZ)
Confidence: 95%

⚠️ Amount Mismatch! Difference: 50,000 MMK
```

### Low Confidence Warning
```
⚠️ Sale Receipt Detected

Type: SELL
Message ID: 12345
Expected MMK: 1,000,000
Detected MMK: 1,000,000
Detected Bank: San(KBZ)
Confidence: 45%

⚠️ Low Confidence! Bank detection may be inaccurate
```

## Transaction Types

### Sell Transaction
- Sale receipt: MMK receipt from customer
- Staff receipt: USDT receipt showing transfer to customer
- Pre-scan: Detects MMK amount and bank from sale receipt

### Buy Transaction
- Sale receipt: USDT receipt from customer
- Staff receipt: MMK receipt showing transfer to customer
- Pre-scan: Detects USDT amount from sale receipt

## Fallback Behavior

If no pre-scanned OCR data is found when staff replies:
1. Bot logs warning: "No pre-scanned OCR data found - performing OCR now"
2. Falls back to original OCR behavior
3. Transaction still processes normally

This ensures backward compatibility and handles edge cases.

## Cleanup

- OCR data is automatically deleted after successful transaction processing
- Old OCR data (>48 hours) is cleaned up periodically
- Media group photos are cleaned up after processing
