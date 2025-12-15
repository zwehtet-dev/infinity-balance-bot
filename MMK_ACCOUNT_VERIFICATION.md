# MMK Account Verification System

## Overview

The bot now includes an MMK account verification system to improve accuracy when processing buy transactions. By registering bank account details, the bot can verify that customer payments are sent to the correct recipient.

## Why This Feature?

### Problem
Different banks show recipient information differently:
- **KBZ**: Full account number (27251127201844001)
- **CB**: Partial account (0005-xxxx-xxxx-2957)
- **Kpay P**: Partial phone (******3777)
- **Wave**: Partial phone (******3777)

### Solution
Register your bank account details once, and the bot will:
1. Verify recipient name matches
2. Verify account/phone number matches (even if partial)
3. Confirm correct bank before processing
4. Improve accuracy and prevent errors

## Command: `/set_mmk_bank`

### View Registered Accounts

```
/set_mmk_bank
```

Shows all registered MMK bank accounts.

**Response:**
```
🏦 Registered MMK Bank Accounts:

• San(KBZ)
  Account: 27251127201844001
  Holder: CHAW SU THU ZAR

• San(CB)
  Account: 02251009000260 42
  Holder: CHAW SU THU ZAR

• San(Kpay P)
  Account: 09783275630
  Holder: San Wint Htal
```

### Register New Account

**Format:**
```
/set_mmk_bank <bank_name> | <account_number> | <holder_name>
```

**Examples:**

#### KBZ Bank
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
```

#### CB Bank
```
/set_mmk_bank San(CB) | 02251009000260 42 | CHAW SU THU ZAR
```

#### Kpay P (Phone Number)
```
/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal
```

#### Wave (Phone Number)
```
/set_mmk_bank San(Wave) | 09783275630 | San Wint Htal
```

#### Wave Channel
```
/set_mmk_bank San(Wave Channel) | 09783275630 | Ei Ei Phyu
```

## How Verification Works

### Step 1: Register Account
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
```

### Step 2: Customer Sends Payment
Customer sends MMK to your registered account and posts receipt.

### Step 3: Bot Verifies Receipt
When processing buy transaction, bot checks:

#### Full Account Number (KBZ)
```
Receipt shows:
- Beneficiary Account: 27251127201844001
- Beneficiary Name: CHAW SU THU ZAR

Bot verifies:
✅ Last 4 digits match: 4001
✅ Name matches: CHAW SU THU ZAR
✅ Verified!
```

#### Partial Account Number (CB)
```
Receipt shows:
- Account: 0005-xxxx-xxxx-2957
- Name: CHAW SU THU ZAR

Bot verifies:
✅ Last 4 digits match: 2957
✅ Name matches: CHAW SU THU ZAR
✅ Verified!
```

#### Partial Phone Number (Kpay P / Wave)
```
Receipt shows:
- Transfer To: San Wint Htal (******3777)
- Amount: 399,800.00 Ks

Bot verifies:
✅ Last 4 digits match: 3777
✅ Name matches: San Wint Htal
✅ Verified!
```

### Step 4: Process or Reject

**If Verified:**
```
✅ Recipient verified!
Processing transaction...
```

**If Not Verified:**
```
⚠️ Recipient verification failed!

Expected:
- Account ending in: 4001
- Name: CHAW SU THU ZAR

Found in receipt:
- Account: 12345678901234567
- Name: WRONG NAME

Please check the receipt and try again.
```

## Database Storage

Account details are stored in SQLite:

