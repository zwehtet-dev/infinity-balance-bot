# Quick Start Guide - Version 2.0

## 🚀 Getting Started in 5 Minutes

### Step 1: Update Configuration

Add the new topic ID to your `.env` file:

```bash
# Add this line
ACCOUNTS_MATTER_TOPIC_ID=789  # Replace with your actual topic ID
```

### Step 2: Start the Bot

```bash
python bot.py
```

The bot will automatically create the `bot_data.db` database on first run.

### Step 3: Set Up Staff Mappings

Have each staff member send a message in the group, then reply to their message:

```
Reply to San's message:
/set_user San

Reply to TZT's message:
/set_user TZT

Reply to MMN's message:
/set_user MMN

Reply to NDT's message:
/set_user NDT
```

You should see:
```
✅ Set prefix 'San' for @san_username (ID: 123456789)
```

### Step 4: Post New Balance Format

Post a balance message in the Auto Balance topic using the new format:

```
San(Kpay P) -2639565
San(CB M) -0
San(KBZ)-11044185
San(Wave) -0
San(Wave M )-1220723
San(Wave Channel) - 1970347
NDT (Wave) -2864900
MMM (Kpay p)-8839154

USDT
San(Swift) -81.99
MMN(Binance)-(15.86)
NDT(Binance)-6.96
TZT (Binance)-(222.6)
PPK (Binance) - 0
```

Bot will automatically load it and show:
```
✅ Balance loaded: 8 MMK banks, 5 USDT banks
```

### Step 5: Test a Transaction

**Buy Transaction:**
1. Customer posts: `Buy 100 = 2,500,000`
2. Staff (San) replies with KBZ receipt photo
3. Bot processes and updates `San(KBZ)` balance

**Sell Transaction:**
1. Customer posts: `Sell 100 = 2,500,000` with MMK receipt
2. Staff (San) replies with USDT receipt photo
3. Bot updates `San(KBZ)` and `San(Swift)` balances

### Step 6: Test Internal Transfer

In the Accounts Matter topic:

```
San(Wave Channel) to NDT (Wave)
[attach receipt photo showing 1,000,000 MMK]
```

Bot will:
1. Detect the transfer format
2. OCR the amount from receipt
3. Reduce `San(Wave Channel)` by 1,000,000
4. Increase `NDT (Wave)` by 1,000,000
5. Post updated balance to Auto Balance topic

---

## 🧪 Testing

### Test Balance Parsing

```bash
python test_balance_parsing.py
```

Should show:
```
✅ Parsed 13 MMK banks, 7 USDT banks
```

### Test Bot Configuration

In Telegram, send:
```
/test
```

Should show your current configuration and location.

---

## 📋 Common Tasks

### Add a New Staff Member

1. Have them send a message in the group
2. Reply to their message: `/set_user <prefix>`
3. Add their banks to the balance message

### Check Current Mappings

```bash
python setup_users.py
```

Shows all user → prefix mappings.

### View Current Balance

In Telegram:
```
/balance
```

### Reload Balance

Reply to a balance message with:
```
/load
```

---

## 🔍 Troubleshooting

### "You don't have a prefix set"

**Solution:** Admin needs to use `/set_user` command:
1. Reply to the staff member's message
2. Send: `/set_user <prefix>`

### Balance not updating

**Checklist:**
- [ ] Balance message uses new format with prefixes
- [ ] Staff member has prefix set in database
- [ ] Prefix in database matches prefix in balance message (case-sensitive)
- [ ] Receipt photo is clear and readable

### Internal transfer not working

**Checklist:**
- [ ] Message is in Accounts Matter topic
- [ ] Format is correct: `Prefix(Bank) to Prefix(Bank)`
- [ ] Both banks exist in balance message
- [ ] Receipt photo is attached
- [ ] Source bank has sufficient balance

### OCR not detecting bank

**Solutions:**
- Ensure receipt photo is clear and well-lit
- Check that bank name in balance message matches receipt
- Verify staff prefix is set correctly
- Try taking a clearer photo

---

## 💡 Tips

### Multiple Receipts

Send multiple photos as a media group (select multiple photos at once):
- Bot accumulates amounts from all photos
- Verifies total matches expected amount
- Processes once all photos are received

### USDT Tolerance

USDT transactions allow up to 0.03 difference:
- Expected: 100.00 USDT
- Detected: 100.02 USDT
- ✅ Will be accepted

### Bank Name Matching

Bank names must match exactly (case-sensitive):
- ✅ `San(KBZ)` matches `San(KBZ)`
- ❌ `San(KBZ)` does NOT match `san(kbz)`
- ❌ `San(KBZ)` does NOT match `San(KBZ )`

### Prefix Examples

Common prefixes:
- `San` - Main staff member
- `TZT` - Thin Zar Hhet
- `MMN` - Staff member MMN
- `NDT` - Nandar
- `MMM` - Staff member MMM
- `PPK` - Staff member PPK
- `ACT` - Staff member ACT
- `OKM` - Staff member OKM

---

## 📞 Support

For issues or questions:
1. Check the logs: Bot prints detailed information
2. Review [UPDATES.md](UPDATES.md) for detailed documentation
3. Check [CHANGELOG.md](CHANGELOG.md) for recent changes
4. Test with `/test` command to verify configuration

---

## 🎯 Next Steps

1. ✅ Set up all staff members with `/set_user`
2. ✅ Convert balance messages to new format
3. ✅ Test buy/sell transactions
4. ✅ Test internal transfers
5. ✅ Monitor bot logs for any issues

**You're all set! 🎉**
