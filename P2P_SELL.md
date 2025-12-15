# P2P Sell Feature

## Overview

P2P Sell is a special transaction type where staff sells USDT to another currency exchange (not to a customer). Unlike regular sell transactions, P2P sell is posted directly to the USDT Transfers topic with the fee included in the message.

## Format

```
[attach MMK receipt photo]
sell 13000000/3222.6=4034.00981 fee-6.44
```

**Components:**
- `sell` - Transaction type keyword
- `13000000` - MMK amount received
- `3222.6` - USDT amount sent (without fee)
- `4034.00981` - Exchange rate
- `fee-6.44` - Transaction fee in USDT

## How It Works

1. **Staff posts directly** to USDT Transfers topic (not a reply to customer)
2. **Attaches MMK receipt** showing the MMK received
3. **Includes fee in message** using format: `fee-6.44`
4. **Bot processes**:
   - Detects MMK bank from receipt using confidence matching
   - Adds MMK to detected bank
   - Reduces USDT + fee from staff's USDT account
   - Updates balance

## Process Flow

### Step 1: Staff Posts Message

Staff posts to USDT Transfers topic:
```
[CB Bank receipt showing 13,000,000 MMK]
sell 13000000/3222.6=4034.00981 fee-6.44
```

### Step 2: Bot Detects P2P Sell

Bot recognizes P2P sell by:
- Message contains "fee-" or "fee -"
- Message has photo attached
- Message is NOT a reply (direct post)
- Message matches pattern: `sell MMK/USDT=RATE fee-FEE`

### Step 3: Bot Analyzes MMK Receipt

Bot uses confidence-based matching to:
- Detect MMK amount from receipt
- Match to registered bank account
- Verify recipient details (account number, holder name)
- Ensure confidence score ≥ 50%

### Step 4: Bot Updates Balances

**MMK Update:**
- Adds 13,000,000 MMK to detected bank (e.g., San(CB))

**USDT Update:**
- Reduces 3,229.04 USDT from staff's account (3,222.6 + 6.44 fee)
- Uses staff's prefix to find correct USDT account

### Step 5: Bot Posts New Balance

Bot sends updated balance to Auto Balance topic.

## Example Transaction

### Scenario

San sells 3,222.6 USDT to another exchange for 13,000,000 MMK with 6.44 USDT fee.

### Message Posted

```
[CB Bank receipt]
sell 13000000/3222.6=4034.00981 fee-6.44
```

### Bot Processing

```
🔍 Detected P2P sell format (fee in message)
🔄 Processing P2P SELL transaction: 3222.6 USDT + 6.44 fee = 13,000,000 MMK
📊 Analyzing MMK receipt...
✅ Matched to San(CB) with 95% confidence
💰 Added 13,000,000 MMK to San(CB)
💸 Reduced 3,229.04 USDT from San(Binance)
```

### Bot Response

```
✅ P2P Sell processed!

MMK: +13,000,000 (San(CB))
USDT: -3,229.04 (Amount: 3,222.6 + Fee: 6.44)
Rate: 4034.00981
```

### Balance Update

**Before:**
```
MMK
San(CB) -10,000,000

USDT
San(Binance) -5,000.00
```

**After:**
```
MMK
San(CB) -23,000,000

USDT
San(Binance) -1,770.96
```

## Differences from Regular Sell

| Feature | Regular Sell | P2P Sell |
|---------|-------------|----------|
| **Initiated by** | Customer posts | Staff posts directly |
| **Message type** | Staff replies to customer | Staff posts with photo |
| **Fee handling** | No fee in message | Fee included in message |
| **MMK receipt** | From customer | From exchange (to staff) |
| **USDT receipt** | From staff to customer | Not required |
| **MMK direction** | Staff sends to customer | Staff receives from exchange |
| **USDT direction** | Staff receives from customer | Staff sends to exchange |
| **Balance update** | +MMK to staff, -USDT from staff | +MMK to staff, -USDT from staff |

## Message Format Variations

The bot accepts these format variations:

```
sell 13000000/3222.6=4034.00981 fee-6.44
sell 13000000 / 3222.6 = 4034.00981 fee-6.44
sell 13,000,000/3222.6=4034.00981 fee -6.44
sell 13,000,000 / 3222.6 = 4034.00981 fee - 6.44
```

**Rules:**
- Spaces around `/` and `=` are optional
- Commas in MMK amount are optional
- Space after `fee` is optional
- Hyphen after `fee` is optional

## Bank Detection

P2P sell uses the same confidence-based bank matching as regular buy transactions:

1. **OCR analyzes receipt** for:
   - Transaction amount
   - Recipient account number (last 4 digits)
   - Recipient name

2. **Matches against registered banks**:
   - 50 points for account number match
   - 50 points for name match
   - Total: 100 points maximum

3. **Selects best match**:
   - Requires minimum 50% confidence
   - Shows warning if confidence < 50%

## Error Handling

### Insufficient USDT Balance

