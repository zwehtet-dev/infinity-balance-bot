# Bot Testing Checklist

Complete testing guide for all Infinity Balance Bot features.

---

## Pre-Testing Setup

### 1. Environment Configuration
- [ ] `.env` file configured with all required variables
- [ ] `TELEGRAM_BOT_TOKEN` is valid
- [ ] `OPENAI_API_KEY` is valid
- [ ] `TARGET_GROUP_ID` is correct
- [ ] `USDT_TRANSFERS_TOPIC_ID` is set (or 0 for main chat)
- [ ] `AUTO_BALANCE_TOPIC_ID` is set
- [ ] `ACCOUNTS_MATTER_TOPIC_ID` is set
- [ ] `ALERT_TOPIC_ID` is set (optional)

### 2. Database Setup
- [ ] Run bot once to create `bot_data.db`
- [ ] Verify database tables created: `user_prefixes`, `settings`, `mmk_bank_accounts`
- [ ] Default MMK bank accounts registered

### 3. User Setup
- [ ] At least 2 test users mapped to prefixes (e.g., San, TZT)
- [ ] Use `/set_user` command to map users
- [ ] Verify mappings with database query or test transaction

### 4. Initial Balance
- [ ] Post initial balance message in Auto Balance topic
- [ ] Verify bot loads balance automatically
- [ ] Check balance with `/balance` command

---

## 1. Basic Commands Testing

### 1.1 Start Command
- [ ] Send `/start` in any topic
- [ ] Verify bot responds with help message
- [ ] Check all command categories are listed
- [ ] Verify response is sent to Alert topic (if configured)

### 1.2 Balance Command
- [ ] Send `/balance` command
- [ ] Verify current balance is displayed
- [ ] Check MMK, USDT, and THB sections (if applicable)
- [ ] Verify formatting is correct (commas, decimals)

### 1.3 Load Command
- [ ] Post a balance message
- [ ] Reply to it with `/load`
- [ ] Verify bot confirms balance loaded
- [ ] Check bank counts are correct

### 1.4 Test Command
- [ ] Send `/test` in USDT Transfers topic
- [ ] Verify bot shows current location info
- [ ] Send `/test` in Auto Balance topic
- [ ] Send `/test` in Accounts Matter topic
- [ ] Verify bot correctly identifies each location

---

## 2. User Management Testing

### 2.1 Set User Command
- [ ] Reply to user's message with `/set_user San`
- [ ] Verify confirmation message
- [ ] Test with direct user ID: `/set_user 123456789 TZT`
- [ ] Verify user can now perform transactions

### 2.2 User Prefix Filtering
- [ ] User with prefix "San" sends transaction
- [ ] Verify bot only shows San's banks in OCR
- [ ] User with prefix "TZT" sends transaction
- [ ] Verify bot only shows TZT's banks in OCR

### 2.3 List Users Command
- [ ] Send `/list_users` command
- [ ] Verify all mapped users are displayed
- [ ] Check user IDs are shown
- [ ] Check usernames are shown
- [ ] Check creation dates are shown
- [ ] Verify total user count is correct

---

## 3. Buy Transaction Testing

### 3.1 Basic Buy Transaction
**Setup:**
```
Customer posts:
Buy 100 USDT = 2,500,000 MMK
[USDT receipt photo]
```

**Test:**
- [ ] Staff replies with MMK receipt photo
- [ ] Verify bot detects MMK amount correctly
- [ ] Verify bot detects correct bank
- [ ] Check MMK is reduced from staff's bank
- [ ] Check USDT is added to receiving account
- [ ] Verify new balance posted to Auto Balance topic
- [ ] Check balance is correct

### 3.2 Buy Transaction with Fee
**Setup:**
```
Customer posts:
Buy 100 USDT = 2,503,000 MMK
[USDT receipt photo]
```

**Test:**
- [ ] Staff replies with MMK receipt (showing 2,500,000) and text: `fee-3000`
- [ ] Verify bot detects receipt amount: 2,500,000
- [ ] Verify bot detects fee: 3,000
- [ ] Verify bot calculates total: 2,503,000
- [ ] Check MMK reduced: 2,503,000
- [ ] Check logs show fee breakdown
- [ ] Verify balance is correct

