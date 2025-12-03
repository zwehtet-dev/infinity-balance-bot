# Quick Start Guide

## 1. Setup (5 minutes)

```bash
# Clone/navigate to project
cd infinity-balance-bot

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required values in `.env`:
- `TELEGRAM_BOT_TOKEN` - Get from @BotFather
- `TARGET_GROUP_ID` - Your Telegram group ID (negative number)
- `USDT_TRANSFERS_TOPIC_ID` - Topic ID for transactions
- `AUTO_BALANCE_TOPIC_ID` - Topic ID for balance messages
- `OPENAI_API_KEY` - Your OpenAI API key

## 2. Install & Run

### Option A: Local
```bash
make install
make run
```

### Option B: Docker
```bash
make docker-build
make docker-up
make docker-logs  # View logs
```

## 3. Initialize Balance

Post this message in your **auto balance topic**:
```
MMKKpay P -13,205,369KBZ -11,044,185Wave -6,351,481AYA -0CB -10,000Yoma -0USDTWallet -5607.1401
```

Bot will auto-load it. Check with `/balance` command.

## 4. Test Transaction

### Buy Transaction
1. In USDT transfers topic, post:
   ```
   Buy 100 = 235,000
   ```
2. Reply to that message with MMK receipt photo
3. Bot processes and updates balance

### Sell Transaction
1. User posts with MMK receipt:
   ```
   Sell 100 = 235,000
   ```
2. Staff replies with USDT receipt photo
3. Bot processes and updates balance

## Troubleshooting

**Balance not loading?**
- Check topic IDs are correct
- Ensure balance message format is exact
- Use `/load` command by replying to balance message

**OCR not detecting bank?**
- Ensure receipt image is clear
- Check bank name matches one of: CB, KBZ, Kpay P, Kpay, Wave, AYA, Yoma
- View logs for OCR response

**Amount mismatch?**
- Bot allows ±100 MMK tolerance
- Check receipt shows correct amount
- Verify transaction message format

## Commands

- `/start` - Check status
- `/balance` - Show current balance
- `/load` - Load balance (reply to balance message)

## Support

Check logs:
```bash
# Local
tail -f logs

# Docker
make docker-logs
```
