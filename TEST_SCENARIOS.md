# Quick Test Scenarios

Quick reference for testing common bot scenarios with example data.

---

## Setup Test Data

### Test Users
- **User 1**: San (ID: 123456789)
- **User 2**: TZT (ID: 987654321)

### Test Balance
```
San(KBZ) -10000000
San(Wave) -5000000
TZT(Wave) -3000000

USDT
San(Binance) -100.0000
San(Swift) -50.0000
TZT(Binance) -75.0000
ACT(Wallet) -200.0000

THB
ACT(Bkk B) -50000
```

---

## Scenario 1: Buy Transaction (No Fee)

**Customer Message:**
```
Buy 10 USDT = 250,000 MMK
[USDT receipt photo]
```

**Staff (San) Reply:**
```
[KBZ receipt photo showing 250,000 MMK]
```

**Expected Result:**
- San(KBZ): 10,000,000 - 250,000 = 9,750,000
- ACT(Wallet): 200 + 10 = 210 USDT
- ✅ Balance updated

---

## Scenario 2: Buy Transaction (With Fee)

**Customer Message:**
```
Buy 10 USDT = 253,000 MMK
[USDT receipt photo]
```

**Staff (San) Reply:**
```
[KBZ receipt photo showing 250,000 MMK]
fee-3000
```

**Expected Result:**
- Bot detects: 250,000 + 3,000 = 253,000 MMK
- San(KBZ): 10,000,000 - 253,000 = 9,747,000
- ACT(Wallet): 200 + 10 = 210 USDT
- ✅ Balance updated
- 📝 Log shows: "Receipt: 250,000 + Fee: 3,000"

---

## Scenario 3: Sell Transaction (No Fee)

**Customer Message:**
```
Sell 10 USDT = 250,000 MMK
[MMK receipt photo showing 250,000]
```

**Staff (San) Reply:**
```
[Binance receipt photo showing 10 USDT]
```

**Expected Result:**
- San(KBZ): 10,000,000 + 250,000 = 10,250,000
- San(Binance): 100 - 10 = 90 USDT
- ✅ Balance updated

---

## Scenario 4: Sell Transaction (With Fee)

**Customer Message:**
```
Sell 10 USDT = 253,000 MMK
[MMK receipt photo showing 250,000]
```

**Staff (San) Reply:**
```
[Binance receipt photo showing 10 USDT]
fee-3000
```

**Expected Result:**
- Bot detects: 250,000 + 3,000 = 253,000 MMK
- San(KBZ): 10,000,000 + 253,000 = 10,253,000
- San(Binance): 100 - 10 = 90 USDT
- ✅ Balance updated
- 📝 Log shows: "Receipt: 250,000 + Fee: 3,000"

---

## Scenario 5: Sell with Swift (Network Fee)

**Customer Message:**
```
Sell 10 USDT = 250,000 MMK
[MMK receipt photo showing 250,000]
```

**Staff (San) Reply:**
```
[Swift receipt showing: 9.88 USDT sent, 0.12 network fee]
```

**Expected Result:**
- Bot detects: amount=9.88, fee=0.12, total=10.00
- San(KBZ): 10,000,000 + 250,000 = 10,250,000
- San(Swift): 50 - 10 = 40 USDT
- ✅ Balance updated

---

## Scenario 6: Buy with Multiple Receipts

**Customer Message:**
```
Buy 20 USDT = 500,000 MMK
[USDT receipt photo]
```

**Staff (San) Replies:**

**First Reply:**
```
[KBZ receipt photo showing 250,000 MMK]
```
- Bot waits for more photos

**Second Reply:**
```
[KBZ receipt photo showing 250,000 MMK]
```
- Bot processes: 250,000 + 250,000 = 500,000 ✅

**Expected Result:**
- San(KBZ): 10,000,000 - 500,000 = 9,500,000
- ACT(Wallet): 200 + 20 = 220 USDT
- ✅ Balance updated

---

## Scenario 7: Sell with Multiple USDT Receipts

**Customer Message:**
```
Sell 20 USDT = 500,000 MMK
[MMK receipt photo showing 500,000]
```

**Staff (San) Replies:**

