# Bank Recognition Guide

## MMK Banks

The bot can recognize the following MMK banks from receipt photos:

### 1. Kpay P (KBZ Pay Partner)
**Visual Indicators:**
- RED/CORAL color scheme
- "Payment Successful" text
- KBZ Pay branding

### 2. CB M (CB Bank Mobile)
**Visual Indicators:**
- Blue "Account History" interface
- "CB BANK" logo
- Mobile app interface

### 3. CB (CB Bank Regular)
**Visual Indicators:**
- Rainbow "CB BANK" logo
- Regular banking interface

### 4. KBZ (KBZ Bank)
**Visual Indicators:**
- "INTERNAL TRANSFER - CONFIRM" text
- Green banner
- KBZ branding

### 5. AYA M (AYA Pay Mobile)
**Visual Indicators:**
- "AYA PAY" mobile app interface
- Mobile-specific design

### 6. AYA (AYA Bank Regular)
**Visual Indicators:**
- "Payment Complete" text
- "AYA PAY" logo
- Regular banking interface

### 7. AYA Wallet
**Visual Indicators:**
- "AYA Wallet" branding
- Wallet-specific interface

### 8. Wave (Wave Money Regular)
**Visual Indicators:**
- YELLOW header
- "Wave Money" logo
- Regular Wave interface

### 9. Wave M (Wave Money Mobile)
**Visual Indicators:**
- Wave mobile app interface
- "Wave Money" branding
- Mobile-specific design

### 10. Wave Channel (Wave Agent/Channel) ⭐
**Visual Indicators:**
- Green "Successful" checkmark
- "Cash In" text
- Recipient phone number displayed
- Agent/Channel transaction interface

**Example from receipt:**
```
✓ Successful
Cash In
295,600 Ks
to
09783275630
```

**IMPORTANT:** Wave Channel is DIFFERENT from Wave and Wave M!

### 11. Yoma (Yoma Bank)
**Visual Indicators:**
- "Flexi Everyday Account" text
- Yoma Bank branding

## Critical Distinctions

### Wave vs Wave M vs Wave Channel

These are **THREE DIFFERENT accounts** - do not confuse them:

| Account | Visual Indicator | Use Case |
|---------|-----------------|----------|
| **Wave** | Yellow header, Wave Money logo | Regular Wave account |
| **Wave M** | Wave mobile app interface | Mobile Wave account |
| **Wave Channel** | Green checkmark, "Cash In", phone number | Agent/Channel transactions |

### How to Identify Wave Channel

✅ **Wave Channel Receipt Shows:**
- Green checkmark (✓)
- "Successful" text
- "Cash In" label
- Large amount in blue (e.g., 295,600 Ks)
- "to" text
- Recipient phone number (e.g., 09783275630)
- Transaction details (Name, Phone Number, Total Amount, Commission)
- "I have taken the money" button at bottom

❌ **NOT Wave Channel if:**
- Yellow header → This is "Wave"
- Wave mobile app → This is "Wave M"
- No "Cash In" text → Check other indicators

## OCR Prompt Updates

The bot now includes specific instructions to distinguish Wave Channel:

```
CRITICAL NOTES:
1. Return amount as positive number, ignore any minus signs
2. If you see "Cash In" with green checkmark and phone number → This is "Wave Channel"
3. Match the bank name EXACTLY as shown in the available banks list
4. Wave, Wave M, and Wave Channel are THREE DIFFERENT accounts
```

## Testing

To test Wave Channel recognition:

1. Post a balance message with Wave Channel:
   ```
   San(Wave Channel) -1970347
   San(Wave) -0
   San(Wave M) -1220723
   ```

2. Process a transaction with Wave Channel receipt
3. Bot should correctly identify it as "Wave Channel"

## Troubleshooting

### Issue: Bot confuses Wave Channel with Wave

**Symptoms:**
- Receipt shows "Cash In" but bot detects as "Wave"
- Wrong account updated

**Solution:**
- The updated OCR prompt now specifically looks for "Cash In" text
- Restart bot to load new prompt
- Try processing again

### Issue: Wave Channel not in balance

**Symptoms:**
```
❌ Bank not found: San(Wave Channel)
```

**Solution:**
Add Wave Channel to your balance message:
```
San(Wave Channel) -1970347
```

## Summary

✅ **11 MMK banks supported**
✅ **Wave Channel specifically recognized** by "Cash In" + green checkmark
✅ **Clear distinction** between Wave, Wave M, and Wave Channel
✅ **Updated OCR prompt** with specific instructions
✅ **Ready for production use**

The bot can now correctly identify Wave Channel receipts and distinguish them from regular Wave and Wave M accounts.