### 3.3 Buy with Multiple Receipts
**Setup:**
```
Customer posts:
Buy 200 USDT = 5,000,000 MMK
[USDT receipt photo]
```

**Test:**
- [ ] Staff replies with first MMK receipt (2,500,000)
- [ ] Verify bot waits for more photos
- [ ] Staff replies with second MMK receipt (2,500,000)
- [ ] Verify bot processes when total matches
- [ ] Check balance is correct

### 3.4 Buy with Bulk Photos (Media Group)
**Setup:**
```
Customer posts:
Buy 200 USDT = 5,000,000 MMK
[USDT receipt photo]
```

**Test:**
- [ ] Staff replies with 2 MMK receipts sent together (media group)
- [ ] Verify bot waits for all photos (1.5 seconds)
- [ ] Verify bot processes all photos together
- [ ] Check total amount is correct
- [ ] Verify balance updated correctly

### 3.5 Buy with Insufficient Balance
**Setup:**
```
Customer posts:
Buy 1000 USDT = 25,000,000 MMK
[USDT receipt photo]
```

**Test:**
- [ ] Staff with low balance replies with MMK receipt
- [ ] Verify bot detects insufficient balance
- [ ] Check error is logged (not sent to chat)
- [ ] Verify balance is NOT updated

---

## 4. Sell Transaction Testing

### 4.1 Basic Sell Transaction
**Setup:**
```
Customer posts:
Sell 100 USDT = 2,500,000 MMK
[Customer's MMK receipt photo]
```

**Test:**
- [ ] Staff replies with USDT receipt photo (Binance/Swift/Wallet)
- [ ] Verify bot detects MMK from customer's receipt
- [ ] Verify bot detects USDT amount + network fee
- [ ] Verify bot detects bank type (Binance/Swift/Wallet)
- [ ] Check MMK is added to staff's bank
- [ ] Check USDT is reduced from correct staff account
- [ ] Verify balance is correct

### 4.2 Sell Transaction with MMK Fee
**Setup:**
```
Customer posts:
Sell 600 USDT = 15,200,285 MMK
[Customer's MMK receipt showing 15,197,246]
```

**Test:**
- [ ] Staff replies with USDT receipt and text: `fee-3039`
- [ ] Verify bot detects customer receipt: 15,197,246
- [ ] Verify bot detects fee: 3,039
- [ ] Verify bot calculates total: 15,200,285
- [ ] Check MMK added: 15,200,285
- [ ] Check logs show fee breakdown
- [ ] Verify balance is correct

### 4.3 Sell with Binance Receipt
**Test:**
- [ ] Use Binance withdrawal receipt
- [ ] Verify bot detects bank_type: "binance"
- [ ] Verify bot uses amount as-is (fee already included)
- [ ] Check USDT reduced from staff's Binance account

### 4.4 Sell with Swift Receipt
**Test:**
- [ ] Use Swift USDT sent receipt
- [ ] Verify bot detects bank_type: "swift"
- [ ] Verify bot adds network fee to amount
- [ ] Check USDT reduced from staff's Swift account

### 4.5 Sell with Wallet Receipt
**Test:**
- [ ] Use wallet (Trust Wallet/MetaMask) receipt
- [ ] Verify bot detects bank_type: "wallet"
- [ ] Verify bot adds network fee to amount
- [ ] Check USDT reduced from staff's Wallet account

### 4.6 Sell with Multiple USDT Receipts
**Setup:**
```
Customer posts:
Sell 200 USDT = 5,000,000 MMK
[Customer's MMK receipt]
```

**Test:**
- [ ] Staff replies with first USDT receipt (100 USDT)
- [ ] Verify bot waits for more photos
- [ ] Staff replies with second USDT receipt (100 USDT)
- [ ] Verify bot processes when total matches
- [ ] Check balance is correct

### 4.7 Sell with Bulk USDT Photos
**Setup:**
```
Customer posts:
Sell 200 USDT = 5,000,000 MMK
[Customer's MMK receipt]
```

**Test:**
- [ ] Staff replies with 2 USDT receipts sent together
- [ ] Verify bot processes all photos together
- [ ] Check total USDT is correct
- [ ] Verify balance updated correctly

---

