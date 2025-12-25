# Zero Amount Support - Version 2.3.4

## Support Transactions with 0 or Invalid Amounts

### Problem
- Another bot sometimes has errors and sends: `Buy 0 x 3923 = 0`
- Our bot skipped these messages as "not valid"
- Staff had to manually fix the message

### Solution
- Bot now accepts transactions with 0 or missing amounts
- Uses OCR to detect actual amounts from receipts
- Sends warning to alert topic showing detected amounts
- Processes successfully!

### How It Works

**Before:**
```
Message: Buy 0 x 3923 = 0
Bot: ⏭️ Skipping: Not a valid Buy/Sell transaction message
Result: ❌ Not processed
```

**After:**
```
Message: Buy 0 x 3923 = 0
Bot: ⚠️ Transaction has invalid amounts - Will use OCR
Bot: Detects from receipt: 100 USDT, 396,700 MMK
Bot: Sends warning to alert topic
Bot: Processes with OCR amounts
Result: ✅ Processed successfully!
```

### Warning Message

When message has 0 or invalid amounts, bot sends:
```
⚠️ MMK Amount Mismatch Warning

Transaction: Buy
Staff: San
Expected (from message): 0 MMK
Detected (from OCR): 396,700 MMK
Difference: 396,700 MMK

⚠️ Processing with OCR detected amount: 396,700 MMK
```

### Validation Changes

**Old Validation:**
```python
if not tx_info['type'] or not tx_info.get('usdt') or not tx_info.get('mmk'):
    skip()  # ❌ Skips when amounts are 0
```

**New Validation:**
```python
if not tx_info['type']:
    skip()  # Only skip if not Buy/Sell

# Allow 0 or None amounts
if usdt == 0 or mmk == 0 or usdt is None or mmk is None:
    logger.warning("Invalid amounts - Will use OCR")
    # Set to 0 to avoid errors
    usdt = 0 if usdt is None else usdt
    mmk = 0 if mmk is None else mmk
    # ✅ Continue processing
```

### Examples

**Example 1: Both amounts are 0**
- Message: `Buy 0 x 3923 = 0`
- OCR detects: 100 USDT, 396,700 MMK
- Warning sent: Yes (amounts don't match)
- Result: Processes with 100 USDT, 396,700 MMK ✅

**Example 2: USDT is 0**
- Message: `Sell 0 x 3967 = 2,000,000`
- OCR detects: 504 USDT, 2,000,000 MMK
- Warning sent: Yes (USDT doesn't match)
- Result: Processes with 504 USDT, 2,000,000 MMK ✅

**Example 3: MMK is 0**
- Message: `Buy 100 x 3923 = 0`
- OCR detects: 100 USDT, 392,300 MMK
- Warning sent: Yes (MMK doesn't match)
- Result: Processes with 100 USDT, 392,300 MMK ✅

**Example 4: Both amounts missing**
- Message: `Buy x = ` (malformed)
- OCR detects: 50 USDT, 196,150 MMK
- Warning sent: Yes (amounts don't match)
- Result: Processes with 50 USDT, 196,150 MMK ✅

### Benefits

1. **Handles Bot Errors**: Works even when other bot sends wrong amounts
2. **Always Uses OCR**: Trusts receipt amounts over message amounts
3. **Transparent**: Warns staff about mismatches
4. **Never Fails**: Processes all valid Buy/Sell messages

### Testing

Test with zero amounts:
1. Send message: `Buy 0 x 3923 = 0`
2. Staff replies with receipt showing 100 USDT, 392,300 MMK
3. Bot detects amounts from OCR
4. Bot sends warning to alert topic
5. Bot processes with OCR amounts
6. Transaction succeeds! ✅

### Your Case

**Message from other bot:**
```
Buy 0 x 3923 = 0
Kpay09444518188
Kaungsithu S-b68e9d1959e93a1c4c2151c4fcb9ccc...
```

**Bot behavior:**
1. Detects: Buy transaction (valid type ✅)
2. Detects: USDT = 0, MMK = 0 (invalid amounts ⚠️)
3. Logs: "Will use OCR to detect amounts"
4. Staff replies with receipt
5. OCR detects actual amounts from receipt
6. Sends warning showing detected amounts
7. Processes successfully! ✅
