# MMK Fee Handling in Buy and Sell Transactions

## Overview
When staff replies to buy or sell transactions, they can now include an MMK fee in their message. The bot will automatically add this fee to the detected MMK amount from the receipt.

## Use Case
Sometimes the actual MMK amount includes an additional fee that's not shown in the receipt. For example:
- Receipt shows: 15,197,246 MMK
- Actual fee charged: 3,039 MMK
- Total MMK to process: 15,200,285 MMK

## Format
When replying to a transaction with a receipt, staff can include the fee in the message:

```
[Receipt Photo]
fee-3039
```

## How It Works

### Sell Transaction Example

**Customer posts:**
```
Sell 600 USDT = 15,200,285 MMK
[Customer's MMK receipt showing 15,197,246 MMK]
```

**Staff replies:**
```
[USDT receipt photo]
fee-3039
```

**Bot processes:**
1. OCR detects 15,197,246 MMK from customer's receipt
2. Bot detects "fee-3039" in staff's reply
3. Bot calculates: 15,197,246 + 3,039 = 15,200,285 MMK
4. Bot verifies: 15,200,285 matches the expected 15,200,285 ✅
5. Bot adds 15,200,285 MMK to staff's bank account
6. Bot reduces USDT from staff's account

### Buy Transaction Example

**Customer posts:**
```
Buy 100 USDT = 2,503,000 MMK
[Customer's USDT receipt]
```

**Staff replies:**
```
[MMK receipt photo showing 2,500,000 MMK]
fee-3000
```

**Bot processes:**
1. OCR detects 2,500,000 MMK from staff's receipt
2. Bot detects "fee-3000" in staff's reply
3. Bot calculates: 2,500,000 + 3,000 = 2,503,000 MMK
4. Bot verifies: 2,503,000 matches the expected 2,503,000 ✅
5. Bot reduces 2,503,000 MMK from staff's bank account
6. Bot adds USDT to receiving account

## Format Variations

The bot accepts various formats (case-insensitive, spaces optional):

```
fee-3039
fee - 3039
Fee-3039
FEE - 3039
fee-1,234
fee-100.50
```

## Important Notes

1. **Optional**: Fee is optional. If not provided, bot uses the receipt amount as-is
2. **Automatic Addition**: Fee is automatically added to the detected receipt amount
3. **Verification**: Total amount (receipt + fee) must match the expected MMK amount
4. **Works with Both**: 
   - Buy transactions (single and bulk photos)
   - Sell transactions (single and bulk photos)
5. **Case Insensitive**: "fee", "Fee", "FEE" all work
6. **Flexible Spacing**: Spaces around the hyphen are optional

## Examples

### Sell Transaction Examples

#### Example 1: Sell with Fee
```
Customer: Sell 600 USDT = 15,200,285 MMK
[Receipt: 15,197,246 MMK]

Staff: [USDT photo] fee-3039

Result: 15,197,246 + 3,039 = 15,200,285 MMK added to balance ✅
```

#### Example 2: Sell without Fee
```
Customer: Sell 100 USDT = 2,500,000 MMK
[Receipt: 2,500,000 MMK]

Staff: [USDT photo]

Result: 2,500,000 MMK added to balance ✅
```

### Buy Transaction Examples

#### Example 3: Buy with Fee
```
Customer: Buy 100 USDT = 2,503,000 MMK
[USDT receipt]

Staff: [MMK photo showing 2,500,000] fee-3000

Result: 2,500,000 + 3,000 = 2,503,000 MMK reduced from balance ✅
```

#### Example 4: Buy without Fee
```
Customer: Buy 50 USDT = 1,250,000 MMK
[USDT receipt]

Staff: [MMK photo showing 1,250,000]

Result: 1,250,000 MMK reduced from balance ✅
```

#### Example 5: Buy with Formatted Fee
```
Customer: Buy 200 USDT = 5,005,000 MMK
[USDT receipt]

Staff: [MMK photo showing 5,000,000] fee - 5,000

Result: 5,000,000 + 5,000 = 5,005,000 MMK reduced from balance ✅
```

## Error Handling

### Sell Transaction - Amount Mismatch
If the total (receipt + fee) doesn't match the expected amount:

```
Customer: Sell 600 USDT = 15,200,285 MMK
[Receipt: 15,197,246 MMK]

Staff: [USDT photo] fee-1000

Bot: ❌ MMK mismatch!
Expected: 15,200,285
Detected: 15,198,246 (Receipt: 15,197,246 + Fee: 1,000)
```

### Buy Transaction - Amount Mismatch
If the total (receipt + fee) doesn't match the expected amount:

```
Customer: Buy 100 USDT = 2,503,000 MMK
[USDT receipt]

Staff: [MMK photo: 2,500,000] fee-1000

Bot: ❌ Amount mismatch!
Expected: 2,503,000
Detected: 2,501,000 (Receipt: 2,500,000 + Fee: 1,000)
```

## Logging

The bot logs fee detection for debugging:

**Sell Transaction:**
```
INFO: Detected MMK fee in staff reply: 3,039 MMK
INFO: MMK amount adjusted: 15,197,246 + 3,039 (fee) = 15,200,285
INFO: Added 15,200,285 MMK to San(KBZ) (Receipt: 15,197,246 + Fee: 3,039)
```

**Buy Transaction:**
```
INFO: Detected MMK fee in staff reply: 3,000 MMK
INFO: Buy: Detected 2,500,000 MMK + 3,000 (fee) = 2,503,000 MMK from San(KBZ)
INFO: Reduced 2,503,000 MMK from San(KBZ) (Receipt: 2,500,000 + Fee: 3,000)
```

## Related Features

- [Buy Transactions](FEATURES_OVERVIEW.md#buy-transaction) - Main buy transaction flow
- [Sell Transactions](FEATURES_OVERVIEW.md#sell-transaction) - Main sell transaction flow
- [USDT Network Fees](SWIFT_WALLET_NETWORK_FEE.md) - USDT network fee handling
- [Multiple Receipts](FEATURES_OVERVIEW.md#multiple-receipts) - Bulk photo support

## Technical Details

### Regex Pattern
```python
fee_pattern = r'fee\s*-\s*([\d,]+(?:\.\d+)?)'
```

### Calculation
```python
detected_mmk = 15197246  # From OCR
mmk_fee = 3039           # From text
total_mmk = detected_mmk + mmk_fee  # 15200285
```

### Verification
```python
if abs(total_mmk - expected_mmk) > 100:
    # Amount mismatch error
```

## Testing

Run the test suite to verify fee detection:

```bash
python test_mmk_fee.py
```

This tests:
- Fee pattern matching with various formats
- MMK amount calculation with fees
- Edge cases (no fee, formatted numbers, etc.)
