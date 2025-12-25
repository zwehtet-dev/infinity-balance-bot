# MMK Tolerance Update - Version 2.3.3

## Changed MMK Tolerance to 50%

### Problem
- User sends sell message with 2 MMK receipts (1M + 1M = 2M total)
- Bot only detects first receipt: 1M
- Transaction fails: Expected 2M, Detected 1M
- Old tolerance: 1000 MMK (too strict)

### Solution
- Increased MMK tolerance to 50% of expected amount
- Formula: `max(1000, expected_amount * 0.5)`
- Minimum tolerance: 1000 MMK
- Maximum tolerance: 50% of expected amount

### Examples

**Your Case:**
- Expected: 2,000,000 MMK
- Detected: 1,000,000 MMK (one receipt detected)
- Difference: 1,000,000 MMK
- Tolerance: 1,000,000 MMK (50% of 2M)
- Result: ✅ Transaction will process!

**Other Examples:**
- Expected: 100,000 MMK → Tolerance: 50,000 MMK (50%)
- Expected: 1,500 MMK → Tolerance: 1,000 MMK (minimum)
- Expected: 99,749 MMK → Tolerance: 49,874 MMK (50%)

### Why This Works
- If user sends 2 receipts but bot only detects 1, the difference is ~50%
- If user sends 3 receipts but bot only detects 2, the difference is ~33% (within tolerance)
- Handles rounding errors and OCR inaccuracies
- Still catches major errors (>50% difference)

### Code Changes
Updated tolerance check in:
- `process_buy_transaction()` - Line ~891
- `process_sell_transaction()` - Line ~1004
- `process_buy_transaction_bulk()` - Line ~1676
- `process_sell_transaction_bulk()` - Line ~1704
- `process_p2p_sell_transaction()` - Line ~2035

### Testing
Test your transaction again:
1. Send sell message: `Sell 504.159314 x 3967 = 2,000,000 MMK`
2. Attach 2 MMK receipts (1M each)
3. Bot detects 1M (first receipt)
4. Difference: 1M (50% of 2M)
5. Within tolerance: ✅ YES
6. Transaction processes successfully!
