# Infinity Balance Bot

Clean, minimal Telegram bot for managing MMK and USDT balances independently (no backend required).

## Features

- ✅ **Independent Mode**: No database, balances stored in Telegram messages
- 🔍 **OCR Recognition**: Automatic bank detection from receipts using GPT-4 Vision
- 💱 **Buy/Sell Processing**: Handles both transaction types
- 📊 **Auto Balance Loading**: Reads balance from auto balance topic
- 🏦 **Multi-Bank Support**: CB, KBZ, Kpay, Kpay Partner, Wave, AYA, Yoma

## Setup

1. **Install dependencies**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Run bot**:
```bash
python bot.py
```

## Balance Message Format

Single-line format:
```
MMKKpay P -13,205,369KBZ -11,044,185Wave -6,351,481AYA -0CB -10,000Yoma -0USDTWallet -5607.1401
```

## Usage

### Initialize
1. Post balance message in auto balance topic
2. Bot auto-loads it

### Buy Transaction (User buys USDT)
1. User posts: "Buy 100 = 235,000"
2. Staff replies with MMK receipt photo
3. Bot processes and updates balance

### Sell Transaction (User sells USDT)
1. User posts: "Sell 100 = 235,000" with MMK receipt
2. Staff replies with USDT receipt photo
3. Bot processes and updates balance

## Commands

- `/start` - Check bot status
- `/balance` - Show current balance
- `/load` - Load balance from message (reply to balance message)

## How It Works

1. **Balance Storage**: Balances stored as Telegram messages in auto balance topic
2. **OCR Processing**: GPT-4 Vision analyzes receipts to detect bank and amount
3. **Transaction Flow**:
   - Extract transaction info from message
   - OCR receipt(s)
   - Verify amounts
   - Update balance
   - Post new balance message

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TARGET_GROUP_ID` | Telegram group ID (negative number) |
| `USDT_TRANSFERS_TOPIC_ID` | Topic ID for transactions (set to 0 for main chat) |
| `AUTO_BALANCE_TOPIC_ID` | Topic ID for balance messages (set to 0 for main chat) |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 Vision |

**Note:** If you don't use topics in your Telegram group, set `USDT_TRANSFERS_TOPIC_ID` and `AUTO_BALANCE_TOPIC_ID` to `0` to use the main chat instead.

## Bank Recognition

The bot recognizes banks by visual features:
- **CB**: Blue "Account History" or rainbow logo
- **KBZ**: "INTERNAL TRANSFER - CONFIRM" with green banner
- **Kpay Partner**: RED/CORAL color with "Payment Successful"
- **Kpay**: BLUE with "KBZ Pay" branding
- **Wave**: YELLOW header or green "Successful"
- **AYA**: "Payment Complete" or "AYA PAY" logo
- **Yoma**: "Flexi Everyday Account" text

## License

MIT