```
❌ Insufficient USDT balance!

San(Binance): 1,000.00 USDT
Required: 3,229.04 USDT (USDT: 3,222.6 + Fee: 6.44)
Shortage: 2,229.04 USDT
```

### Low Confidence Bank Detection

```
⚠️ Low confidence in bank detection!

Confidence scores:
• San(CB): 45%
• San(KBZ): 30%
• San(AYA): 10%

Best match: 45%

Please check the receipt and try again, or register the correct bank account with /set_mmk_bank
```

### MMK Amount Mismatch

```
⚠️ MMK amount mismatch!
Expected: 13,000,000 MMK
Detected: 12,500,000 MMK
```

### No Prefix Set

```
❌ You don't have a prefix set. Admin needs to use /set_user command.
```

### Invalid Format

If the message doesn't match the P2P sell format, the bot will skip it and log:
```
⏭️ Skipping: Not a valid Buy/Sell transaction message
```

## Requirements

1. **Staff must have prefix set**: Use `/set_user` command
2. **Staff must have USDT account**: Account name should contain staff prefix
3. **MMK bank must be registered**: Use `/set_mmk_bank` command for better accuracy
4. **Balance must be loaded**: Post balance message in Auto Balance topic first
5. **Message must be in USDT Transfers topic**: Or main chat if no topic configured

## Use Cases

### Use Case 1: Selling USDT to Binance P2P

Staff sells USDT on Binance P2P and receives MMK to CB Bank.

```
[CB Bank receipt: 13,000,000 MMK]
sell 13000000/3222.6=4034.00981 fee-6.44
```

### Use Case 2: Selling USDT to Local Exchange

Staff sells USDT to local exchange and receives MMK to KBZ Bank.

```
[KBZ Bank receipt: 5,000,000 MMK]
sell 5000000/1240.5=4030.12 fee-2.5
```

### Use Case 3: Multiple P2P Sells

Staff can post multiple P2P sells in sequence:

```
[CB receipt: 10,000,000 MMK]
sell 10000000/2480=4032.26 fee-5.0

[KBZ receipt: 8,000,000 MMK]
sell 8000000/1984=4032.26 fee-4.0
```

## Logging

The bot logs detailed information about P2P sell transactions:

```
🔍 Detected P2P sell format (fee in message)
🔄 Processing P2P SELL transaction: 3222.6 USDT + 6.44 fee = 13,000,000 MMK
P2P Sell: Matched to San(CB) with 95% confidence
Added 13,000,000 MMK to San(CB)
Reduced 3,229.04 USDT from San(Binance) (USDT: 3,222.6 + Fee: 6.44)
```

## Testing Checklist

- [ ] Test P2P sell with CB Bank receipt
- [ ] Test P2P sell with KBZ Bank receipt
- [ ] Test P2P sell with different format variations
- [ ] Test with insufficient USDT balance
- [ ] Test with low confidence bank detection
- [ ] Test with MMK amount mismatch
- [ ] Test with staff who has no prefix set
- [ ] Test with multiple P2P sells in sequence
- [ ] Verify MMK is added to correct bank
- [ ] Verify USDT + fee is deducted from staff account
- [ ] Verify balance is posted to Auto Balance topic

## Troubleshooting

### Issue: Bot doesn't detect P2P sell

**Cause:** Message format doesn't match pattern

**Solution:** Ensure message contains:
- Keyword "sell" (case-insensitive)
- Format: `MMK/USDT=RATE fee-FEE`
- Photo attached
- Posted directly (not a reply)

### Issue: Wrong bank updated

**Cause:** Low confidence in bank detection

**Solution:**
- Register bank account with `/set_mmk_bank`
- Ensure receipt shows clear account number and holder name
- Check that registered details match receipt

### Issue: USDT not deducted

**Cause:** Staff has no USDT account or wrong prefix

**Solution:**
- Verify staff has prefix set with `/set_user`
- Ensure staff has USDT account in balance
- Check account name contains staff prefix

## Technical Details

### Function: `extract_transaction_info()`

Updated to detect P2P sell format:
```python
if 'fee-' in text.lower() or 'fee -' in text.lower():
    # P2P Sell format detected
    pattern = r'sell\s+([\d,]+(?:\.\d+)?)\s*/\s*([\d.]+)\s*=\s*([\d.]+)\s+fee\s*-?\s*([\d.]+)'
    # Returns: {'type': 'p2p_sell', 'mmk': ..., 'usdt': ..., 'rate': ..., 'fee': ..., 'total_usdt': ...}
```

### Function: `process_p2p_sell_transaction()`

New function that:
1. Validates balance is loaded
2. Gets staff prefix
3. Analyzes MMK receipt with confidence matching
4. Verifies MMK amount
5. Adds MMK to detected bank
6. Reduces USDT + fee from staff account
7. Posts updated balance

### Function: `handle_message()`

Updated to detect P2P sell before checking for reply:
```python
if not is_reply and has_photo:
    if 'fee-' in current_message_text.lower():
        # Process P2P sell
```

## Migration

No migration needed. The feature works with existing balance structure and database.