**First Reply:**
```
[Binance receipt showing 10 USDT]
```
- Bot waits for more photos

**Second Reply:**
```
[Binance receipt showing 10 USDT]
```
- Bot processes: 10 + 10 = 20 USDT ✅

**Expected Result:**
- San(KBZ): 10,000,000 + 500,000 = 10,500,000
- San(Binance): 100 - 20 = 80 USDT
- ✅ Balance updated

---

## Scenario 8: P2P Sell

**Staff (San) Posts Directly:**
```
[MMK receipt photo showing 13,000,000]
sell 13000000/3222.6=4034.00981 fee-6.44
```

**Expected Result:**
- Bot detects P2P sell format
- MMK: 13,000,000 detected from receipt
- USDT: 3,222.6 + 6.44 = 3,229.04 total
- San(KBZ): 10,000,000 + 13,000,000 = 23,000,000
- San(Binance): 100 - 3,229.04 = 96,770.96 USDT
- ✅ Balance updated

---

## Scenario 9: Internal Transfer (MMK)

**In Accounts Matter Topic:**
```
San(Wave) to TZT(Wave)
[Receipt photo showing 1,000,000 MMK]
```

**Expected Result:**
- Bot OCRs amount: 1,000,000
- San(Wave): 5,000,000 - 1,000,000 = 4,000,000
- TZT(Wave): 3,000,000 + 1,000,000 = 4,000,000
- ✅ Balance updated

---

## Scenario 10: Internal Transfer (USDT)

**In Accounts Matter Topic:**
```
San(Binance) to TZT(Binance)
[Receipt photo showing 10 USDT]
```

**Expected Result:**
- Bot OCRs amount: 10 USDT
- San(Binance): 100 - 10 = 90 USDT
- TZT(Binance): 75 + 10 = 85 USDT
- ✅ Balance updated

---

## Scenario 11: Coin Transfer

**In Accounts Matter Topic:**
```
[TRC20 receipt photo]
San (Binance) to ACT(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT
```

**Expected Result:**
- Bot parses: sent=10, fee=0.47, received=9.53
- San(Binance): 100 - 10 = 90 USDT
- ACT(Wallet): 200 + 9.53 = 209.53 USDT
- ✅ Balance updated
- 📝 Log shows: "Sent: 10, Fee: 0.47, Received: 9.53"

---

## Scenario 12: Insufficient Balance (Buy)

**Customer Message:**
```
Buy 1000 USDT = 25,000,000 MMK
[USDT receipt photo]
```

**Staff (San) Reply:**
```
[KBZ receipt photo showing 25,000,000 MMK]
```

**Expected Result:**
- Bot detects: 25,000,000 MMK needed
- San(KBZ) has: 10,000,000 MMK
- ❌ Error logged: "Insufficient balance"
- ❌ Balance NOT updated

---

## Scenario 13: Amount Mismatch (Buy with Fee)

**Customer Message:**
```
Buy 10 USDT = 253,000 MMK
[USDT receipt photo]
```

**Staff (San) Reply:**
```
[KBZ receipt photo showing 250,000 MMK]
fee-1000
```

**Expected Result:**
- Bot detects: 250,000 + 1,000 = 251,000
- Expected: 253,000
- ❌ Error logged: "Amount mismatch! Expected: 253,000, Detected: 251,000"
- ❌ Balance NOT updated

---

## Scenario 14: Wrong Bank Type (Sell)

**Customer Message:**
```
Sell 10 USDT = 250,000 MMK
[MMK receipt photo showing 250,000]
```

**Staff (TZT) Reply:**
```
[Binance receipt showing 10 USDT]
```