## 5. P2P Sell Transaction Testing

### 5.1 Basic P2P Sell
**Test:**
- [ ] Staff posts directly (not a reply): `[MMK receipt] sell 13000000/3222.6=4034.00981 fee-6.44`
- [ ] Verify bot detects P2P sell format
- [ ] Verify bot detects MMK amount from receipt
- [ ] Check MMK is added to detected bank
- [ ] Check USDT + fee is reduced from staff's account
- [ ] Verify balance is correct

### 5.2 P2P Sell with Confidence Matching
**Test:**
- [ ] Use receipt with registered bank account
- [ ] Verify bot uses confidence-based matching
- [ ] Check confidence scores in logs
- [ ] Verify correct bank is selected (highest confidence)

### 5.3 P2P Sell with Low Confidence
**Test:**
- [ ] Use receipt with unregistered bank
- [ ] Verify bot shows confidence warning
- [ ] Check all confidence scores are displayed
- [ ] Verify transaction is NOT processed

---

## 6. Internal Transfer Testing

### 6.1 Basic Internal Transfer (MMK)
**Test in Accounts Matter topic:**
- [ ] Post: `San(Wave Channel) to NDT(Wave)` with receipt photo
- [ ] Verify bot detects transfer format
- [ ] Verify bot OCRs amount from receipt
- [ ] Check amount is reduced from source bank
- [ ] Check amount is added to destination bank
- [ ] Verify balance updated correctly

### 6.2 Internal Transfer (USDT)
**Test in Accounts Matter topic:**
- [ ] Post: `San(Binance) to TZT(Binance)` with receipt photo
- [ ] Verify bot detects USDT transfer
- [ ] Verify bot handles network fee correctly
- [ ] Check USDT reduced from source
- [ ] Check USDT added to destination
- [ ] Verify balance is correct

### 6.3 Internal Transfer (THB)
**Test in Accounts Matter topic:**
- [ ] Post: `ACT(Bkk B) to San(Bkk B)` with receipt photo
- [ ] Verify bot detects THB transfer
- [ ] Check THB reduced from source
- [ ] Check THB added to destination
- [ ] Verify balance is correct

### 6.4 Internal Transfer with Insufficient Balance
**Test:**
- [ ] Post transfer with amount > source balance
- [ ] Verify bot detects insufficient balance
- [ ] Check error is logged
- [ ] Verify balance is NOT updated

---

## 7. Coin Transfer Testing

### 7.1 Basic Coin Transfer
**Test in Accounts Matter topic:**
- [ ] Post: `[TRC20 receipt] San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT`
- [ ] Verify bot detects coin transfer format
- [ ] Verify bot parses: sent=10, fee=0.47, received=9.53
- [ ] Check 10 USDT reduced from San(binance)
- [ ] Check 9.53 USDT added to OKM(Wallet)
- [ ] Verify balance is correct

### 7.2 Coin Transfer Variations
**Test different formats:**
- [ ] `San(binance) to OKM (Wallet) 10 USDT - 0.47 USDT(fee) = 9.53 USDT` (spaces)
- [ ] `MMN (Wallet) to MMN (binance) 50 USDT-1.2 USDT(fee) = 48.8 USDT`
- [ ] `TZT (Swift) to TZT (Wallet) 100 USDT-0.15 USDT(fee) = 99.85 USDT`
- [ ] Verify all formats work correctly

### 7.3 Coin Transfer with Insufficient Balance
**Test:**
- [ ] Post transfer with sent amount > source balance
- [ ] Verify bot detects insufficient balance
- [ ] Check error message is sent
- [ ] Verify balance is NOT updated

---

## 8. MMK Bank Management Testing

### 8.1 Set MMK Bank
**Test:**
- [ ] Send: `/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR`
- [ ] Verify confirmation message
- [ ] Check bank is registered in database
- [ ] Test with another bank

### 8.2 List MMK Banks
**Test:**
- [ ] Send: `/list_mmk_bank`
- [ ] Verify all registered banks are listed
- [ ] Check account numbers are masked (middle digits)
- [ ] Verify holder names are shown

### 8.3 Edit MMK Bank
**Test:**
- [ ] Send: `/edit_mmk_bank San(KBZ) | 99999999999999999 | NEW NAME`
- [ ] Verify old and new details are shown
- [ ] Check bank is updated in database
- [ ] Verify next transaction uses new details

