# Deployment Checklist

## Pre-Deployment

### 1. Backup Current System ✓
- [ ] Backup `bot.py` → `bot.py.backup`
- [ ] Backup `.env` → `.env.backup`
- [ ] Save current balance messages
- [ ] Note all staff user IDs

### 2. Review Changes ✓
- [ ] Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- [ ] Review [UPDATES.md](UPDATES.md)
- [ ] Check [CHANGELOG.md](CHANGELOG.md)
- [ ] Read [QUICKSTART_V2.md](QUICKSTART_V2.md)

### 3. Test Locally ✓
- [ ] Run `python test_balance_parsing.py`
- [ ] Verify output shows correct parsing
- [ ] Check for any errors

---

## Deployment Steps

### Step 1: Update Configuration
```bash
# Add to .env file
echo "ACCOUNTS_MATTER_TOPIC_ID=789" >> .env
```

**Replace 789 with your actual Accounts Matter topic ID**

- [ ] Added `ACCOUNTS_MATTER_TOPIC_ID` to `.env`
- [ ] Verified all topic IDs are correct

### Step 2: Start Bot
```bash
python bot.py
```

**Expected output:**
```
✅ Database initialized
🤖 Infinity Balance Bot Started
📱 Group: -1001234567890
💱 USDT Topic: 123
📊 Balance Topic: 456
🏦 Accounts Matter Topic: 789
```

- [ ] Bot started successfully
- [ ] Database created (`bot_data.db`)
- [ ] All topic IDs displayed correctly

### Step 3: Set Up Staff Mappings

**For each staff member:**

1. Have them send a message in the group
2. Reply to their message with: `/set_user <prefix>`

**Example:**
```
Reply to San's message:
/set_user San

Bot response:
✅ Set prefix 'San' for @san_username (ID: 123456789)
```

**Staff to set up:**
- [ ] San → `/set_user San`
- [ ] Thin Zar Htet → `/set_user TZT`
- [ ] MMN → `/set_user MMN`
- [ ] Nandar → `/set_user NDT`
- [ ] MMM → `/set_user MMM`
- [ ] PPK → `/set_user PPK`
- [ ] ACT → `/set_user ACT`
- [ ] OKM → `/set_user OKM`
- [ ] (Add others as needed)

**Verify mappings:**
```bash
python setup_users.py
```

### Step 4: Convert Balance Format

**Option A: Use migration script**
```bash
python migrate_balance_format.py
```
- Select option 1 (Interactive conversion)
- Paste old balance
- Enter default prefix
- Copy converted balance

**Option B: Manual conversion**

Old format:
```
MMK
Kpay P -13,205,369
KBZ -11,044,185
USDT
Wallet -5607.1401
```

New format:
```
San(Kpay P) -13205369
San(KBZ) -11044185
USDT
San(Wallet) -5607.14
```

- [ ] Balance converted to new format
- [ ] All banks have staff prefixes
- [ ] USDT amounts have 2 decimal places
- [ ] MMK amounts are integers

### Step 5: Post New Balance

1. Go to Auto Balance topic
2. Post the converted balance message
3. Bot should auto-load it

**Expected bot log:**
```
✅ Balance loaded: 8 MMK banks, 5 USDT banks
```

- [ ] Balance posted to Auto Balance topic
- [ ] Bot auto-loaded the balance
- [ ] Correct number of banks detected

### Step 6: Test Buy Transaction

1. Customer posts: `Buy 100 = 2,500,000`
2. Staff member replies with MMK receipt photo
3. Bot should process and update balance

**Expected response:**
```
✅ Buy processed!
MMK: -2,500,000 (San(KBZ))
USDT: +100.0000
```

- [ ] Buy transaction processed successfully
- [ ] Correct bank updated
- [ ] New balance posted to Auto Balance topic

### Step 7: Test Sell Transaction

1. Customer posts: `Sell 50 = 1,250,000` with MMK receipt
2. Staff member replies with USDT receipt photo
3. Bot should process and update balance

**Expected response:**
```
✅ Sell processed!
MMK: +1,250,000 (San(KBZ))
USDT: -50.0000
```

- [ ] Sell transaction processed successfully
- [ ] Correct banks updated
- [ ] New balance posted to Auto Balance topic

### Step 8: Test Internal Transfer

1. Go to Accounts Matter topic
2. Post: `San(Wave Channel) to NDT (Wave)`
3. Attach receipt photo
4. Bot should process transfer

**Expected response:**
```
✅ Internal transfer processed!
From: San(Wave Channel)
To: NDT (Wave)
Amount: 1,000,000

New balances:
San(Wave Channel): 970,347
NDT (Wave): 3,864,900
```

- [ ] Internal transfer processed successfully
- [ ] Source bank reduced
- [ ] Destination bank increased
- [ ] New balance posted to Auto Balance topic

---

## Post-Deployment

### Verification

- [ ] All staff members have prefixes set
- [ ] Balance format is correct
- [ ] Buy transactions work
- [ ] Sell transactions work
- [ ] Internal transfers work
- [ ] Multiple receipts work (media groups)
- [ ] Balance updates correctly
- [ ] No errors in bot logs

### Monitoring

**Check bot logs regularly for:**
- Transaction processing
- OCR results
- Balance updates
- Error messages

**Use commands:**
- `/test` - Verify configuration
- `/balance` - Check current balance
- `/load` - Reload balance if needed

### Troubleshooting

**If staff gets "You don't have a prefix set":**
1. Reply to their message with `/set_user <prefix>`
2. Verify with `python setup_users.py`

**If balance not updating:**
1. Check prefix matches exactly (case-sensitive)
2. Verify balance format is correct
3. Use `/load` to reload balance

**If OCR not detecting:**
1. Ensure receipt photo is clear
2. Check bank name matches balance message
3. Verify staff prefix is set

---

## Rollback Plan

**If issues occur:**

1. Stop the bot (Ctrl+C)
2. Restore backup:
   ```bash
   cp bot.py.backup bot.py
   cp .env.backup .env
   ```
3. Restart bot:
   ```bash
   python bot.py
   ```
4. Post old balance format to Auto Balance topic

---

## Success Criteria

✅ **Deployment is successful when:**

1. All staff members have prefixes set
2. Balance loads correctly with new format
3. Buy transactions update correct staff banks
4. Sell transactions update correct staff banks
5. Internal transfers work between accounts
6. No errors in bot logs
7. All balances update correctly

---

## Support Resources

- **Quick Start:** [QUICKSTART_V2.md](QUICKSTART_V2.md)
- **Full Documentation:** [UPDATES.md](UPDATES.md)
- **Changes:** [CHANGELOG.md](CHANGELOG.md)
- **Implementation:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

## Contact

For issues or questions:
1. Check bot logs
2. Review documentation
3. Test with `/test` command
4. Run test scripts

---

**Ready to deploy? Follow the steps above! 🚀**