**Expected Result:**
- Bot detects bank_type: "binance"
- Bot looks for TZT's Binance account
- TZT(Binance): 75 - 10 = 65 USDT ✅
- (NOT San's Binance account)

---

## Scenario 15: User Without Prefix

**Customer Message:**
```
Buy 10 USDT = 250,000 MMK
[USDT receipt photo]
```

**Unmapped User Reply:**
```
[KBZ receipt photo]
```

**Expected Result:**
- ❌ Error: "You don't have a prefix set"
- ❌ Transaction NOT processed

---

## Scenario 16: Bulk Photos (Media Group)

**Customer Message:**
```
Buy 20 USDT = 500,000 MMK
[USDT receipt photo]
```

**Staff (San) Reply:**
```
[Sends 2 KBZ receipts together as media group]
Receipt 1: 250,000 MMK
Receipt 2: 250,000 MMK
```

**Expected Result:**
- Bot waits 1.5 seconds for all photos
- Bot processes both: 250,000 + 250,000 = 500,000 ✅
- San(KBZ): 10,000,000 - 500,000 = 9,500,000
- ACT(Wallet): 200 + 20 = 220 USDT
- ✅ Balance updated

---

## Scenario 17: THB Transfer

**In Accounts Matter Topic:**
```
ACT(Bkk B) to San(Bkk B)
[Receipt photo showing 10,000 THB]
```

**Expected Result:**
- Bot OCRs amount: 10,000 THB
- ACT(Bkk B): 50,000 - 10,000 = 40,000 THB
- San(Bkk B): 0 + 10,000 = 10,000 THB
- ✅ Balance updated
- 📝 No decimals in THB amounts

---

## Scenario 18: Commands Testing

### Set User
```
Admin replies to San's message:
/set_user San
```
**Expected:** ✅ "Set prefix 'San' for @san_username"

### Show Balance
```
/balance
```
**Expected:** Shows current balance with all currencies

### Set Receiving USDT Account
```
/set_receiving_usdt_acc ACT(Wallet)
```
**Expected:** ✅ "Receiving USDT Account Updated!"

### List MMK Banks
```
/list_mmk_bank
```
**Expected:** Shows all registered banks with masked account numbers

### Test Location
```
/test
```
**Expected:** Shows current chat/topic info and configuration

---

## Error Scenarios

### E1: No Balance Loaded
```
Try any transaction before loading balance
```
**Expected:** ❌ "Balance not loaded"

### E2: No Receipt Photo
```
Reply to transaction with text only (no photo)
```
**Expected:** ❌ "No receipt photo"

### E3: Bank Not Found
```
Use bank name not in balance
```
**Expected:** ❌ "Bank not found: BankName"

### E4: Wrong Topic
```
Send buy transaction in Accounts Matter topic
```
**Expected:** Bot ignores (no response)

### E5: Invalid Fee Format
```
fee3000 (missing hyphen)
```
**Expected:** Fee not detected, uses receipt amount only

---

## Performance Benchmarks

| Operation | Expected Time | Notes |
|-----------|--------------|-------|
| OCR MMK Receipt | < 5 seconds | Depends on OpenAI API |
| OCR USDT Receipt | < 5 seconds | Depends on OpenAI API |
| Balance Update | < 1 second | Local operation |
| Media Group Processing | < 10 seconds | Waits 1.5s + OCR time |
| Command Response | < 1 second | Database query |

---

## Test Data Generator

Use this to generate test transactions:

```python
# Buy transaction
buy_amount_usdt = 10
buy_rate = 25000
buy_mmk = buy_amount_usdt * buy_rate
buy_fee = 3000
buy_total = buy_mmk + buy_fee

print(f"Buy {buy_amount_usdt} USDT = {buy_total:,} MMK")
print(f"Receipt: {buy_mmk:,} MMK")
print(f"Fee: {buy_fee:,} MMK")

# Sell transaction
sell_amount_usdt = 10
sell_rate = 25000
sell_mmk = sell_amount_usdt * sell_rate
sell_fee = 3000
sell_total = sell_mmk + sell_fee

print(f"Sell {sell_amount_usdt} USDT = {sell_total:,} MMK")
print(f"Receipt: {sell_mmk:,} MMK")
print(f"Fee: {sell_fee:,} MMK")
```

---

## Quick Verification Checklist

After each deployment:

- [ ] Bot starts without errors
- [ ] Balance loads automatically
- [ ] Buy transaction works
- [ ] Sell transaction works
- [ ] Buy with fee works
- [ ] Sell with fee works
- [ ] Internal transfer works
- [ ] Coin transfer works
- [ ] Commands respond
- [ ] Logs are clean

**If all pass:** ✅ Ready for production
**If any fail:** ❌ Debug before going live