### 8.4 Remove MMK Bank
**Test:**
- [ ] Send: `/remove_mmk_bank San(KBZ)`
- [ ] Verify confirmation message
- [ ] Check bank is removed from database
- [ ] Verify bank is no longer in list

---

## 9. USDT Receiving Account Testing

### 9.1 Show Receiving Account
**Test:**
- [ ] Send: `/show_receiving_usdt_acc`
- [ ] Verify current account is displayed
- [ ] Check explanation is clear

### 9.2 Set Receiving Account
**Test:**
- [ ] Send: `/set_receiving_usdt_acc ACT(Wallet)`
- [ ] Verify confirmation message
- [ ] Check setting is saved in database
- [ ] Test buy transaction - verify USDT goes to new account

### 9.3 Buy Transaction with Different Receiving Accounts
**Test:**
- [ ] Set receiving account to `ACT(Wallet)`
- [ ] Process buy transaction
- [ ] Verify USDT added to ACT(Wallet)
- [ ] Change to `San(Swift)`
- [ ] Process another buy transaction
- [ ] Verify USDT added to San(Swift)

---

## 10. Multi-Currency Testing (THB)

### 10.1 Balance with THB
**Test:**
- [ ] Post balance with THB section
- [ ] Verify bot loads THB banks correctly
- [ ] Check `/balance` shows THB section
- [ ] Verify THB formatting (no decimals)

### 10.2 THB Internal Transfer
**Test:**
- [ ] Transfer THB between accounts
- [ ] Verify amounts are integers (no decimals)
- [ ] Check balance updated correctly

---

## 11. Error Handling Testing

### 11.1 Missing Balance
**Test:**
- [ ] Clear balance (restart bot)
- [ ] Try to process transaction
- [ ] Verify error: "Balance not loaded"

### 11.2 No User Prefix
**Test:**
- [ ] User without prefix tries transaction
- [ ] Verify error: "You don't have a prefix set"

### 11.3 No Receipt Photo
**Test:**
- [ ] Reply to transaction without photo
- [ ] Verify error: "No receipt photo"

### 11.4 Amount Mismatch
**Test:**
- [ ] Transaction expects 2,500,000 MMK
- [ ] Send receipt with 2,000,000 MMK
- [ ] Verify error is logged (amount mismatch)

### 11.5 Bank Not Found
**Test:**
- [ ] Use bank name not in balance
- [ ] Verify error: "Bank not found"

### 11.6 Wrong Topic
**Test:**
- [ ] Send buy transaction in Accounts Matter topic
- [ ] Verify bot ignores it
- [ ] Send internal transfer in USDT Transfers topic
- [ ] Verify bot ignores it

---

## 12. Logging and Monitoring

### 12.1 Check Logs
**Test:**
- [ ] Process various transactions
- [ ] Check logs show:
  - Transaction type detected
  - OCR results
  - Fee detection (if applicable)
  - Amount calculations
  - Balance updates
  - Bank matching

### 12.2 Alert Topic
**Test (if ALERT_TOPIC_ID configured):**
- [ ] Trigger error condition
- [ ] Verify error sent to Alert topic
- [ ] Send command
- [ ] Verify response sent to Alert topic

---

## 13. Edge Cases Testing

### 13.1 Concurrent Transactions
**Test:**
- [ ] Two staff members send transactions simultaneously
- [ ] Verify both are processed correctly
- [ ] Check balance is accurate

### 13.2 Same Transaction Multiple Times
**Test:**
- [ ] Process transaction
- [ ] Try to process same transaction again
- [ ] Verify bot handles correctly (pending_transactions cleanup)

### 13.3 Very Large Amounts
**Test:**
- [ ] Transaction with 100,000,000 MMK
- [ ] Verify formatting is correct (commas)
- [ ] Check calculation is accurate

### 13.4 Very Small USDT Amounts
**Test:**
- [ ] Transaction with 0.01 USDT
- [ ] Verify decimal precision (4 places)
- [ ] Check calculation is accurate

