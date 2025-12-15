# THB (Thai Baht) Support

## Overview

The bot now supports THB (Thai Baht) in addition to MMK and USDT. THB banks can be tracked separately for each staff member.

## Balance Format

### With THB Section

```
MMK
San(Kpay P) 2639565
San(KBZ) 11044185
NDT(Wave) 2864900

USDT
San(Swift) 81.99
MMN(Binance) 15.86

THB
ACT(Bkk B) 13223.00
ACT(SCB) 25000.00
```

### Single-Line Format (Also Supported)

```
MMKSan(Kpay P) -2639565San(KBZ)-11044185USDTSan(Swift) -81.99THBACT(Bkk B) -13223ACT(SCB) -25000
```

## Features

### 1. Balance Parsing
- Automatically detects THB section after USDT
- Parses THB banks with staff prefixes
- Handles both multi-line and single-line formats

### 2. Balance Formatting
- THB amounts displayed with 2 decimal places
- Positive values (no minus sign)
- Separate THB section in output

### 3. Internal Transfers
- Supports transfers between THB accounts
- Supports transfers between MMK, USDT, and THB accounts
- Example: `ACT(Bkk B) to ACT(SCB)`

### 4. Transaction Processing
- All transaction types support THB banks
- Staff-specific THB tracking
- OCR detection for THB receipts

## Usage Examples

### Example 1: Balance with THB

Post this balance message to Auto Balance topic:

```
San(Kpay P) 2639565
San(KBZ) 11044185
NDT(Wave) 2864900

USDT
San(Swift) 81.99
MMN(Binance) 15.86

THB
ACT(Bkk B) 13223.00
ACT(SCB) 25000.00
```

Bot will parse:
- 3 MMK banks
- 2 USDT banks
- 2 THB banks

### Example 2: Internal Transfer (THB)

In Accounts Matter topic:

```
ACT(Bkk B) to ACT(SCB)
[attach receipt photo showing 5000 THB]
```

Bot will:
1. Detect transfer from ACT(Bkk B) to ACT(SCB)
2. OCR amount: 5000 THB
3. Reduce ACT(Bkk B): 13223 - 5000 = 8223
4. Increase ACT(SCB): 25000 + 5000 = 30000
5. Post updated balance

### Example 3: Cross-Currency Transfer

```
San(KBZ) to ACT(Bkk B)
[attach receipt]
```

Bot will handle transfers between different currency accounts (MMK to THB, USDT to THB, etc.)

## Technical Details

### Parsing Logic

1. **Find Currency Sections**
   - Locate "USDT" marker
   - Locate "THB" marker (if exists)
   - Split text into MMK, USDT, and THB sections

2. **Parse Each Section**
   - Use regex pattern: `([A-Za-z\s]+?)\s*\(([^)]+)\)\s*-\s*\(?([\d,]+(?:\.\d+)?)\)?`
   - Extract: prefix, bank name, amount
   - Store in respective arrays

3. **Return Structure**
   ```python
   {
       'mmk_banks': [...],
       'usdt_banks': [...],
       'thb_banks': [...]  # Empty array if no THB section
   }
   ```

### Formatting Logic

1. **MMK Section**
   - Format as integer with commas
   - No decimal places

2. **USDT Section**
   - Format with 2 decimal places
   - Always include decimals

3. **THB Section** (if exists)
   - Format with 2 decimal places
   - Always include decimals
   - Only shown if THB banks exist

### Internal Transfer Logic

```python
# Check all currency banks
all_banks = balances['mmk_banks'] + balances['usdt_banks'] + balances.get('thb_banks', [])

# Find source and destination
for bank in all_banks:
    if bank['bank_name'] == from_full_name:
        from_bank_obj = bank
    if bank['bank_name'] == to_full_name:
        to_bank_obj = bank

# Transfer amount
from_bank_obj['amount'] -= amount
to_bank_obj['amount'] += amount
```

## Testing

### Test Balance Parsing

```bash
python test_balance_parsing.py
```

Expected output:
```
✅ Parsed 13 MMK banks, 7 USDT banks, 2 THB banks
```

### Test Bot

```bash
python bot.py
```

Post balance with THB section to Auto Balance topic.

Expected log:
```
✅ Balance loaded: 13 MMK banks, 7 USDT banks, 2 THB banks
```

## Migration

### Adding THB to Existing Balance

**Old balance (without THB):**
```
San(Kpay P) 2639565
San(KBZ) 11044185

USDT
San(Swift) 81.99
```

**New balance (with THB):**
```
San(Kpay P) 2639565
San(KBZ) 11044185

USDT
San(Swift) 81.99

THB
ACT(Bkk B) 13223.00
ACT(SCB) 25000.00
```

Simply add the THB section after USDT. The bot will automatically detect and parse it.

## Backward Compatibility

- ✅ Balances without THB section still work
- ✅ Old balance messages are compatible
- ✅ THB section is optional
- ✅ All existing features continue to work

## Commands

All commands now support THB:

### `/balance`
Shows MMK, USDT, and THB banks

### `/load`
Loads balance including THB banks

Output:
```
✅ Loaded!

MMK Banks: 13
USDT Banks: 7
THB Banks: 2
```

## Supported Thai Banks

Common Thai banks that can be tracked:

- **Bkk B** - Bangkok Bank
- **SCB** - Siam Commercial Bank
- **KBank** - Kasikorn Bank
- **TMB** - TMB Bank
- **BBL** - Bangkok Bank
- **KBANK** - Kasikorn Bank
- **KTB** - Krung Thai Bank
- **BAY** - Bank of Ayudhya
- **GSB** - Government Savings Bank
- **CIMB** - CIMB Thai Bank

## Notes

1. **Currency Format**
   - MMK: Integer (no decimals)
   - USDT: 2 decimals
   - THB: 2 decimals

2. **Amount Display**
   - All amounts shown as positive
   - No minus signs in output

3. **OCR Detection**
   - OCR automatically detects amounts as positive
   - Ignores minus signs in receipts

4. **Internal Transfers**
   - Works between any currency accounts
   - Validates sufficient balance
   - Updates both source and destination

## Summary

✅ THB support fully implemented
✅ Backward compatible
✅ Tested and working
✅ Supports all existing features
✅ Ready for production use

The bot now supports three currencies:
- **MMK** (Myanmar Kyat) - Integer format
- **USDT** (Tether) - 2 decimal places
- **THB** (Thai Baht) - 2 decimal places
