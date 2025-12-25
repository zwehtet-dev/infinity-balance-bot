# BNB Transfer Support

## Overview
Bot now supports internal transfers using BNB and other cryptocurrencies that display USD equivalent values.

## Problem
Previously, when staff transferred BNB between accounts (e.g., San(Binance) to San(Swift)), the bot would fail because:
1. The receipt showed BNB amount instead of USDT
2. The AI would respond with "I can't extract USDT from this BNB receipt"
3. No JSON was returned, causing a parsing error

## Solution
Updated the OCR prompts in `process_internal_transfer()` to:
1. Detect crypto transfers (BNB, ETH, etc.) that show USD values
2. Extract the USD amount from the receipt
3. Add network fees (if shown separately in USD)
4. Use the total USD amount for balance updates

## Example Receipt
```
Receive BNB
+0.01067054 BNB
9.49 $

Network fee: 0.0000021 BNB (0.001868 $)
```

**Bot Detection:**
- Main amount: $9.49
- Network fee: $0.001868
- Total: $9.491868

## Usage
Staff can now send BNB transfer receipts with format:
```
San(Binance) to San(Swift)
[BNB receipt photo showing USD value]
```

Bot will:
1. Detect it's a USDT-equivalent transfer (Binance/Swift keywords)
2. Extract USD amount from BNB receipt
3. Reduce amount from San(Binance)
4. Add amount to San(Swift)

## Technical Details

### Updated Prompts
Both USDT and MMK/THB transfer prompts now include:
- Support for crypto transfers with USD values
- Instruction to add network fees to main amount
- Examples showing BNB transfers
- Clear rules for amount extraction

### Code Changes
- File: `bot.py`
- Function: `process_internal_transfer()`
- Lines: ~1368-1430
- Changes: Enhanced OCR prompts for both USDT and MMK/THB sections

## Testing
Test with:
1. BNB transfer: San(Binance) to San(Swift) with BNB receipt
2. ETH transfer: Any account with ETH receipt showing USD
3. Regular USDT transfer: Should still work as before
4. MMK transfer: Should still work as before

## Version
- Added in: v2.3.3
- Date: 2025-12-22
