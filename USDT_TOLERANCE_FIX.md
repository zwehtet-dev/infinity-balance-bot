# USDT Tolerance Fix - Version 2.3.3

## Fixed: USDT Tolerance Too Strict

### Problem
- Bot detected: 504.3034 USDT
- Expected: 504.1593 USDT
- Difference: 0.144 USDT
- Old tolerance: 0.03 USDT (too strict!)
- Result: Bot was waiting for more photos ❌

### Solution
- Updated USDT tolerance to match other sell functions
- New tolerance: `max(0.5, amount * 0.005)` - 0.5 USDT or 0.5% of amount
- For 504.16 USDT: tolerance = 2.52 USDT
- Difference of 0.144 USDT is well within tolerance ✅

### Your Case
- Expected: 504.1593 USDT
- Detected: 504.3034 USDT
- Difference: 0.144 USDT
- Tolerance: 2.52 USDT (0.5% of 504.16)
- Result: ✅ Transaction will process immediately!

### Code Change
File: `bot.py`
Line: ~1057
Function: `process_sell_transaction()`

**Before:**
```python
if abs(total_detected_usdt - tx_info['usdt']) > 0.03:
```

**After:**
```python
tolerance = max(0.5, tx_info['usdt'] * 0.005)
if abs(total_detected_usdt - tx_info['usdt']) > tolerance:
```

### Why This Happened
- This was an old hardcoded tolerance from early development
- Other sell functions were already updated to use flexible tolerance
- This one was missed during the previous update

### Testing
Try your transaction again:
1. Send sell message: `Sell 504.159314 x 3967 = 2,000,000 MMK`
2. Staff replies with USDT receipt showing 504.3034 USDT
3. Difference: 0.144 USDT
4. Tolerance: 2.52 USDT
5. Result: ✅ Processes immediately (no waiting)!
