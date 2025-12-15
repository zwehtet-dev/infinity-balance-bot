# Confidence-Based Bank Matching System

## Overview

The bot now uses an advanced confidence-based matching system to identify which bank account a customer payment was sent to. Instead of guessing, the OCR analyzes the receipt against ALL registered bank accounts and returns confidence scores for each.

## How It Works

### Step 1: Register Bank Accounts

Register all your MMK bank accounts:

```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
/set_mmk_bank San(CB) | 02251009000260 42 | CHAW SU THU ZAR
/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal
/set_mmk_bank San(Wave) | 09783275630 | Ei Ei Phyu
```

### Step 2: Customer Sends Payment

Customer sends MMK and posts receipt.

### Step 3: OCR Analyzes Receipt

Bot sends receipt to OCR with ALL registered banks:

```
REGISTERED BANK ACCOUNTS:
Bank ID 1: San(KBZ)
  Account ends in: 4001
  Holder: CHAW SU THU ZAR

Bank ID 2: San(CB)
  Account ends in: 6042
  Holder: CHAW SU THU ZAR

Bank ID 3: San(Kpay P)
  Account ends in: 3630
  Holder: San Wint Htal

Bank ID 4: San(Wave)
  Account ends in: 3630
  Holder: Ei Ei Phyu
```

### Step 4: OCR Returns Confidence Scores

OCR analyzes the receipt and returns:

```json
{
    "amount": 812600,
    "banks": {
        "1": 100,  // San(KBZ) - Perfect match!
        "2": 50,   // San(CB) - Name matches, account doesn't
        "3": 0,    // San(Kpay P) - No match
        "4": 0     // San(Wave) - No match
    }
}
```

### Step 5: Bot Selects Best Match

Bot selects the bank with highest confidence:
- **Bank ID 1 (San(KBZ))**: 100% confidence
- **Amount**: 812,600 MMK

### Step 6: Process Transaction

Bot updates the correct bank account.

## Confidence Scoring

### How Confidence is Calculated

**Total: 100 points**
- **Account Match (50 points)**: Last 4 digits of account/phone match
- **Name Match (50 points)**: Recipient name matches (case-insensitive)

### Examples

#### Example 1: Perfect Match (100%)

**Receipt shows:**
- Account: 27251127201844001
- Name: CHAW SU THU ZAR

**Registered:**
- San(KBZ): 27251127201844001 | CHAW SU THU ZAR

**Score:**
- Account match (4001 = 4001): ✅ 50 points
- Name match (CHAW SU THU ZAR): ✅ 50 points
- **Total: 100%**

#### Example 2: Partial Account Match (100%)

**Receipt shows:**
- Account: 0005-xxxx-xxxx-2957
- Name: CHAW SU THU ZAR

**Registered:**
- San(CB): 02251009000260 42 | CHAW SU THU ZAR

**Score:**
- Account match (2957 visible): ✅ 50 points
- Name match: ✅ 50 points
- **Total: 100%**

#### Example 3: Name Only Match (50%)

**Receipt shows:**
- Account: 99999999999999999
- Name: CHAW SU THU ZAR

**Registered:**
- San(KBZ): 27251127201844001 | CHAW SU THU ZAR

**Score:**
- Account match (4001 ≠ 9999): ❌ 0 points
- Name match: ✅ 50 points
- **Total: 50%**

#### Example 4: No Match (0%)

**Receipt shows:**
- Account: 99999999999999999
- Name: WRONG NAME

**Registered:**
- San(KBZ): 27251127201844001 | CHAW SU THU ZAR

**Score:**
- Account match: ❌ 0 points
- Name match: ❌ 0 points
- **Total: 0%**

## Confidence Thresholds

### High Confidence (≥ 50%)

Bot processes the transaction automatically.

**Example:**
```
✅ Matched to San(KBZ) with 100% confidence
Processing transaction...
```

### Low Confidence (< 50%)

Bot shows warning and asks for verification.

**Example:**
```
⚠️ Low confidence in bank detection!

Confidence scores:
• San(KBZ): 0%
• San(CB): 0%
• San(Kpay P): 25%
• San(Wave): 25%

Best match: 25%

Please check the receipt and try again, or register the correct bank account with /set_mmk_bank
```

## Real-World Examples

### Example 1: KBZ Receipt

**Receipt:**
```
Beneficiary Account: 27251127201844001
Beneficiary Name: CHAW SU THU ZAR
Amount: MMK 812,600.00
```

**Registered Banks:**
1. San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
2. San(CB) | 02251009000260 42 | CHAW SU THU ZAR
3. San(Wave) | 09783275630 | Ei Ei Phyu

