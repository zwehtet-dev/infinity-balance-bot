# Deploy On Ubuntu VPS

This bot is a long-running Telegram polling process. On Ubuntu, the simplest reliable setup is:

- Python virtual environment
- `.env` file for secrets and runtime config
- `systemd` service for auto-start and restart
- Optional PostgreSQL, or SQLite for a simple single-server setup

## 1. Prepare the VPS

Connect to your server:

```bash
ssh your_user@your_vps_ip
```

Update packages:

```bash
sudo apt update && sudo apt upgrade -y
```

Install system packages required by this project:

```bash
sudo apt install -y python3.11 python3.11-venv python3-pip git libpq-dev
```

If you want PostgreSQL on the same VPS, also install:

```bash
sudo apt install -y postgresql postgresql-contrib
```

## 2. Create App Directory

Example path:

```bash
sudo mkdir -p /opt/infinity-tg-auto-balance-bot
sudo chown -R "$USER":"$USER" /opt/infinity-tg-auto-balance-bot
cd /opt/infinity-tg-auto-balance-bot
```

Clone your repository:

```bash
git clone <your-repo-url> .
```

## 3. Create Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Use Python 3.11 for this project. Some Ubuntu images now default to Python 3.14, which can break older library assumptions around the default asyncio event loop.

## 4. Configure Environment

Create the runtime env file:

```bash
cp .env.example .env
nano .env
```

Minimum required values:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_api_key
TARGET_GROUP_ID=-1001234567890
USDT_TRANSFERS_TOPIC_ID=0
AUTO_BALANCE_TOPIC_ID=0
ACCOUNTS_MATTER_TOPIC_ID=0
ALERT_TOPIC_ID=0
SQLITE_DB_FILE=/opt/infinity-tg-auto-balance-bot/data/bot_data.db
```

Notes:

- Use `0` for topic IDs if the group does not use forum topics.
- `TARGET_GROUP_ID` is usually a negative Telegram chat ID.
- For SQLite, use an absolute DB path so the location is explicit.

Create the SQLite data directory if you use SQLite:

```bash
mkdir -p /opt/infinity-tg-auto-balance-bot/data
```

If you want PostgreSQL instead of SQLite, set `DATABASE_URL` and omit `SQLITE_DB_FILE`:

```env
DATABASE_URL=postgresql://bot_user:strong_password@127.0.0.1:5432/infinity_bot
```

## 5. Optional: Create PostgreSQL Database

Skip this section if you are using SQLite.

Create DB and user:

```bash
sudo -u postgres psql
```

Then run:

```sql
CREATE DATABASE infinity_bot;
CREATE USER bot_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE infinity_bot TO bot_user;
\q
```

Update `.env` with the matching `DATABASE_URL`.

## 6. Test The Bot Manually

Before creating the service, verify the bot starts cleanly:

```bash
cd /opt/infinity-tg-auto-balance-bot
source .venv/bin/activate
python bot.py
```

Expected result:

- The process stays running.
- You see log lines showing the bot started.
- The bot responds to `/start` in Telegram.

Stop it with `Ctrl+C` after the smoke test.

## 7. Create systemd Service

Copy the example service file from this repo:

```bash
sudo cp deploy/infinity-balance-bot.service /etc/systemd/system/infinity-balance-bot.service
```

Open it and confirm these values are correct:

- `User`
- `WorkingDirectory`
- `ExecStart`

The service does not import environment variables directly. That is intentional: the bot already loads `.env` itself via `python-dotenv`, and this avoids `systemd` parsing differences with dotenv-style files.

Then reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable infinity-balance-bot
sudo systemctl start infinity-balance-bot
```

Check status:

```bash
sudo systemctl status infinity-balance-bot
```

View live logs:

```bash
sudo journalctl -u infinity-balance-bot -f
```

## 8. Common Operations

Restart after code changes:

```bash
cd /opt/infinity-tg-auto-balance-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart infinity-balance-bot
```

Stop service:

```bash
sudo systemctl stop infinity-balance-bot
```

Start service:

```bash
sudo systemctl start infinity-balance-bot
```

See recent logs:

```bash
sudo journalctl -u infinity-balance-bot -n 100 --no-pager
```

## 9. Firewall

This bot uses long polling, so you usually do not need to open an inbound app port.

If `ufw` is enabled, allow SSH:

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

## 10. Recommended Production Notes

- Use a non-root Linux user for the bot service.
- Keep `.env` readable only by the app user.
- Prefer PostgreSQL if you expect larger data volume or want stronger durability guarantees.
- Back up either the PostgreSQL database or the SQLite file in `/opt/infinity-tg-auto-balance-bot/data/`.

## Troubleshooting

If the service fails immediately:

```bash
sudo systemctl status infinity-balance-bot
sudo journalctl -u infinity-balance-bot -n 200 --no-pager
```

If import errors appear, make sure the service uses the venv Python:

```bash
/opt/infinity-tg-auto-balance-bot/.venv/bin/python --version
```

If the journal paths show `python3.14` inside the venv, rebuild the virtual environment with Python 3.11 and reinstall dependencies:

```bash
cd /opt/infinity-tg-auto-balance-bot
sudo systemctl stop infinity-balance-bot
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
sudo systemctl start infinity-balance-bot
```

If Telegram commands do not work:

- Verify `TELEGRAM_BOT_TOKEN`
- Verify the bot is in the target group
- Verify `TARGET_GROUP_ID` and topic IDs
- Disable stale updates by restarting the service

If database writes fail:

- For SQLite, check that the data directory exists and is writable
- For PostgreSQL, verify `DATABASE_URL`, DB permissions, and that PostgreSQL is running

## Suggested Directory Layout

```text
/opt/infinity-tg-auto-balance-bot/
├── .env
├── .venv/
├── bot.py
├── data/
│   └── bot_data.db
├── deploy/
│   └── infinity-balance-bot.service
└── requirements.txt
```