```sql
CREATE TABLE mmk_bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name TEXT NOT NULL UNIQUE,
    account_number TEXT NOT NULL,
    account_holder TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Verification Logic

### Account Number Matching

The bot extracts the **last 4 digits** from your registered account number and checks if they appear in the receipt:

| Registered | Receipt Shows | Match? |
|------------|---------------|--------|
| 27251127201844001 | 27251127201844001 | ✅ Yes (4001) |
| 27251127201844001 | xxxx-xxxx-xxxx-4001 | ✅ Yes (4001) |
| 09783275630 | ******3777 | ❌ No (3630 ≠ 3777) |
| 09783275630 | ******3630 | ✅ Yes (3630) |

### Name Matching

The bot performs **case-insensitive partial matching**:

| Registered | Receipt Shows | Match? |
|------------|---------------|--------|
| CHAW SU THU ZAR | CHAW SU THU ZAR | ✅ Yes (exact) |
| CHAW SU THU ZAR | Chaw Su Thu Zar | ✅ Yes (case-insensitive) |
| San Wint Htal | San Wint Htal | ✅ Yes (exact) |
| San Wint Htal | SAN WINT HTAL | ✅ Yes (case-insensitive) |
| CHAW SU THU ZAR | WRONG NAME | ❌ No |

## Use Cases

### Use Case 1: Multiple Staff Members

Each staff member registers their accounts:

```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
/set_mmk_bank TZT(KBZ) | 12345678901234567 | THIN ZAR HTET
/set_mmk_bank MMN(KBZ) | 98765432109876543 | MMN NAME
```

Bot verifies each transaction against the correct staff member's account.

### Use Case 2: Multiple Banks per Staff

One staff member with multiple banks:

```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
/set_mmk_bank San(CB) | 02251009000260 42 | CHAW SU THU ZAR
/set_mmk_bank San(Wave) | 09783275630 | San Wint Htal
/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal
```

Bot verifies based on which bank the customer used.

### Use Case 3: Update Account Details

If account details change:

```
/set_mmk_bank San(KBZ) | NEW_ACCOUNT_NUMBER | NEW_NAME
```

The bot updates the existing record.

## Benefits

### 1. Improved Accuracy
- Verifies recipient before processing
- Prevents wrong account errors
- Reduces manual checking

### 2. Fraud Prevention
- Detects if payment sent to wrong account
- Alerts if name doesn't match
- Protects against mistakes

### 3. Partial Number Support
- Works with masked account numbers (xxxx)
- Works with masked phone numbers (*****)
- Verifies using last 4 digits

### 4. Multi-Bank Support
- Register multiple banks per staff
- Each bank verified independently
- Flexible configuration

## Troubleshooting

### Issue: Verification Failed

**Symptom:**
```
⚠️ Recipient verification failed!
```

**Solutions:**

1. **Check registered details:**
   ```
   /set_mmk_bank
   ```

2. **Verify account number:**
   - Make sure last 4 digits match
   - Remove spaces when registering

3. **Verify name:**
   - Check spelling
   - Case doesn't matter
   - Partial match is OK

4. **Update if needed:**
   ```
   /set_mmk_bank San(KBZ) | CORRECT_NUMBER | CORRECT_NAME
   ```

### Issue: Account Not Registered

**Symptom:**
Bot processes without verification.

**Solution:**
Register the account:
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
```

### Issue: Wrong Format

**Symptom:**
```
❌ Invalid Format!
```

**Solution:**
Use pipe (|) to separate parts:
```
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
                      ↑                   ↑
                    pipe                pipe
```

## Examples from Receipts

### Example 1: KBZ Receipt
```
Receipt shows:
- Beneficiary Account: 27251127201844001
- Beneficiary Name: CHAW SU THU ZAR
- Amount: MMK 812,600.00

Register:
/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR

Verification:
✅ Account ends in 4001 → Match!
✅ Name is CHAW SU THU ZAR → Match!
✅ Verified!
```

### Example 2: CB Receipt
```
Receipt shows:
- Account: 0005-xxxx-xxxx-2957
- Name: CHAW SU THU ZAR
- Amount: 13,000,000.00 MMK

Register:
/set_mmk_bank San(CB) | 02251009000260 42 | CHAW SU THU ZAR

Verification:
✅ Account ends in 2957 → Match!
✅ Name is CHAW SU THU ZAR → Match!
✅ Verified!
```

### Example 3: Kpay P Receipt
```
Receipt shows:
- Transfer To: San Wint Htal (******3777)
- Amount: -399,800.00 Ks

Register:
/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal

Verification:
❌ Account ends in 3630 but receipt shows 3777 → No match!
⚠️ Verification failed!
```

### Example 4: Wave Receipt
```
Receipt shows:
- Recipient: 300948464 - Chaw Su
- Amount: -100,000.00 Ks

Register:
/set_mmk_bank San(Wave) | 300948464 | Chaw Su

Verification:
✅ Account ends in 8464 → Match!
✅ Name contains "Chaw Su" → Match!
✅ Verified!
```

## Summary

✅ **Register accounts** with `/set_mmk_bank`
✅ **Automatic verification** on buy transactions
✅ **Supports partial numbers** (xxxx, *****)
✅ **Name matching** (case-insensitive)
✅ **Multi-bank support** per staff
✅ **Fraud prevention** and accuracy
✅ **Easy to update** anytime

This feature significantly improves transaction accuracy and helps prevent errors when processing customer payments!
