# OCR Amount Priority - Version 2.3.4

## Always Use OCR Detected Amount

### Change Summary
Bot now ALWAYS uses the OCR detected amount from receipts, not the amount from the message. If amounts don't match, bot sends warning to alert topic but continues processing.

### Key Changes

#### Before:
- Bot compared OCR amount with message amount
- If mismatch > tolerance → **STOP processing** ❌
- Transaction failed

#### After:
- Bot compares OCR amount with message amount
- If mismatch > tolerance → **Send warning** ⚠️
- **Continue processing** with OCR detected amount ✅
- Transaction succeeds

### How It Works Now

**Sell Transaction:**
1. User sends: `Sell 504.159314 x 3967 = 2,000,000 MMK`
2. Staff replies with MMK receipt
3. Bot OCR detects: 1,000,000 MMK (different from message!)
4. Bot checks: |1,000,000 - 2,000,000| = 1,000,000 > tolerance
5. Bot sends warning to alert topic:
   ```
   ⚠️ MMK Amount Mismatch Warning
   
   Transaction: Sell
   Staff: San
   Expected (from message): 2,000,000 MMK
   Detected (from OCR): 1,000,000 MMK
   Difference: 1,000,000 MMK
   
   ⚠️ Processing with OCR detected amount: 1,000,000 MMK
   ```
6. Bot continues processing with 1,000,000 MMK ✅
7. Adds 1,000,000 MMK to staff's bank
8. Reduces USDT from staff's account
9. Transaction completes successfully!

### Warning Message Format

**Sent to Alert Topic when amounts don't match:**
```
⚠️ MMK Amount Mismatch Warning

Transaction: Sell / Buy / P2P Sell
Staff: [Staff Name]
Expected (from message): [Amount from message]
Detected (from OCR): [Amount from OCR]
Difference: [Absolute difference]

⚠️ Processing with OCR detected amount: [OCR Amount]
```

### Affected Transactions

1. **Regular Sell Transaction**
   - Compares MMK from message vs OCR
   - Warns if mismatch
   - Processes with OCR amount

2. **Bulk Sell Transaction**
   - Compares MMK from message vs OCR
   - Warns if mismatch
   - Processes with OCR amount

3. **P2P Sell Transaction**
   - Compares MMK from message vs OCR
   - Warns if mismatch
   - Processes with OCR amount

### Benefits

1. **Never Fails**: Transaction always processes
2. **Transparent**: Staff sees warning if amounts don't match
3. **Accurate**: Uses actual receipt amount (OCR), not typed amount
4. **Flexible**: Handles cases where message amount is wrong

### Examples

**Example 1: Exact Match**
- Message: 2,000,000 MMK
- OCR: 2,000,000 MMK
- Result: No warning, processes normally ✅

**Example 2: Small Difference (within tolerance)**
- Message: 2,000,000 MMK
- OCR: 1,999,500 MMK
- Difference: 500 MMK (< 1,000 tolerance)
- Result: No warning, processes normally ✅

**Example 3: Large Difference (exceeds tolerance)**
- Message: 2,000,000 MMK
- OCR: 1,000,000 MMK
- Difference: 1,000,000 MMK (> tolerance)
- Result: Warning sent, processes with 1,000,000 MMK ⚠️✅

**Example 4: Very Large Difference**
- Message: 2,000,000 MMK
- OCR: 500,000 MMK
- Difference: 1,500,000 MMK (> 50% tolerance)
- Result: Warning sent, processes with 500,000 MMK ⚠️✅

### Why This Is Better

**Old Behavior:**
- Staff types wrong amount in message
- OCR detects correct amount from receipt
- Bot rejects transaction ❌
- Staff has to resend

**New Behavior:**
- Staff types wrong amount in message
- OCR detects correct amount from receipt
- Bot warns about mismatch ⚠️
- Bot uses correct OCR amount ✅
- Transaction completes!

### Testing

Test with intentional mismatch:
1. Send: `Sell 100 x 3967 = 5,000,000 MMK` (wrong amount)
2. Attach receipt showing 1,000,000 MMK (correct amount)
3. Bot detects mismatch
4. Bot sends warning to alert topic
5. Bot processes with 1,000,000 MMK (OCR amount)
6. Transaction succeeds!