### 13.5 Special Characters in Text
**Test:**
- [ ] Message with emojis: `fee-3000 😊`
- [ ] Message with extra text: `Some text fee-3000 more text`
- [ ] Verify bot extracts fee correctly

---

## 14. Performance Testing

### 14.1 OCR Speed
**Test:**
- [ ] Time OCR processing for MMK receipt
- [ ] Time OCR processing for USDT receipt
- [ ] Verify reasonable response time (<10 seconds)

### 14.2 Multiple Photos
**Test:**
- [ ] Send 5 photos in media group
- [ ] Verify all are processed
- [ ] Check processing time is reasonable

### 14.3 Database Performance
**Test:**
- [ ] Add 20+ user mappings
- [ ] Add 20+ MMK bank accounts
- [ ] Verify queries are fast
- [ ] Check no performance degradation

---

## 15. Integration Testing

### 15.1 Full Buy Flow
**Test complete workflow:**
- [ ] Customer posts buy request
- [ ] Staff sends MMK receipt with fee
- [ ] Bot processes transaction
- [ ] Balance updated in Auto Balance topic
- [ ] Verify all amounts correct
- [ ] Check logs are complete

### 15.2 Full Sell Flow
**Test complete workflow:**
- [ ] Customer posts sell request with MMK receipt
- [ ] Staff sends USDT receipt with fee
- [ ] Bot processes transaction
- [ ] Balance updated in Auto Balance topic
- [ ] Verify all amounts correct
- [ ] Check logs are complete

### 15.3 Full Internal Transfer Flow
**Test complete workflow:**
- [ ] Post internal transfer in Accounts Matter
- [ ] Bot OCRs and processes
- [ ] Balance updated in Auto Balance topic
- [ ] Verify amounts correct

### 15.4 Full Coin Transfer Flow
**Test complete workflow:**
- [ ] Post coin transfer in Accounts Matter
- [ ] Bot parses and processes
- [ ] Balance updated in Auto Balance topic
- [ ] Verify sent and received amounts correct

---

## 16. Regression Testing

After any code changes, re-test:
- [ ] Basic buy transaction
- [ ] Basic sell transaction
- [ ] Buy with fee
- [ ] Sell with fee
- [ ] Internal transfer
- [ ] Coin transfer
- [ ] All commands work
- [ ] Balance loading works
- [ ] User prefix filtering works

---

## Test Results Template

```
Test Date: ___________
Tester: ___________
Bot Version: 2.2.0

| Test Category | Tests Passed | Tests Failed | Notes |
|--------------|--------------|--------------|-------|
| Basic Commands | __/4 | __ | |
| User Management | __/2 | __ | |
| Buy Transactions | __/5 | __ | |
| Sell Transactions | __/7 | __ | |
| P2P Sell | __/3 | __ | |
| Internal Transfers | __/4 | __ | |
| Coin Transfers | __/3 | __ | |
| MMK Bank Management | __/4 | __ | |
| USDT Receiving Account | __/3 | __ | |
| Multi-Currency (THB) | __/2 | __ | |
| Error Handling | __/6 | __ | |
| Logging | __/2 | __ | |
| Edge Cases | __/5 | __ | |
| Performance | __/3 | __ | |
| Integration | __/4 | __ | |
| **TOTAL** | **__/57** | **__** | |

Overall Status: ☐ PASS ☐ FAIL

Critical Issues Found:
1. 
2. 
3. 

Minor Issues Found:
1. 
2. 
3. 

Recommendations:
1. 
2. 
3. 
```

---

## Quick Smoke Test (5 minutes)

For quick verification after deployment:

1. [ ] `/start` - Bot responds
2. [ ] `/balance` - Shows current balance
3. [ ] Post balance message - Bot loads it
4. [ ] Buy transaction (no fee) - Works
5. [ ] Sell transaction (no fee) - Works
6. [ ] Buy with fee - Works
7. [ ] Sell with fee - Works
8. [ ] Internal transfer - Works
9. [ ] Coin transfer - Works
10. [ ] Check logs - No errors

If all pass: ✅ Bot is working
If any fail: ❌ Investigate immediately

---

## Automated Testing

Run automated tests:
```bash
python test_balance_parsing.py
python test_coin_transfer.py
python test_mmk_fee.py
```

All should pass before manual testing.
