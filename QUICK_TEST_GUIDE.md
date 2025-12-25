# Quick Test Guide

Fast reference for testing bot features in 15 minutes.

---

## 🚀 Quick Start (2 minutes)

1. **Start Bot**
   ```bash
   python bot.py
   ```

2. **Load Balance**
   - Post balance in Auto Balance topic
   - Verify bot loads it automatically

3. **Test Command**
   ```
   /balance
   ```
   - Should show current balance

---

## ✅ Core Features (10 minutes)

### 1. Buy Transaction (2 min)
```
Customer: Buy 10 USDT = 250,000 MMK [USDT photo]
Staff: [MMK receipt: 250,000]
✅ Check: MMK reduced, USDT added
```

### 2. Buy with Fee (2 min)
```
Customer: Buy 10 USDT = 253,000 MMK [USDT photo]
Staff: [MMK receipt: 250,000] fee-3000
✅ Check: 253,000 MMK reduced (250k + 3k)
```

### 3. Sell Transaction (2 min)
```
Customer: Sell 10 USDT = 250,000 MMK [MMK receipt: 250,000]
Staff: [USDT receipt: 10]
✅ Check: MMK added, USDT reduced
```

### 4. Sell with Fee (2 min)
```
Customer: Sell 10 USDT = 253,000 MMK [MMK receipt: 250,000]
Staff: [USDT receipt: 10] fee-3000
✅ Check: 253,000 MMK added (250k + 3k)
```

### 5. Coin Transfer (2 min)
```
In Accounts Matter:
San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT
✅ Check: 10 reduced from source, 9.53 added to destination
```

---

## 🔧 Commands Test (3 minutes)

```
/start          → Shows help
/balance        → Shows balance
/list_users     → Shows all user mappings
/test           → Shows location info
/list_mmk_bank  → Shows registered banks
/show_receiving_usdt_acc → Shows USDT config
```

---

## ❌ Error Tests (Optional - 2 minutes)

1. **No Balance**
   - Restart bot, try transaction
   - ✅ Should error: "Balance not loaded"

2. **No Prefix**
   - Unmapped user tries transaction
   - ✅ Should error: "You don't have a prefix set"

3. **Amount Mismatch**
   - Send wrong amount
   - ✅ Should error in logs

---

## 📊 Test Results

| Feature | Status | Time | Notes |
|---------|--------|------|-------|
| Buy | ☐ | __:__ | |
| Buy + Fee | ☐ | __:__ | |
| Sell | ☐ | __:__ | |
| Sell + Fee | ☐ | __:__ | |
| Coin Transfer | ☐ | __:__ | |
| Commands | ☐ | __:__ | |
| Errors | ☐ | __:__ | |

**Overall:** ☐ PASS ☐ FAIL

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Bot not responding | Check .env, restart bot |
| Balance not loading | Post in correct topic |
| OCR fails | Check OpenAI API key |
| Wrong bank detected | Check user prefix mapping |
| Fee not detected | Check format: `fee-3000` |

---

## 📝 Test Data

**Test Balance:**
```
San(KBZ) -10000000
San(Binance) -100.0000
ACT(Wallet) -200.0000
```

**Test Users:**
- San (ID: 123456789)
- TZT (ID: 987654321)

**Test Amounts:**
- Buy: 10 USDT = 250,000 MMK
- Fee: 3,000 MMK
- Total: 253,000 MMK

---

## 🎯 Success Criteria

✅ All 7 core tests pass
✅ Commands respond correctly
✅ Balance updates accurately
✅ Logs show no errors
✅ Response time < 10 seconds

**If all pass:** Ready for production! 🚀
**If any fail:** Check logs and debug 🔍

---

## 📞 Quick Support

**Check Logs:**
```bash
# View recent logs
tail -f bot.log

# Search for errors
grep ERROR bot.log
```

**Database Check:**
```bash
sqlite3 bot_data.db "SELECT * FROM user_prefixes;"
sqlite3 bot_data.db "SELECT * FROM mmk_bank_accounts;"
```

**Restart Bot:**
```bash
# Stop
Ctrl+C

# Start
python bot.py
```

---

## 🔄 Regression Test (After Updates)

Run these 5 tests after any code change:

1. ✅ Buy with fee
2. ✅ Sell with fee
3. ✅ Coin transfer
4. ✅ Internal transfer
5. ✅ Commands work

**Time:** 5 minutes
**If all pass:** Update is safe ✅