**OCR Result:**
```json
{
    "amount": 812600,
    "banks": {
        "1": 100,  // Perfect match!
        "2": 50,   // Name matches only
        "3": 0     // No match
    }
}
```

**Bot Action:**
✅ Processes with San(KBZ) - 100% confidence

### Example 2: CB Receipt (Partial Account)

**Receipt:**
```
Account: 0005-xxxx-xxxx-2957
Name: CHAW SU THU ZAR
Amount: 13,000,000.00 MMK
```

**Registered Banks:**
1. San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
2. San(CB) | 02251009000260 42 | CHAW SU THU ZAR (ends in 6042, but receipt shows 2957)

**OCR Result:**
```json
{
    "amount": 13000000,
    "banks": {
        "1": 50,   // Name matches only
        "2": 50    // Name matches only (account doesn't match 2957 ≠ 6042)
    }
}
```

**Bot Action:**
⚠️ Shows warning - Need to register correct CB account ending in 2957

### Example 3: Kpay P Receipt (Partial Phone)

**Receipt:**
```
Transfer To: San Wint Htal (******3777)
Amount: -399,800.00 Ks
```

**Registered Banks:**
1. San(Kpay P) | 09783275630 | San Wint Htal (ends in 3630, not 3777)
2. San(Kpay P) | 09783273777 | San Wint Htal (ends in 3777)

**OCR Result:**
```json
{
    "amount": 399800,
    "banks": {
        "1": 50,   // Name matches, account doesn't
        "2": 100   // Perfect match!
    }
}
```

**Bot Action:**
✅ Processes with Bank ID 2 - 100% confidence

## Benefits

### 1. Automatic Bank Selection
- No manual selection needed
- Bot chooses best match automatically
- Reduces human error

### 2. Multi-Account Support
- Register multiple accounts per bank type
- Bot distinguishes between them
- Example: Multiple Kpay P accounts with different phone numbers

### 3. Confidence Transparency
- See why bot chose a specific bank
- Understand matching logic
- Debug issues easily

### 4. Error Prevention
- Low confidence triggers warning
- Prevents wrong account updates
- Asks for verification when unsure

### 5. Flexible Matching
- Works with full account numbers
- Works with partial (xxxx, *****)
- Works with different name formats

## Troubleshooting

### Issue: Low Confidence Warning

**Symptom:**
```
⚠️ Low confidence in bank detection!
Best match: 25%
```

**Causes:**
1. Bank account not registered
2. Wrong account number registered
3. Wrong name registered
4. Receipt unclear/damaged

**Solutions:**

1. **Check registered accounts:**
   ```
   /set_mmk_bank
   ```

2. **Register missing account:**
   ```
   /set_mmk_bank San(KBZ) | CORRECT_NUMBER | CORRECT_NAME
   ```

3. **Update existing account:**
   ```
   /set_mmk_bank San(KBZ) | NEW_NUMBER | NEW_NAME
   ```

4. **Retake receipt photo** if unclear

### Issue: Wrong Bank Selected

**Symptom:**
Bot updates wrong bank account.

**Cause:**
Multiple banks have same confidence score.

**Solution:**
Register more specific account details:
```
/set_mmk_bank San(KBZ) | FULL_ACCOUNT_NUMBER | EXACT_NAME
```

### Issue: All Banks Show 0%

**Symptom:**
```
Confidence scores:
• San(KBZ): 0%
• San(CB): 0%
• San(Wave): 0%
```

**Causes:**
1. Receipt doesn't match any registered account
2. Customer sent to unregistered account
3. OCR couldn't read receipt

**Solutions:**
1. Check if customer sent to correct account
2. Register the account they actually used
3. Retake clearer receipt photo

## Advanced Usage

### Multiple Accounts Same Bank

Register multiple accounts for the same bank:

```
/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal
/set_mmk_bank San(Kpay P 2) | 09783273777 | San Wint Htal
/set_mmk_bank San(Kpay P 3) | 09123456789 | San Wint Htal
```

Bot will match to the correct one based on phone number in receipt.

### Different Names Same Bank

Register accounts with different holder names:

```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
/set_mmk_bank San(KBZ 2) | 12345678901234567 | SAN WINT HTAL
```

Bot will match based on both account and name.

## Summary

✅ **Confidence-based matching** - Analyzes all registered banks
✅ **Automatic selection** - Chooses best match
✅ **Transparent scoring** - See why bank was chosen
✅ **Error prevention** - Warns on low confidence
✅ **Multi-account support** - Handles multiple accounts per bank
✅ **Flexible matching** - Works with partial numbers
✅ **Improved accuracy** - Reduces wrong bank errors

This system significantly improves transaction accuracy by intelligently matching receipts to the correct bank account!
