#!/usr/bin/env python3
"""
Infinity Balance Bot - Independent Mode
Manages MMK and USDT balances via Telegram messages (no backend required)
"""

import os
import re
import json
import logging
import base64
import sqlite3
import asyncio
import traceback
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from openai import OpenAI
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TARGET_GROUP_ID = int(os.getenv('TARGET_GROUP_ID', '0'))
USDT_TRANSFERS_TOPIC_ID = int(os.getenv('USDT_TRANSFERS_TOPIC_ID', '0'))
AUTO_BALANCE_TOPIC_ID = int(os.getenv('AUTO_BALANCE_TOPIC_ID', '0'))
ACCOUNTS_MATTER_TOPIC_ID = int(os.getenv('ACCOUNTS_MATTER_TOPIC_ID', '0'))
ALERT_TOPIC_ID = int(os.getenv('ALERT_TOPIC_ID', '0'))

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Missing required environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

# Database setup
DB_FILE = 'bot_data.db'

def init_database():
    """Initialize SQLite database for user-prefix mappings and settings"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # User prefixes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_prefixes (
            user_id INTEGER PRIMARY KEY,
            prefix_name TEXT NOT NULL,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Settings table for receiving USDT account
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # MMK bank accounts table for verification
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mmk_bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL UNIQUE,
            account_number TEXT NOT NULL,
            account_holder TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Media group photos table for storing downloaded photos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_group_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_group_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(media_group_id, message_id)
        )
    ''')
    
    # Create index for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_media_group_id ON media_group_photos(media_group_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_message_id ON media_group_photos(message_id)
    ''')
    
    # Sale receipt OCR results table - stores pre-scanned receipt data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_receipt_ocr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            media_group_id TEXT,
            receipt_index INTEGER DEFAULT 0,
            transaction_type TEXT,
            detected_amount REAL,
            detected_bank TEXT,
            detected_usdt REAL,
            ocr_raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, receipt_index)
        )
    ''')
    
    # Create index for sale receipt lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sale_receipt_message_id ON sale_receipt_ocr(message_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sale_receipt_media_group ON sale_receipt_ocr(media_group_id)
    ''')
    
    # Set default receiving USDT account if not exists
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('receiving_usdt_account', 'ACT(Wallet)')
    ''')
    
    # Insert default MMK bank accounts if not exists
    default_banks = [
        ('San(CB)', '0225100900026042', 'Chaw Su Thu Zar'),
        ('San(KBZ)', '27251127201844001', 'CHAW SU THU ZAR'),
        ('San(Yoma)', '007011118014339', 'Daw Chaw Su Thu Zar'),
        ('San(Kpay P)', '300948464', 'Chaw Su'),
        ('San(AYA)', '40038204256', 'CHAW SU THU ZAR'),
    ]
    
    for bank_name, account_number, account_holder in default_banks:
        cursor.execute('''
            INSERT OR IGNORE INTO mmk_bank_accounts (bank_name, account_number, account_holder)
            VALUES (?, ?, ?)
        ''', (bank_name, account_number, account_holder))
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized with default banks")

# Media group photos directory
MEDIA_GROUP_DIR = 'media_group_photos'
os.makedirs(MEDIA_GROUP_DIR, exist_ok=True)

def save_media_group_photo(media_group_id: str, message_id: int, photo_bytes: bytes) -> str:
    """Save a photo from media group to disk and record in database"""
    # Create filename
    filename = f"{media_group_id}_{message_id}.jpg"
    file_path = os.path.join(MEDIA_GROUP_DIR, filename)
    
    # Save to disk
    with open(file_path, 'wb') as f:
        f.write(photo_bytes)
    
    # Save to database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO media_group_photos (media_group_id, message_id, file_path)
        VALUES (?, ?, ?)
    ''', (media_group_id, message_id, file_path))
    conn.commit()
    conn.close()
    
    logger.info(f"Saved media group photo: {file_path}")
    return file_path

def get_media_group_photos(media_group_id: str) -> list:
    """Get all photo paths for a media group from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message_id, file_path FROM media_group_photos
        WHERE media_group_id = ?
        ORDER BY message_id
    ''', (media_group_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_media_group_by_message_id(message_id: int) -> tuple:
    """Get media group ID and all photos by any message ID in the group"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # First find the media_group_id for this message
    cursor.execute('''
        SELECT media_group_id FROM media_group_photos
        WHERE message_id = ?
    ''', (message_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None, []
    
    media_group_id = result[0]
    
    # Get all photos in this media group
    cursor.execute('''
        SELECT message_id, file_path FROM media_group_photos
        WHERE media_group_id = ?
        ORDER BY message_id
    ''', (media_group_id,))
    photos = cursor.fetchall()
    conn.close()
    
    return media_group_id, photos

def delete_media_group_photos(media_group_id: str):
    """Delete all photos for a media group from disk and database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get file paths first
    cursor.execute('''
        SELECT file_path FROM media_group_photos
        WHERE media_group_id = ?
    ''', (media_group_id,))
    results = cursor.fetchall()
    
    # Delete files from disk
    for (file_path,) in results:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted media group photo: {file_path}")
        except Exception as e:
            logger.warning(f"Could not delete file {file_path}: {e}")
    
    # Delete from database
    cursor.execute('''
        DELETE FROM media_group_photos
        WHERE media_group_id = ?
    ''', (media_group_id,))
    conn.commit()
    conn.close()
    
    logger.info(f"Cleaned up media group {media_group_id}")

def cleanup_old_media_group_photos(max_age_hours: int = 24):
    """Clean up media group photos older than max_age_hours"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Find old media groups
    cursor.execute('''
        SELECT DISTINCT media_group_id FROM media_group_photos
        WHERE created_at < datetime('now', ? || ' hours')
    ''', (f'-{max_age_hours}',))
    old_groups = cursor.fetchall()
    conn.close()
    
    # Delete each old group
    for (media_group_id,) in old_groups:
        delete_media_group_photos(media_group_id)
    
    if old_groups:
        logger.info(f"Cleaned up {len(old_groups)} old media groups (older than {max_age_hours} hours)")

# ============================================================================
# SALE RECEIPT OCR STORAGE FUNCTIONS
# ============================================================================

def save_sale_receipt_ocr(message_id: int, receipt_index: int, transaction_type: str, 
                          detected_amount: float, detected_bank: str = None, 
                          detected_usdt: float = None, media_group_id: str = None,
                          ocr_raw_data: dict = None):
    """Save OCR result for a sale receipt to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    raw_data_json = json.dumps(ocr_raw_data) if ocr_raw_data else None
    
    cursor.execute('''
        INSERT OR REPLACE INTO sale_receipt_ocr 
        (message_id, media_group_id, receipt_index, transaction_type, 
         detected_amount, detected_bank, detected_usdt, ocr_raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (message_id, media_group_id, receipt_index, transaction_type,
          detected_amount, detected_bank, detected_usdt, raw_data_json))
    conn.commit()
    conn.close()
    
    logger.info(f"Saved sale receipt OCR: msg_id={message_id}, idx={receipt_index}, "
                f"type={transaction_type}, amount={detected_amount}, bank={detected_bank}")

def get_sale_receipt_ocr(message_id: int) -> list:
    """Get all OCR results for a sale message (supports multiple receipts)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message_id, media_group_id, receipt_index, transaction_type,
               detected_amount, detected_bank, detected_usdt, ocr_raw_data
        FROM sale_receipt_ocr
        WHERE message_id = ?
        ORDER BY receipt_index
    ''', (message_id,))
    results = cursor.fetchall()
    conn.close()
    
    ocr_results = []
    for row in results:
        raw_data = json.loads(row[7]) if row[7] else None
        ocr_results.append({
            'message_id': row[0],
            'media_group_id': row[1],
            'receipt_index': row[2],
            'transaction_type': row[3],
            'detected_amount': row[4],
            'detected_bank': row[5],
            'detected_usdt': row[6],
            'ocr_raw_data': raw_data
        })
    
    return ocr_results

def get_sale_receipt_ocr_by_media_group(media_group_id: str) -> list:
    """Get all OCR results for a media group"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message_id, media_group_id, receipt_index, transaction_type,
               detected_amount, detected_bank, detected_usdt, ocr_raw_data
        FROM sale_receipt_ocr
        WHERE media_group_id = ?
        ORDER BY receipt_index
    ''', (media_group_id,))
    results = cursor.fetchall()
    conn.close()
    
    ocr_results = []
    for row in results:
        raw_data = json.loads(row[7]) if row[7] else None
        ocr_results.append({
            'message_id': row[0],
            'media_group_id': row[1],
            'receipt_index': row[2],
            'transaction_type': row[3],
            'detected_amount': row[4],
            'detected_bank': row[5],
            'detected_usdt': row[6],
            'ocr_raw_data': raw_data
        })
    
    return ocr_results

def delete_sale_receipt_ocr(message_id: int):
    """Delete OCR results for a sale message"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM sale_receipt_ocr
        WHERE message_id = ?
    ''', (message_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        logger.info(f"Deleted {deleted} sale receipt OCR record(s) for message {message_id}")

def delete_sale_receipt_ocr_by_media_group(media_group_id: str):
    """Delete OCR results for a media group"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM sale_receipt_ocr
        WHERE media_group_id = ?
    ''', (media_group_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        logger.info(f"Deleted {deleted} sale receipt OCR record(s) for media group {media_group_id}")

def cleanup_old_sale_receipt_ocr(max_age_hours: int = 48):
    """Clean up old sale receipt OCR data"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM sale_receipt_ocr
        WHERE created_at < datetime('now', ? || ' hours')
    ''', (f'-{max_age_hours}',))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old sale receipt OCR records (older than {max_age_hours} hours)")

def normalize_bank_name(bank_name):
    """Normalize bank name for case-insensitive comparison (removes spaces, converts to lowercase)
    
    Examples:
        'MMN(Swift)' -> 'mmn(swift)'
        'mmn ( swift )' -> 'mmn(swift)'
        'MMN ( BINANCE)' -> 'mmn(binance)'
    """
    if not bank_name:
        return ""
    # Remove all spaces and convert to lowercase
    return bank_name.replace(" ", "").lower()

def banks_match(bank_name1, bank_name2):
    """Check if two bank names match (case-insensitive, space-insensitive)"""
    return normalize_bank_name(bank_name1) == normalize_bank_name(bank_name2)

def get_user_prefix(user_id):
    """Get prefix name for a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT prefix_name FROM user_prefixes WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_user_prefix(user_id, prefix_name, username=None):
    """Set prefix name for a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_prefixes (user_id, prefix_name, username)
        VALUES (?, ?, ?)
    ''', (user_id, prefix_name, username))
    conn.commit()
    conn.close()
    logger.info(f"✅ Set prefix '{prefix_name}' for user {user_id} (@{username})")

def get_all_user_prefixes():
    """Get all user-prefix mappings"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, prefix_name, username FROM user_prefixes ORDER BY prefix_name')
    results = cursor.fetchall()
    conn.close()
    return [{'user_id': r[0], 'prefix_name': r[1], 'username': r[2]} for r in results]

def get_receiving_usdt_account():
    """Get the receiving USDT account for buy transactions"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('receiving_usdt_account',))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'ACT(Wallet)'

def set_receiving_usdt_account(account_name):
    """Set the receiving USDT account for buy transactions"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES ('receiving_usdt_account', ?, CURRENT_TIMESTAMP)
    ''', (account_name,))
    conn.commit()
    conn.close()
    logger.info(f"✅ Set receiving USDT account to '{account_name}'")

def set_mmk_bank_account(bank_name, account_number, account_holder):
    """Set MMK bank account details for verification"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO mmk_bank_accounts (bank_name, account_number, account_holder, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (bank_name, account_number, account_holder))
    conn.commit()
    conn.close()
    logger.info(f"✅ Set MMK bank account: {bank_name} - {account_holder} ({account_number})")

def get_mmk_bank_account(bank_name):
    """Get MMK bank account details"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT account_number, account_holder FROM mmk_bank_accounts WHERE bank_name = ?', (bank_name,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'account_number': result[0], 'account_holder': result[1]}
    return None

def get_all_mmk_bank_accounts():
    """Get all MMK bank accounts"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT bank_name, account_number, account_holder FROM mmk_bank_accounts ORDER BY bank_name')
    results = cursor.fetchall()
    conn.close()
    return [{'bank_name': r[0], 'account_number': r[1], 'account_holder': r[2]} for r in results]

async def send_alert(message, alert_text, context):
    """Send alert message (error/warning) to alert topic if configured, otherwise reply to message
    
    Args:
        message: The original message object
        alert_text: The alert text to send
        context: The context object for sending messages
    """
    if ALERT_TOPIC_ID:
        # Send to alert topic
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=ALERT_TOPIC_ID,
            text=alert_text
        )
    else:
        # Send as reply to original message
        await message.reply_text(alert_text)

async def send_command_response(context, response_text, parse_mode=None):
    """Send command response to alert topic
    
    Args:
        context: The context object for sending messages
        response_text: The response text to send
        parse_mode: Optional parse mode (HTML, Markdown, etc.)
    """
    if ALERT_TOPIC_ID:
        # Send to alert topic
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=ALERT_TOPIC_ID,
            text=response_text,
            parse_mode=parse_mode
        )
    else:
        # Fallback: send to general chat (shouldn't happen if ALERT_TOPIC_ID is configured)
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=response_text,
            parse_mode=parse_mode
        )

async def send_status_message(context, status_text, parse_mode=None):
    """Send status message (success/processing/info) to alert topic
    
    Args:
        context: The context object for sending messages
        status_text: The status text to send
        parse_mode: Optional parse mode (HTML, Markdown, etc.)
    """
    if ALERT_TOPIC_ID:
        # Send to alert topic
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=ALERT_TOPIC_ID,
            text=status_text,
            parse_mode=parse_mode
        )
    else:
        # Fallback: send to general chat (shouldn't happen if ALERT_TOPIC_ID is configured)
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=status_text,
            parse_mode=parse_mode
        )

# Storage for tracking multiple photo replies to same transaction
# Format: {original_message_id: {'amounts': [amount1, amount2], 'bank': bank_obj, 'expected': amount, 'type': 'buy/sell'}}
pending_transactions = {}

# Storage for media groups (bulk photos sent together by staff)
# Format: {media_group_id: {'photos': [photo1, photo2], 'message': message_obj, 'original_text': text}}
media_groups = {}
media_group_locks = {}  # Track which media groups are being processed

# ============================================================================
# BALANCE PARSING & FORMATTING
# ============================================================================

def parse_balance_message(message_text):
    """Parse new balance format with staff prefixes:
    San(Kpay P) -2639565
    San(CB M) -0
    San(KBZ)-11044185
    ...
    USDT
    San(Swift) -81.99
    THB
    ACT(Bkk B) -13223
    
    Also handles single-line format without line breaks
    """
    try:
        text = message_text.strip()
        
        # Remove "MMK" prefix if present at the start
        if text.startswith('MMK'):
            text = text[3:]
        
        # Find currency sections
        usdt_start = text.find('USDT')
        thb_start = text.find('THB')
        
        if usdt_start == -1:
            logger.error("Missing USDT marker")
            return None
        
        # Determine section boundaries
        mmk_section = text[:usdt_start]
        
        if thb_start != -1 and thb_start > usdt_start:
            # THB section exists after USDT
            usdt_section = text[usdt_start + 4:thb_start]
            thb_section = text[thb_start + 3:]
        else:
            # No THB section
            usdt_section = text[usdt_start + 4:]
            thb_section = ""
        
        # Pattern matches: San(KBZ)-11044185 or TZT (Binance)-(222.6) or NDT (Wave) -2864900
        # Updated to handle amounts with extra info like: NDT(Binance)-6.96(52.96)
        bank_pattern = r'([A-Za-z\s]+?)\s*\(([^)]+)\)\s*-\s*\(?([\d,]+(?:\.\d+)?)\)?(?:\([^)]+\))?'
        
        # Parse MMK banks
        banks = []
        for match in re.finditer(bank_pattern, mmk_section):
            prefix = match.group(1).strip()
            bank_name = match.group(2).strip()
            amount_str = match.group(3).replace(',', '')
            
            try:
                amount = float(amount_str)
                full_name = f"{prefix}({bank_name})"
                banks.append({'bank_name': full_name, 'amount': amount, 'prefix': prefix, 'bank': bank_name})
            except ValueError:
                logger.warning(f"Could not parse amount for {prefix}({bank_name}): {amount_str}")
                continue
        
        # Parse USDT banks
        usdt_banks = []
        for match in re.finditer(bank_pattern, usdt_section):
            prefix = match.group(1).strip()
            bank_name = match.group(2).strip()
            amount_str = match.group(3).replace(',', '')
            
            try:
                amount = float(amount_str)
                full_name = f"{prefix}({bank_name})"
                usdt_banks.append({'bank_name': full_name, 'amount': amount, 'prefix': prefix, 'bank': bank_name})
            except ValueError:
                logger.warning(f"Could not parse USDT amount for {prefix}({bank_name}): {amount_str}")
                continue
        
        # Parse THB banks
        thb_banks = []
        if thb_section:
            for match in re.finditer(bank_pattern, thb_section):
                prefix = match.group(1).strip()
                bank_name = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')
                
                try:
                    amount = float(amount_str)
                    full_name = f"{prefix}({bank_name})"
                    thb_banks.append({'bank_name': full_name, 'amount': amount, 'prefix': prefix, 'bank': bank_name})
                except ValueError:
                    logger.warning(f"Could not parse THB amount for {prefix}({bank_name}): {amount_str}")
                    continue
        
        logger.info(f"Parsed {len(banks)} MMK banks, {len(usdt_banks)} USDT banks, {len(thb_banks)} THB banks")
        
        # Log parsed banks for debugging
        if banks:
            logger.info(f"MMK banks: {[b['bank_name'] for b in banks]}")
        if usdt_banks:
            logger.info(f"USDT banks: {[b['bank_name'] for b in usdt_banks]}")
        if thb_banks:
            logger.info(f"THB banks: {[b['bank_name'] for b in thb_banks]}")
        
        return {'mmk_banks': banks, 'usdt_banks': usdt_banks, 'thb_banks': thb_banks}
    
    except Exception as e:
        logger.error(f"Parse error: {e}")

        logger.error(traceback.format_exc())
        return None

def format_balance_message(mmk_banks, usdt_banks, thb_banks=None):
    """Format balance with staff prefixes:
    San(Kpay P) -2639565
    San(KBZ) -11044185
    ...
    USDT
    San(Swift) -81.99
    THB
    ACT(Bkk B) -13223
    
    Note: The hyphen (-) is a separator, not a minus sign
    """
    message = ""
    for bank in mmk_banks:
        # Format with hyphen separator
        formatted = f"{abs(int(bank['amount'])):,}"
        message += f"{bank['bank_name']} -{formatted}\n"
    
    message += "\nUSDT\n"
    for bank in usdt_banks:
        # Format USDT with 4 decimal places and hyphen separator
        formatted = f"{abs(bank['amount']):.4f}"
        message += f"{bank['bank_name']} -{formatted}\n"
    
    # Add THB section if there are THB banks
    if thb_banks:
        message += "\nTHB\n"
        for bank in thb_banks:
            # Format THB with no decimal places (integer) and hyphen separator
            formatted = f"{abs(int(bank['amount'])):,}"
            message += f"{bank['bank_name']} -{formatted}\n"
    
    return message.strip()

# ============================================================================
# OCR FUNCTIONS
# ============================================================================

async def ocr_detect_mmk_bank_and_amount(image_base64, mmk_banks, user_prefix=None):
    """Detect MMK bank and amount from receipt, optionally filtering by user prefix"""
    try:
        # Filter banks by user prefix if provided
        if user_prefix:
            filtered_banks = [b for b in mmk_banks if b.get('prefix') == user_prefix]
            if not filtered_banks:
                logger.warning(f"No banks found for prefix '{user_prefix}'")
                filtered_banks = mmk_banks
        else:
            filtered_banks = mmk_banks
        
        bank_list = ", ".join([f"{i+1}. {b['bank_name']}" for i, b in enumerate(filtered_banks)])
        
        prompt = f"""Analyze this MMK payment receipt carefully.

Available banks:
{bank_list}

Extract:
1. Transaction amount (integer, no decimals, positive number only)
2. Bank number (1-{len(filtered_banks)})

CRITICAL - Bank Recognition Guide:
1. Kpay P: RED/CORAL color with "Payment Successful"
2. CB M: Blue "Account History" with "CB BANK" logo (Mobile)
3. CB: Rainbow "CB BANK" logo (Regular)
4. KBZ: "INTERNAL TRANSFER - CONFIRM" with green banner
5. AYA M: "AYA PAY" mobile app interface
6. AYA: "Payment Complete" OR "AYA PAY" logo (Regular)
7. AYA Wallet: "AYA Wallet" branding
8. Wave: YELLOW header with "Wave Money" logo (Regular Wave)
9. Wave M: Wave mobile app with "Wave Money" (Mobile)
10. Wave Channel: Green "Successful" with "Cash In" text and phone number display (Agent/Channel)
11. Yoma: "Flexi Everyday Account" text

IMPORTANT: 
- "Wave Channel" shows "Cash In" with green checkmark and recipient phone number
- "Wave" shows yellow header with Wave Money logo
- "Wave M" shows Wave mobile app interface
- These are THREE DIFFERENT accounts - do not confuse them!

Return JSON:
{{"amount": <integer>, "bank_number": <1-{len(filtered_banks)}>}}

CRITICAL NOTES:
1. Return amount as positive number, ignore any minus signs in the receipt
2. If you see "Cash In" with green checkmark and phone number → This is "Wave Channel" (NOT "Wave" or "Wave M")
3. Match the bank name EXACTLY as shown in the available banks list
4. Wave, Wave M, and Wave Channel are THREE DIFFERENT accounts"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_base64}}
                ]
            }],
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*|\s*```', '', result)
        
        json_start = result.find('{')
        json_end = result.rfind('}')
        if json_start != -1 and json_end != -1:
            result = result[json_start:json_end + 1]
        
        data = json.loads(result)
        # Use absolute value to ensure positive amount
        amount = abs(float(data['amount']))
        bank_idx = int(data['bank_number']) - 1
        
        if 0 <= bank_idx < len(filtered_banks):
            return {'amount': amount, 'bank': filtered_banks[bank_idx]}
        
        return None
    
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return None

async def ocr_extract_usdt_amount(image_base64):
    """Extract USDT amount from receipt (legacy function for backward compatibility)"""
    result = await ocr_extract_usdt_with_fee(image_base64)
    if result:
        return result['total_amount']
    return None

async def ocr_extract_usdt_with_fee(image_base64):
    """Extract USDT amount, network fee, and bank type from receipt
    
    Returns:
        {
            'amount': <transaction amount>,
            'network_fee': <network fee>,
            'total_amount': <final amount to use for balance>,
            'bank_type': 'swift', 'wallet', or 'binance'
        }
    """
    try:
        prompt = """Analyze this USDT transfer receipt carefully.

TASK:
1. Identify the receipt type:
   - Binance: Shows "Withdrawal Details" title, dark theme, shows network fee separately at bottom
   - Swift: Shows "USDT Sent" title, dark theme, network fee in BNB
   - Wallet: Shows different interface (Trust Wallet, MetaMask, etc.)

2. Extract the main transaction amount (the USDT sent/withdrawn, as positive number)

3. Extract the network fee (if shown separately)

4. Calculate total_amount based on receipt type:
   - Binance: Use the displayed amount AS-IS (Binance already includes fee in the amount)
   - Swift/Wallet: total = amount + network_fee (need to add fee manually)

RETURN EXACT JSON FORMAT:
{
    "amount": <transaction amount as positive number>,
    "network_fee": <network fee if shown, 0 if not>,
    "total_amount": <final amount to use>,
    "bank_type": "binance" or "swift" or "wallet"
}

EXAMPLES:

1. Binance Withdrawal Receipt:
   Shows: "-47.84175 USDT" and "Network fee: 0.01 USDT"
   Return: {"amount": 47.84175, "network_fee": 0.01, "total_amount": 47.84175, "bank_type": "binance"}
   Note: total_amount = amount (Binance already includes fee in displayed amount)

2. Swift Receipt:
   Shows: "-24.813896 USDT" and "Network fee (0.12 $)"
   Return: {"amount": 24.813896, "network_fee": 0.12, "total_amount": 24.933896, "bank_type": "swift"}
   Note: total_amount = amount + network_fee (need to add fee)

3. Wallet Receipt:
   Shows: "25.5 USDT" with no network fee
   Return: {"amount": 25.5, "network_fee": 0, "total_amount": 25.5, "bank_type": "wallet"}

CRITICAL RULES:
- For Binance: total_amount = amount (DO NOT add network_fee, it's already included)
- For Swift/Wallet: total_amount = amount + network_fee (need to add it)
- Always return amounts as positive numbers
- bank_type must be "binance", "swift", or "wallet" (lowercase)"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_base64}}
                ]
            }],
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"USDT OCR raw response: {result[:200]}...")
        
        result = re.sub(r'```json\s*|\s*```', '', result)
        
        json_start = result.find('{')
        json_end = result.rfind('}')
        if json_start != -1 and json_end != -1:
            result = result[json_start:json_end + 1]
        else:
            logger.warning(f"No JSON found in USDT OCR response: {result}")
            return None
        
        if not result or result == '':
            logger.warning("Empty result after JSON extraction")
            return None
        
        data = json.loads(result)
        
        # Ensure all values are positive and properly formatted
        amount = abs(float(data.get('amount', 0)))
        network_fee = abs(float(data.get('network_fee', 0)))
        bank_type = data.get('bank_type', 'wallet')
        
        # Handle None or invalid bank_type
        if bank_type is None or not isinstance(bank_type, str):
            bank_type = 'wallet'
        else:
            bank_type = bank_type.lower()
        
        # Validate bank_type
        if bank_type not in ['swift', 'wallet', 'binance']:
            bank_type = 'wallet'
        
        # Calculate total_amount based on bank type
        if bank_type == 'binance':
            # Binance already includes fee in the displayed amount
            total_amount = amount
        else:
            # Swift/Wallet need to add network fee
            total_amount = amount + network_fee
        
        # Override with provided total_amount if it makes sense
        provided_total = abs(float(data.get('total_amount', total_amount)))
        if provided_total > 0:
            total_amount = provided_total
        
        result_data = {
            'amount': amount,
            'network_fee': network_fee,
            'total_amount': total_amount,
            'bank_type': bank_type
        }
        
        logger.info(f"USDT OCR: {result_data}")
        return result_data
    
    except Exception as e:
        logger.error(f"USDT OCR error: {e}")

        logger.error(traceback.format_exc())
        return None

async def ocr_extract_usdt_received(image_base64):
    """Extract USDT RECEIVED amount from customer's receipt (for BUY transactions)
    
    This function detects only the amount we will RECEIVE, not including network fee.
    Network fee is paid by customer, not relevant to our balance.
    
    For example:
    - Receipt shows: 1415 USDT (amount) + 2 USDT (fee) = 1417 total
    - We only care about 1415 USDT (what we receive)
    
    Returns:
        {
            'received_amount': <amount we receive>,
            'network_fee': <fee paid by customer>,
            'bank_type': 'binance', 'swift', or 'wallet'
        }
    """
    try:
        prompt = """Analyze this USDT transfer/withdrawal receipt.

TASK: Extract the USDT amount that will be RECEIVED (not the total sent).

IMPORTANT:
- Look for the main transaction amount (提币数量/币种, Amount, Withdrawal Amount)
- This is the amount RECEIVED, NOT including network fee
- Network fee (手续费) is separate and paid by sender

EXAMPLES:
1. Chinese Binance receipt shows:
   - 提币数量/币种: 1415 USDT (this is what we receive)
   - 手续费: 2 USDT (network fee, ignore this)
   → Return received_amount: 1415

2. English receipt shows:
   - Amount: 100 USDT
   - Network Fee: 1 USDT
   → Return received_amount: 100

3. Swift/Wallet receipt shows:
   - Sent: 50.5 USDT
   - Fee: 0.5 USDT
   → Return received_amount: 50.5

RETURN JSON FORMAT:
{
    "received_amount": <amount that will be received, NOT including fee>,
    "network_fee": <network fee if shown, 0 if not>,
    "bank_type": "binance" or "swift" or "wallet"
}

CRITICAL: received_amount should be the amount BEFORE fee is added, the actual amount received."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_base64}}
                ]
            }],
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"USDT Received OCR raw response: {result[:200]}...")
        
        # Extract JSON from response
        result = re.sub(r'```json\s*|\s*```', '', result)
        
        json_start = result.find('{')
        json_end = result.rfind('}')
        if json_start != -1 and json_end != -1:
            result = result[json_start:json_end + 1]
        else:
            logger.warning(f"No JSON found in USDT Received OCR response: {result}")
            return None
        
        if not result or result == '':
            logger.warning("Empty result after JSON extraction")
            return None
        
        data = json.loads(result)
        
        received_amount = abs(float(data.get('received_amount', 0)))
        network_fee = abs(float(data.get('network_fee', 0)))
        bank_type = data.get('bank_type', 'wallet')
        
        if bank_type is None or not isinstance(bank_type, str):
            bank_type = 'wallet'
        else:
            bank_type = bank_type.lower()
        
        if bank_type not in ['swift', 'wallet', 'binance']:
            bank_type = 'wallet'
        
        result_data = {
            'received_amount': received_amount,
            'network_fee': network_fee,
            'bank_type': bank_type
        }
        
        logger.info(f"USDT Received OCR: {result_data}")
        return result_data
    
    except Exception as e:
        logger.error(f"USDT Received OCR error: {e}")

        logger.error(traceback.format_exc())
        return None

async def ocr_match_mmk_receipt_to_banks(image_base64, mmk_banks_list):
    """Match MMK receipt to registered banks with confidence scores
    
    Args:
        image_base64: Base64 encoded receipt image
        mmk_banks_list: List of dicts with 'bank_id', 'bank_name', 'account_number', 'account_holder'
    
    Returns:
        {
            "amount": 23000,
            "banks": {
                1: 100,  # bank_id: confidence (0-100)
                2: 0,
                3: 0
            }
        }
    """
    try:
        # Build bank list for prompt
        bank_info_list = []
        for bank in mmk_banks_list:
            bank_id = bank['bank_id']
            bank_name = bank['bank_name']
            account = bank['account_number']
            holder = bank['account_holder']
            last_4 = account[-4:] if len(account) >= 4 else account
            
            bank_info_list.append(
                f"Bank ID {bank_id}: {bank_name}\n"
                f"  Account ends in: {last_4}\n"
                f"  Holder: {holder}"
            )
        
        banks_text = "\n\n".join(bank_info_list)
        
        prompt = f"""Analyze this MMK payment receipt and match it to the correct bank account.

REGISTERED BANK ACCOUNTS:
{banks_text}

TASK:
1. Extract the transaction amount (positive number, ignore minus signs)
2. Extract recipient account/phone number (may be partially masked: xxxx, *****)
3. Extract recipient name
4. For EACH bank, calculate confidence score (0-100) based on:
   - Account number match (last 4 digits): 50 points
   - Name match (case-insensitive, partial OK): 50 points
   - Total: 100 points if both match perfectly

RETURN EXACT JSON FORMAT:
{{
    "amount": <number>,
    "banks": {{
        1: <confidence 0-100>,
        2: <confidence 0-100>,
        3: <confidence 0-100>
    }}
}}

MATCHING RULES:
- For partial account "xxxx-xxxx-xxxx-2957", check if "2957" matches last 4 digits
- For partial phone "******3777", check if "3777" matches last 4 digits
- For name "CHAW SU THU ZAR", match against registered holder name (case-insensitive)
- Give 50 points for account match, 50 points for name match
- If no match at all, give 0 points

IMPORTANT:
- Return confidence for ALL banks in the list
- Amount must be positive number
- Confidence must be 0-100 for each bank
- Use bank IDs exactly as provided
- DO NOT include comments in JSON
- DO NOT use trailing commas"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_base64}}
                ]
            }],
            max_tokens=400
        )
        
        result = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks
        result = re.sub(r'```json\s*|\s*```', '', result)
        
        # Extract JSON object
        json_start = result.find('{')
        json_end = result.rfind('}')
        if json_start != -1 and json_end != -1:
            result = result[json_start:json_end + 1]
        
        # Remove comments (// and /* */)
        result = re.sub(r'//.*?$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
        
        # Remove trailing commas before closing braces/brackets
        result = re.sub(r',(\s*[}\]])', r'\1', result)
        
        # Fix unquoted numeric keys in JSON (e.g., {1: 100} -> {"1": 100})
        # This handles the "banks" object where keys are bank IDs
        result = re.sub(r'(\{|,)\s*(\d+)\s*:', r'\1"\2":', result)
        
        # Log the cleaned JSON for debugging
        logger.info(f"Cleaned JSON for parsing: {result[:200]}...")
        
        data = json.loads(result)
        
        # Ensure amount is positive
        data['amount'] = abs(float(data.get('amount', 0)))
        
        # Ensure all banks have confidence scores
        banks_confidence = data.get('banks', {})
        for bank in mmk_banks_list:
            bank_id = str(bank['bank_id'])
            if bank_id not in banks_confidence:
                banks_confidence[bank_id] = 0
        
        data['banks'] = banks_confidence
        
        # Log results
        logger.info(f"OCR Amount: {data['amount']}")
        for bank_id, confidence in banks_confidence.items():
            logger.info(f"  Bank ID {bank_id}: {confidence}% confidence")
        
        return data
    
    except Exception as e:
        logger.error(f"OCR bank matching error: {e}")

        logger.error(traceback.format_exc())
        return None

# ============================================================================
# TRANSACTION PROCESSING
# ============================================================================

def extract_transaction_info(text):
    """Extract Buy/Sell, USDT amount, MMK amount from message
    
    Also detects P2P Sell format: sell 13000000/3222.6=4034.00981 fee-6.44
    """
    # Check for P2P sell format (contains 'fee-' in the message)
    if 'fee-' in text.lower() or 'fee -' in text.lower():
        # P2P Sell format: sell 13000000/3222.6=4034.00981 fee-6.44
        # Pattern: sell MMK/USDT=RATE fee-FEE
        p2p_pattern = r'sell\s+([\d,]+(?:\.\d+)?)\s*/\s*([\d.]+)\s*=\s*([\d.]+)\s+fee\s*-?\s*([\d.]+)'
        match = re.search(p2p_pattern, text, re.IGNORECASE)
        
        if match:
            mmk_amount = float(match.group(1).replace(',', ''))
            usdt_amount = float(match.group(2))
            rate = float(match.group(3))
            fee = float(match.group(4))
            
            return {
                'type': 'p2p_sell',
                'mmk': mmk_amount,
                'usdt': usdt_amount,
                'rate': rate,
                'fee': fee,
                'total_usdt': usdt_amount + fee
            }
    
    # Regular Buy/Sell format
    tx_type = 'buy' if 'Buy' in text else ('sell' if 'Sell' in text else None)
    
    usdt_match = re.search(r'(Buy|Sell)\s+([\d.]+)', text)
    usdt_amount = float(usdt_match.group(2)) if usdt_match else None
    
    mmk_match = re.search(r'=\s*([\d,]+\.?\d*)', text)
    mmk_amount = float(mmk_match.group(1).replace(',', '')) if mmk_match else None
    
    return {'type': tx_type, 'usdt': usdt_amount, 'mmk': mmk_amount}

async def process_buy_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict):
    """BUY: Customer buys USDT from us, we send MMK to customer
    
    BUY FLOW:
    - Sale message contains USDT receipt from customer (showing they sent USDT to us)
    - Staff reply contains MMK receipt (showing we sent MMK to customer)
    
    When staff sends sale message with USDT receipt:
    - OCR the USDT receipt to detect amount
    - Store for later verification
    
    When staff sends MMK receipt as reply:
    - OCR the MMK receipt to detect amount and bank
    - Update balances
    """
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded. Post balance message in auto balance topic first.", context)
        return
    
    if not message.photo:
        await send_alert(message, "❌ No receipt photo", context)
        return
    
    # Get staff prefix
    user_id = message.from_user.id
    user_prefix = get_user_prefix(user_id)
    
    if not user_prefix:
        await send_alert(message, "❌ You don't have a prefix set. Admin needs to use /set_user command.", context)
        return
    
    # Get original message
    original_message = message.reply_to_message
    original_message_id = original_message.message_id if original_message else message.message_id
    
    # Determine if this is the sale message or staff reply
    # If original message has no photo, this is the sale message (USDT receipt)
    # If original message has photo, this is staff reply (MMK receipt)
    original_has_photo = original_message and original_message.photo
    
    if not original_has_photo:
        # CASE 1: This is the SALE MESSAGE with USDT receipt from customer
        logger.info(f"Buy: Processing as SALE MESSAGE - photo is USDT receipt from customer")
        
        # Get photo and OCR as USDT receipt
        photo = message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # OCR USDT receipt - detect RECEIVED amount (not including network fee)
        usdt_result = await ocr_extract_usdt_received(photo_base64)
        
        detected_usdt = tx_info['usdt']  # Default to message amount
        
        if usdt_result and usdt_result['received_amount'] > 0:
            detected_usdt = usdt_result['received_amount']
            logger.info(f"Detected USDT RECEIVED from customer receipt: {detected_usdt:.4f} (fee: {usdt_result['network_fee']:.4f} paid by customer)")
            
            # Check for mismatch
            if tx_info['usdt'] and tx_info['usdt'] > 0:
                if abs(detected_usdt - tx_info['usdt']) > max(0.5, tx_info['usdt'] * 0.01):
                    await send_status_message(
                        context,
                        f"⚠️ <b>USDT Amount Mismatch Warning</b>\n\n"
                        f"<b>Transaction:</b> Buy\n"
                        f"<b>Staff:</b> {user_prefix}\n"
                        f"<b>Expected (from message):</b> {tx_info['usdt']:.4f} USDT\n"
                        f"<b>Detected (from OCR):</b> {detected_usdt:.4f} USDT\n"
                        f"<b>Difference:</b> {abs(detected_usdt - tx_info['usdt']):.4f} USDT",
                        parse_mode='HTML'
                    )
        else:
            logger.warning(f"Could not OCR USDT receipt, using message amount: {tx_info['usdt']:.4f}")
        
        # Store the sale message info for later when staff sends MMK receipt
        sale_message_id = message.message_id
        
        pending_transactions[sale_message_id] = {
            'type': 'buy',
            'detected_usdt': detected_usdt,
            'expected_mmk': tx_info['mmk'],
            'expected_usdt': tx_info['usdt'],
            'user_prefix': user_prefix
        }
        
        # Save to database for persistence
        save_sale_receipt_ocr(
            message_id=sale_message_id,
            media_group_id=message.media_group_id,
            receipt_index=0,
            transaction_type='buy',
            detected_amount=None,
            detected_bank=None,
            detected_usdt=detected_usdt,
            ocr_raw_data=None
        )
        
        # Send notification
        await send_status_message(
            context,
            f"📥 <b>Buy Transaction - USDT Receipt Processed</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>USDT Detected:</b> {detected_usdt:.4f}\n"
            f"<b>Expected MMK:</b> {tx_info['mmk']:,.0f}\n\n"
            f"⏳ Waiting for staff to send MMK receipt...",
            parse_mode='HTML'
        )
        
        logger.info(f"Buy transaction {sale_message_id} stored - waiting for MMK receipt")
        return
    
    else:
        # CASE 2: This is STAFF REPLY with MMK receipt
        logger.info(f"Buy: Processing as STAFF REPLY - photo is MMK receipt")
        
        # Get photo and OCR as MMK receipt
        photo = message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # OCR MMK receipt
        result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
        
        if not result:
            await send_alert(message, "❌ Could not detect bank/amount from MMK receipt", context)
            return
        
        detected_mmk = result['amount']
        detected_bank = result['bank']
        
        # Check if staff reply contains fee (format: fee-3039)
        staff_reply_text = message.text or message.caption or ""
        mmk_fee = 0
        fee_match = re.search(r'fee\s*-\s*([\d,]+(?:\.\d+)?)', staff_reply_text, re.IGNORECASE)
        if fee_match:
            mmk_fee = float(fee_match.group(1).replace(',', ''))
            logger.info(f"Detected MMK fee in staff reply: {mmk_fee:,.0f} MMK")
        
        total_mmk = detected_mmk + mmk_fee
        
        logger.info(f"Buy: Detected {total_mmk:,.0f} MMK from {detected_bank['bank_name']}")
        
        # Get USDT amount from original message (sale message)
        # First check if we have stored OCR data
        stored_ocr = get_sale_receipt_ocr(original_message_id)
        detected_usdt = tx_info['usdt']  # Default
        
        if stored_ocr and stored_ocr[0].get('detected_usdt'):
            detected_usdt = stored_ocr[0]['detected_usdt']
            logger.info(f"Using pre-scanned USDT: {detected_usdt:.4f}")
            delete_sale_receipt_ocr(original_message_id)
        elif original_message.photo:
            # OCR the original USDT receipt - detect RECEIVED amount
            orig_photo = original_message.photo[-1]
            orig_file = await context.bot.get_file(orig_photo.file_id)
            orig_bytes = await orig_file.download_as_bytearray()
            orig_base64 = base64.b64encode(orig_bytes).decode('utf-8')
            
            usdt_result = await ocr_extract_usdt_received(orig_base64)
            if usdt_result and usdt_result['received_amount'] > 0:
                detected_usdt = usdt_result['received_amount']
                logger.info(f"Detected USDT RECEIVED from original receipt: {detected_usdt:.4f}")
        
        # Verify MMK amount
        if tx_info['mmk'] > 0 and abs(total_mmk - tx_info['mmk']) > max(1000, tx_info['mmk'] * 0.1):
            await send_status_message(
                context,
                f"⚠️ <b>MMK Amount Mismatch Warning</b>\n\n"
                f"<b>Transaction:</b> Buy\n"
                f"<b>Staff:</b> {user_prefix}\n"
                f"<b>Expected (from message):</b> {tx_info['mmk']:,.0f} MMK\n"
                f"<b>Detected (from OCR):</b> {total_mmk:,.0f} MMK\n"
                f"<b>Difference:</b> {abs(total_mmk - tx_info['mmk']):,.0f} MMK",
                parse_mode='HTML'
            )
        
        # Check if sufficient MMK balance
        bank_found = False
        for bank in balances['mmk_banks']:
            if banks_match(bank['bank_name'], detected_bank['bank_name']):
                bank_found = True
                if bank['amount'] < total_mmk:
                    await send_alert(message, 
                        f"❌ Insufficient MMK balance!\n\n"
                        f"{bank['bank_name']}: {bank['amount']:,.0f} MMK\n"
                        f"Required: {total_mmk:,.0f} MMK", 
                        context)
                    return
                bank['amount'] -= total_mmk
                logger.info(f"Reduced {total_mmk:,.0f} MMK from {bank['bank_name']}")
                break
        
        if not bank_found:
            await send_alert(message, f"❌ Bank not found: {detected_bank['bank_name']}", context)
            return
        
        # Add USDT to receiving account
        receiving_usdt_account = get_receiving_usdt_account()
        usdt_updated = False
        
        for bank in balances['usdt_banks']:
            if banks_match(bank['bank_name'], receiving_usdt_account):
                bank['amount'] += detected_usdt
                usdt_updated = True
                logger.info(f"Added {detected_usdt:.4f} USDT to {receiving_usdt_account}")
                break
        
        if not usdt_updated:
            await send_alert(message, f"⚠️ USDT account '{receiving_usdt_account}' not found", context)
        
        # Send new balance
        new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
        
        if AUTO_BALANCE_TOPIC_ID:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                message_thread_id=AUTO_BALANCE_TOPIC_ID,
                text=new_balance
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                text=new_balance
            )
        
        context.chat_data['balances'] = balances
        
        # Send success message
        await send_status_message(
            context,
            f"✅ <b>Buy Transaction Processed</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>MMK:</b> -{total_mmk:,.0f} ({detected_bank['bank_name']})\n"
            f"<b>USDT:</b> +{detected_usdt:.4f} ({receiving_usdt_account})",
            parse_mode='HTML'
        )
        
async def process_sell_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict):
    """SELL: User sells USDT, we receive MMK (supports multiple receipts from media group)
    
    SELL FLOW:
    - Sale message contains MMK receipt(s) from customer
    - Staff reply contains USDT receipt(s) showing transfer to customer
    
    Case 1: Staff sends sale message with MMK receipts (no original message with photos)
    - OCR the MMK receipts to detect amount and bank
    - Store for later when staff sends USDT receipts
    
    Case 2: Staff sends USDT receipts as reply to sale message (original message has photos)
    - Fetch stored MMK OCR data or OCR original message
    - OCR current USDT receipts
    - Update balances
    """
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded", context)
        return
    
    # Get staff prefix
    user_id = message.from_user.id
    user_prefix = get_user_prefix(user_id)
    
    if not user_prefix:
        await send_alert(message, "❌ You don't have a prefix set. Admin needs to use /set_user command.", context)
        return
    
    # Determine if this is sale message or staff reply
    original_message = message.reply_to_message
    original_has_photo = original_message and original_message.photo
    current_has_photo = message.photo
    
    if not original_has_photo and current_has_photo:
        # CASE 1: This is the SALE MESSAGE with MMK receipts from customer
        logger.info(f"Sell: Processing as SALE MESSAGE - photo is MMK receipt from customer")
        
        # Get photo and OCR as MMK receipt
        photo = message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # OCR MMK receipt
        mmk_result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
        
        detected_mmk = 0
        detected_bank = None
        
        if mmk_result and mmk_result['amount']:
            detected_mmk = mmk_result['amount']
            detected_bank = mmk_result['bank']
            logger.info(f"Detected MMK from customer receipt: {detected_mmk:,.0f} from {detected_bank['bank_name'] if detected_bank else 'unknown'}")
            
            # Check for mismatch
            if tx_info['mmk'] and tx_info['mmk'] > 0:
                if abs(detected_mmk - tx_info['mmk']) > max(1000, tx_info['mmk'] * 0.1):
                    await send_status_message(
                        context,
                        f"⚠️ <b>MMK Amount Mismatch Warning</b>\n\n"
                        f"<b>Transaction:</b> Sell\n"
                        f"<b>Staff:</b> {user_prefix}\n"
                        f"<b>Expected (from message):</b> {tx_info['mmk']:,.0f} MMK\n"
                        f"<b>Detected (from OCR):</b> {detected_mmk:,.0f} MMK",
                        parse_mode='HTML'
                    )
        else:
            # Use message amount as fallback
            detected_mmk = tx_info['mmk'] if tx_info['mmk'] else 0
            logger.warning(f"Could not detect MMK from receipt, using message amount: {detected_mmk:,.0f}")
        
        if not detected_bank:
            await send_alert(message, "❌ Could not detect MMK bank from receipt", context)
            return
        
        # Store for later
        sale_message_id = message.message_id
        
        pending_transactions[sale_message_id] = {
            'type': 'sell',
            'detected_mmk': detected_mmk,
            'detected_bank': detected_bank,
            'expected_usdt': tx_info['usdt'],
            'user_prefix': user_prefix
        }
        
        # Save to database for persistence
        save_sale_receipt_ocr(
            message_id=sale_message_id,
            media_group_id=message.media_group_id,
            receipt_index=0,
            transaction_type='sell',
            detected_amount=detected_mmk,
            detected_bank=detected_bank['bank_name'] if detected_bank else None,
            detected_usdt=None,
            ocr_raw_data=None
        )
        
        # Send notification
        await send_status_message(
            context,
            f"📥 <b>Sell Transaction - MMK Receipt Processed</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>MMK Detected:</b> {detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
            f"<b>Expected USDT:</b> {tx_info['usdt']:.4f}\n\n"
            f"⏳ Waiting for staff to send USDT receipt...",
            parse_mode='HTML'
        )
        
        logger.info(f"Sell transaction {sale_message_id} stored - waiting for USDT receipt")
        return
    
    elif not current_has_photo:
        # No photos in current message
        await send_alert(message, "❌ No receipt photo attached", context)
        return
    
    # CASE 2: This is STAFF REPLY with USDT receipts (original has photos or we have stored data)
    logger.info(f"Sell: Processing as STAFF REPLY - photo is USDT receipt")
    
    original_message_id = original_message.message_id if original_message else message.message_id
    media_group_id = original_message.media_group_id if original_message else None
    media_group_id_to_cleanup = None
    
    # ============================================================================
    # CHECK FOR PRE-SCANNED OCR DATA
    # ============================================================================
    stored_ocr_data = []
    
    # First try to get OCR data by message_id
    stored_ocr_data = get_sale_receipt_ocr(original_message_id)
    
    # If not found and has media_group_id, try by media_group_id
    if not stored_ocr_data and media_group_id:
        stored_ocr_data = get_sale_receipt_ocr_by_media_group(media_group_id)
    
    total_detected_mmk = 0
    detected_bank = None
    receipt_count = 0
    
    if stored_ocr_data:
        # USE STORED OCR DATA - No need to OCR again!
        logger.info(f"✅ Using pre-scanned OCR data: {len(stored_ocr_data)} receipt(s)")
        
        for ocr_record in stored_ocr_data:
            if ocr_record['detected_amount']:
                total_detected_mmk += ocr_record['detected_amount']
                receipt_count += 1
                
                # Get bank from first record with bank info
                if not detected_bank and ocr_record['detected_bank']:
                    # Find the bank object in balances
                    for bank in balances['mmk_banks']:
                        if banks_match(bank['bank_name'], ocr_record['detected_bank']):
                            detected_bank = bank
                            break
                
                logger.info(f"Pre-scanned receipt: {ocr_record['detected_amount']:,.0f} MMK, bank={ocr_record['detected_bank']}")
        
        # Get media_group_id for cleanup
        if stored_ocr_data[0].get('media_group_id'):
            media_group_id_to_cleanup = stored_ocr_data[0]['media_group_id']
        
        # Clean up OCR data after use
        if media_group_id:
            delete_sale_receipt_ocr_by_media_group(media_group_id)
        else:
            delete_sale_receipt_ocr(original_message_id)
    
    else:
        # NO STORED OCR DATA - Fall back to OCR now
        logger.info(f"⚠️ No pre-scanned OCR data found - performing OCR now")
        
        # Check if original message is part of a media group (multiple receipts)
        photo_data_list = []  # List of (message_id, photo_bytes or file_path)
        
        # Check database for stored media group photos
        mg_id, stored_photos = get_media_group_by_message_id(original_message_id)
        
        if stored_photos and len(stored_photos) > 1:
            logger.info(f"Found {len(stored_photos)} photos in database for media group {mg_id}")
            photo_data_list = stored_photos
            media_group_id_to_cleanup = mg_id
        elif media_group_id:
            stored_photos = get_media_group_photos(media_group_id)
            
            if stored_photos and len(stored_photos) > 1:
                logger.info(f"Found {len(stored_photos)} photos in database for media group {media_group_id}")
                photo_data_list = stored_photos
                media_group_id_to_cleanup = media_group_id
            else:
                logger.warning(f"Media group {media_group_id} not found in database - using single photo")
        
        # If no stored photos found, use single photo from original message
        if not photo_data_list:
            logger.info(f"Processing single photo from original message")
            user_photo = original_message.photo[-1]
            user_file = await context.bot.get_file(user_photo.file_id)
            user_bytes = await user_file.download_as_bytearray()
            photo_data_list = [(original_message_id, bytes(user_bytes))]
        
        # OCR all user's receipts and sum amounts
        for idx, photo_data in enumerate(photo_data_list, 1):
            msg_id, data = photo_data
            logger.info(f"Processing MMK receipt {idx}/{len(photo_data_list)}")
            
            # Data can be either file_path (string) or bytes
            if isinstance(data, str):
                with open(data, 'rb') as f:
                    photo_bytes = f.read()
                user_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            else:
                user_base64 = base64.b64encode(data).decode('utf-8')
            
            user_result = await ocr_detect_mmk_bank_and_amount(user_base64, balances['mmk_banks'], user_prefix)
            
            if not user_result or not user_result['amount']:
                logger.warning(f"Could not process MMK receipt {idx}")
                continue
            
            receipt_mmk = user_result['amount']
            total_detected_mmk += receipt_mmk
            receipt_count += 1
            
            if not detected_bank and user_result['bank']:
                detected_bank = user_result['bank']
            
            logger.info(f"MMK receipt {idx}: {receipt_mmk:,.0f} MMK from {user_result['bank']['bank_name'] if user_result['bank'] else 'unknown'}")
    
    if receipt_count == 0 or not detected_bank:
        await send_alert(message, "❌ Could not detect bank/amount from user receipt(s)", context)
        if media_group_id_to_cleanup:
            delete_media_group_photos(media_group_id_to_cleanup)
        return
    
    logger.info(f"Total MMK from {receipt_count} receipt(s): {total_detected_mmk:,.0f} MMK")
    
    # Check if staff reply contains fee (format: fee-3039)
    staff_reply_text = message.text or message.caption or ""
    mmk_fee = 0
    fee_match = re.search(r'fee\s*-\s*([\d,]+(?:\.\d+)?)', staff_reply_text, re.IGNORECASE)
    if fee_match:
        mmk_fee = float(fee_match.group(1).replace(',', ''))
        logger.info(f"Detected MMK fee in staff reply: {mmk_fee:,.0f} MMK")
    
    # Add fee to detected MMK amount
    total_mmk = total_detected_mmk + mmk_fee
    
    if mmk_fee > 0:
        logger.info(f"MMK amount adjusted: {total_detected_mmk:,.0f} + {mmk_fee:,.0f} (fee) = {total_mmk:,.0f}")
    
    # Verify MMK (compare OCR detected amount with message amount)
    if tx_info['mmk'] > 0 and abs(total_mmk - tx_info['mmk']) > max(1000, tx_info['mmk'] * 0.5):
        await send_status_message(
            context,
            f"⚠️ <b>MMK Amount Mismatch Warning</b>\n\n"
            f"<b>Transaction:</b> Sell\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>Receipts:</b> {receipt_count}\n"
            f"<b>Expected (from message):</b> {tx_info['mmk']:,.0f} MMK\n"
            f"<b>Detected (from OCR):</b> {total_mmk:,.0f} MMK",
            parse_mode='HTML'
        )
    
    # ============================================================================
    # OCR USDT RECEIPT (CURRENT MESSAGE)
    # ============================================================================
    staff_photo = message.photo[-1]
    staff_file = await context.bot.get_file(staff_photo.file_id)
    staff_bytes = await staff_file.download_as_bytearray()
    staff_base64 = base64.b64encode(staff_bytes).decode('utf-8')
    
    usdt_result = await ocr_extract_usdt_with_fee(staff_base64)
    
    if not usdt_result:
        await send_alert(message, "❌ Could not detect USDT amount from receipt", context)
        if media_group_id_to_cleanup:
            delete_media_group_photos(media_group_id_to_cleanup)
        return
    
    detected_usdt = usdt_result['total_amount']
    bank_type = usdt_result['bank_type'] or 'swift'
    
    logger.info(f"Detected USDT: {detected_usdt:.4f} (amount: {usdt_result['amount']:.4f} + fee: {usdt_result['network_fee']:.4f}) from {bank_type}")
    
    # ============================================================================
    # UPDATE BALANCES
    # ============================================================================
    # Add MMK to detected bank
    for bank in balances['mmk_banks']:
        if banks_match(bank['bank_name'], detected_bank['bank_name']):
            bank['amount'] += total_mmk
            logger.info(f"Added {total_mmk:,.0f} MMK to {bank['bank_name']}")
            break
    
    # Reduce USDT from staff's account
    usdt_updated = False
    bank_type_capitalized = bank_type.capitalize()
    expected_bank_name = f"{user_prefix}({bank_type_capitalized})"
    
    logger.info(f"Looking for USDT bank: {expected_bank_name}")
    
    for bank in balances['usdt_banks']:
        if banks_match(bank['bank_name'], expected_bank_name):
            if bank['amount'] < detected_usdt:
                await send_alert(message, 
                    f"❌ Insufficient USDT balance!\n\n"
                    f"{bank['bank_name']}: {bank['amount']:.4f} USDT\n"
                    f"Required: {detected_usdt:.4f} USDT", 
                    context)
                if media_group_id_to_cleanup:
                    delete_media_group_photos(media_group_id_to_cleanup)
                return
            bank['amount'] -= detected_usdt
            usdt_updated = True
            logger.info(f"Reduced {detected_usdt:.4f} USDT from {bank['bank_name']}")
            break
    
    if not usdt_updated:
        await send_alert(message, f"⚠️ USDT bank '{expected_bank_name}' not found", context)
    
    # Send new balance
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
    
    if AUTO_BALANCE_TOPIC_ID:
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=AUTO_BALANCE_TOPIC_ID,
            text=new_balance
        )
    else:
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=new_balance
        )
    
    context.chat_data['balances'] = balances
    
    # Send success message
    mmk_display = f"{total_mmk:,.0f}"
    if mmk_fee > 0:
        mmk_display += f" (Receipts: {total_detected_mmk:,.0f} + Fee: {mmk_fee:,.0f})"
    elif receipt_count > 1:
        mmk_display += f" ({receipt_count} receipts)"
    
    await send_status_message(
        context,
        f"✅ <b>Sell Transaction Processed</b>\n\n"
        f"<b>Staff:</b> {user_prefix}\n"
        f"<b>MMK:</b> +{mmk_display} ({detected_bank['bank_name']})\n"
        f"<b>USDT:</b> -{detected_usdt:.4f} ({expected_bank_name})\n"
        f"<b>Bank Type:</b> {bank_type}",
        parse_mode='HTML'
    )
    
    # Clean up
    if original_message_id in pending_transactions:
        del pending_transactions[original_message_id]
    if media_group_id_to_cleanup:
        delete_media_group_photos(media_group_id_to_cleanup)

# ============================================================================
# INTERNAL TRANSFER PROCESSING
# ============================================================================

async def process_coin_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process coin transfer with network fee (USDT transfers between accounts)
    Format: San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT
    
    Process:
    1. Detect source and destination accounts
    2. Extract sent amount, fee, and received amount
    3. Reduce sent amount from source account
    4. Add received amount to destination account
    """
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded", context)
        return
    
    # Parse transfer text
    text = message.text or message.caption or ""
    
    # Pattern: Prefix(Bank) to Prefix(Bank) AMOUNT USDT-FEE USDT(fee) = RECEIVED USDT
    # Example: San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT
    coin_transfer_pattern = r'([A-Za-z\s]+)\s*\(([^)]+)\)\s+to\s+([A-Za-z\s]+)\s*\(([^)]+)\)\s+([\d.]+)\s*USDT\s*-\s*([\d.]+)\s*USDT\s*\(fee\)\s*=\s*([\d.]+)\s*USDT'
    match = re.search(coin_transfer_pattern, text, re.IGNORECASE)
    
    if match:
        from_prefix = match.group(1).strip()
        from_bank = match.group(2).strip()
        to_prefix = match.group(3).strip()
        to_bank = match.group(4).strip()
        sent_amount = float(match.group(5))
        fee_amount = float(match.group(6))
        received_amount = float(match.group(7))
        
        from_full_name = f"{from_prefix}({from_bank})"
        to_full_name = f"{to_prefix}({to_bank})"
        
        logger.info(f"Coin transfer detected: {from_full_name} -> {to_full_name}, Sent: {sent_amount} USDT, Fee: {fee_amount} USDT, Received: {received_amount} USDT")
        
        # Find source and destination banks in USDT banks
        from_bank_obj = None
        to_bank_obj = None
        
        for bank in balances['usdt_banks']:
            if banks_match(bank['bank_name'], from_full_name):
                from_bank_obj = bank
            if banks_match(bank['bank_name'], to_full_name):
                to_bank_obj = bank
        
        if not from_bank_obj:
            await send_alert(message, f"❌ Source USDT account not found: {from_full_name}", context)
            return
        
        if not to_bank_obj:
            await send_alert(message, f"❌ Destination USDT account not found: {to_full_name}", context)
            return
        
        # Check if sufficient balance in source account
        if from_bank_obj['amount'] < sent_amount:
            logger.error(f"Insufficient USDT balance! {from_full_name}: {from_bank_obj['amount']:.4f} USDT, Required: {sent_amount:.4f} USDT")
            await send_alert(message, 
                f"❌ Insufficient USDT balance!\n"
                f"{from_full_name}: {from_bank_obj['amount']:.4f} USDT\n"
                f"Required: {sent_amount:.4f} USDT\n"
                f"Shortage: {sent_amount - from_bank_obj['amount']:.4f} USDT", 
                context)
            return
        
        # Process coin transfer
        from_bank_obj['amount'] -= sent_amount
        to_bank_obj['amount'] += received_amount
        
        logger.info(f"Coin transfer processed: -{sent_amount:.4f} from {from_full_name}, +{received_amount:.4f} to {to_full_name}")
        
        # Send new balance to auto balance topic
        new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
        
        if AUTO_BALANCE_TOPIC_ID:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                message_thread_id=AUTO_BALANCE_TOPIC_ID,
                text=new_balance
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                text=new_balance
            )
        
        context.chat_data['balances'] = balances
        
        # Send success message to alert topic
        await send_status_message(
            context,
            f"✅ <b>Coin Transfer Processed</b>\n\n"
            f"<b>From:</b> {from_full_name}\n"
            f"<b>To:</b> {to_full_name}\n"
            f"<b>Sent:</b> {sent_amount:.4f} USDT\n"
            f"<b>Fee:</b> {fee_amount:.4f} USDT\n"
            f"<b>Received:</b> {received_amount:.4f} USDT\n\n"
            f"<b>New Balances:</b>\n"
            f"{from_full_name}: {from_bank_obj['amount']:.4f} USDT\n"
            f"{to_full_name}: {to_bank_obj['amount']:.4f} USDT",
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Coin transfer complete: {from_full_name} ({from_bank_obj['amount']:.4f}) -> {to_full_name} ({to_bank_obj['amount']:.4f})")
        return True
    
    return False

async def process_internal_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process internal bank transfers in Accounts Matter topic
    Format: San(Wave Channel) to NDT (Wave)
    """
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded", context)
        return
    
    if not message.photo:
        await send_alert(message, "❌ No receipt photo", context)
        return
    
    # Parse transfer text
    text = message.text or message.caption or ""
    
    # First check if this is a coin transfer with network fee
    coin_transfer_processed = await process_coin_transfer(update, context)
    if coin_transfer_processed:
        return
    
    # Pattern: Prefix(Bank) to Prefix(Bank)
    transfer_pattern = r'([A-Za-z\s]+)\(([^)]+)\)\s+to\s+([A-Za-z\s]+)\(([^)]+)\)'
    match = re.search(transfer_pattern, text, re.IGNORECASE)
    
    if not match:
        logger.info("Not an internal transfer message")
        return
    
    from_prefix = match.group(1).strip()
    from_bank = match.group(2).strip()
    to_prefix = match.group(3).strip()
    to_bank = match.group(4).strip()
    
    from_full_name = f"{from_prefix}({from_bank})"
    to_full_name = f"{to_prefix}({to_bank})"
    
    logger.info(f"Internal transfer: {from_full_name} -> {to_full_name}")
    
    # OCR to detect amount
    photo = message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
    
    # Determine if this is a USDT transfer (check if source or destination contains Swift/Wallet/Binance)
    is_usdt_transfer = any(keyword in from_full_name.lower() or keyword in to_full_name.lower() 
                           for keyword in ['swift', 'wallet', 'binance'])
    
    # Try to detect amount from receipt
    try:
        if is_usdt_transfer:
            # For USDT transfers, check if it's from Swift/Wallet to Binance (need to include network fee)
            from_is_swift_wallet = 'swift' in from_full_name.lower() or 'wallet' in from_full_name.lower()
            to_is_binance = 'binance' in to_full_name.lower()
            
            if from_is_swift_wallet or to_is_binance:
                # Use USDT OCR with network fee detection
                usdt_result = await ocr_extract_usdt_with_fee(photo_base64)
                
                if not usdt_result:
                    await send_alert(message, "❌ Could not detect USDT amount", context)
                    return
                
                # For Swift/Wallet to Binance: use total amount (includes network fee)
                if from_is_swift_wallet:
                    amount = usdt_result['total_amount']
                    logger.info(f"Detected USDT transfer: {amount:.4f} (amount: {usdt_result['amount']:.4f} + fee: {usdt_result['network_fee']:.4f})")
                else:
                    # For Binance to Swift/Wallet: use just the amount (no fee)
                    amount = usdt_result['amount']
                    logger.info(f"Detected USDT transfer: {amount:.4f}")
            else:
                # Regular USDT transfer without network fee
                prompt = """Extract the USDT transfer amount from this receipt.
Return JSON: {"amount": <number>}
Note: Return the amount as a positive number, ignore any minus signs."""

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + photo_base64}}
                        ]
                    }],
                    max_tokens=200
                )
                
                result = response.choices[0].message.content.strip()
                result = re.sub(r'```json\s*|\s*```', '', result)
                
                json_start = result.find('{')
                json_end = result.rfind('}')
                if json_start != -1 and json_end != -1:
                    result = result[json_start:json_end + 1]
                
                data = json.loads(result)
                amount = abs(float(data['amount']))
                logger.info(f"Detected transfer amount: {amount:.4f}")
        else:
            # For MMK/THB transfers, use simple amount detection
            prompt = """Extract the transfer amount from this receipt.
Return JSON: {"amount": <number>}
Note: Return the amount as a positive number, ignore any minus signs."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + photo_base64}}
                    ]
                }],
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            result = re.sub(r'```json\s*|\s*```', '', result)
            
            json_start = result.find('{')
            json_end = result.rfind('}')
            if json_start != -1 and json_end != -1:
                result = result[json_start:json_end + 1]
            
            data = json.loads(result)
            amount = abs(float(data['amount']))
            logger.info(f"Detected transfer amount: {amount:,.2f}")
        
    except Exception as e:
        logger.error(f"Amount detection error: {e}")

        logger.error(traceback.format_exc())
        await send_alert(message, "❌ Could not detect transfer amount", context)
        return
    
    # Find and update source bank
    from_bank_obj = None
    to_bank_obj = None
    
    # Check MMK, USDT, and THB banks
    all_banks = balances['mmk_banks'] + balances['usdt_banks'] + balances.get('thb_banks', [])
    
    for bank in all_banks:
        if banks_match(bank['bank_name'], from_full_name):
            from_bank_obj = bank
        if banks_match(bank['bank_name'], to_full_name):
            to_bank_obj = bank
    
    if not from_bank_obj:
        await send_alert(message, f"❌ Source bank not found: {from_full_name}", context)
        return
    
    if not to_bank_obj:
        await send_alert(message, f"❌ Destination bank not found: {to_full_name}", context)
        return
    
    # Check if sufficient balance
    if from_bank_obj['amount'] < amount:
        logger.error(f"Insufficient balance! {from_full_name}: {from_bank_obj['amount']:,.2f}, Transfer: {amount:,.2f}")
        await send_alert(message, 
            f"❌ Insufficient balance for transfer!\n\n"
            f"{from_full_name}: {from_bank_obj['amount']:,.2f}\n"
            f"Required: {amount:,.2f}\n"
            f"Shortage: {amount - from_bank_obj['amount']:,.2f}", 
            context)
        return
    
    # Process transfer
    from_bank_obj['amount'] -= amount
    to_bank_obj['amount'] += amount
    
    # Send new balance to auto balance topic
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
    
    if AUTO_BALANCE_TOPIC_ID:
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=AUTO_BALANCE_TOPIC_ID,
            text=new_balance
        )
    else:
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=new_balance
        )
    
    context.chat_data['balances'] = balances
    
    # Determine currency type for display
    currency = "MMK"
    if is_usdt_transfer:
        currency = "USDT"
    elif 'thb' in from_full_name.lower() or 'thb' in to_full_name.lower():
        currency = "THB"
    
    # Send success message to alert topic
    await send_status_message(
        context,
        f"✅ <b>Internal Transfer Processed</b>\n\n"
        f"<b>From:</b> {from_full_name}\n"
        f"<b>To:</b> {to_full_name}\n"
        f"<b>Amount:</b> {amount:,.4f} {currency}\n\n"
        f"<b>New Balances:</b>\n"
        f"{from_full_name}: {from_bank_obj['amount']:,.4f} {currency}\n"
        f"{to_full_name}: {to_bank_obj['amount']:,.4f} {currency}",
        parse_mode='HTML'
    )

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

async def process_media_group_delayed(update: Update, context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
    """Process a media group after a short delay to ensure all photos are collected"""
    
    # Check if already being processed
    if media_group_id in media_group_locks:
        logger.info(f"Media group {media_group_id} is already being processed, skipping")
        return
    
    # Mark as being processed
    media_group_locks[media_group_id] = True
    
    # Wait for all photos to arrive
    await asyncio.sleep(1.5)  # Wait 1.5 seconds for all photos to arrive
    
    if media_group_id not in media_groups:
        logger.warning(f"Media group {media_group_id} not found")
        if media_group_id in media_group_locks:
            del media_group_locks[media_group_id]
        return
    
    group_data = media_groups[media_group_id]
    photos = group_data['photos']
    message = group_data['message']
    original_text = group_data['original_text']
    
    logger.info(f"Processing media group {media_group_id} with {len(photos)} photos")
    
    # Extract transaction info
    tx_info = extract_transaction_info(original_text)
    
    # Check if transaction type is valid (Buy or Sell)
    if not tx_info['type']:
        logger.info(f"❌ Original message is not a Buy/Sell transaction")
        if media_group_id in media_groups:
            del media_groups[media_group_id]
        if media_group_id in media_group_locks:
            del media_group_locks[media_group_id]
        return
    
    # Allow transactions with 0 or missing amounts - will use OCR to detect
    if tx_info.get('usdt') is None or tx_info.get('mmk') is None or tx_info.get('usdt') == 0 or tx_info.get('mmk') == 0:
        logger.warning(f"Transaction has invalid amounts (USDT: {tx_info.get('usdt')}, MMK: {tx_info.get('mmk')}) - Will use OCR to detect amounts")
        # Set to 0 if None to avoid errors
        if tx_info.get('usdt') is None:
            tx_info['usdt'] = 0
        if tx_info.get('mmk') is None:
            tx_info['mmk'] = 0
    
    try:
        if tx_info['type'] == 'buy':
            await process_buy_transaction_bulk(update, context, tx_info, photos, message)
        elif tx_info['type'] == 'sell':
            await process_sell_transaction_bulk(update, context, tx_info, photos, message)
    except Exception as e:
        logger.error(f"Error processing media group: {e}")

        logger.error(traceback.format_exc())
    finally:
        # Clean up media group
        if media_group_id in media_groups:
            del media_groups[media_group_id]
        if media_group_id in media_group_locks:
            del media_group_locks[media_group_id]

async def process_buy_transaction_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict, photos: list, message):
    """Process BUY transaction with multiple photos sent as media group
    
    BUY FLOW:
    - Sale message contains USDT receipt(s) from customer
    - Staff reply contains MMK receipt(s) showing we sent MMK to customer
    
    When staff sends sale message with USDT receipts:
    - OCR the USDT receipts to detect amount
    
    When staff sends MMK receipts as reply:
    - OCR the MMK receipts to detect amount and bank
    """
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded. Post balance message in auto balance topic first.", context)
        return
    
    # Get staff prefix
    user_id = message.from_user.id
    user_prefix = get_user_prefix(user_id)
    
    if not user_prefix:
        await send_alert(message, "❌ You don't have a prefix set. Admin needs to use /set_user command.", context)
        return
    
    # Get original message
    original_message = message.reply_to_message
    original_has_photo = original_message and original_message.photo
    
    if not original_has_photo:
        # CASE 1: This is the SALE MESSAGE with USDT receipts from customer
        logger.info(f"Buy (Bulk): Processing as SALE MESSAGE - photos are USDT receipts from customer")
        
        # OCR all USDT receipts
        total_detected_usdt = 0
        
        for idx, photo in enumerate(photos, 1):
            logger.info(f"Processing USDT receipt {idx}/{len(photos)}")
            
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            # OCR USDT receipt - detect RECEIVED amount (not including network fee)
            usdt_result = await ocr_extract_usdt_received(photo_base64)
            
            if usdt_result and usdt_result['received_amount'] > 0:
                detected_usdt = usdt_result['received_amount']
                total_detected_usdt += detected_usdt
                logger.info(f"USDT receipt {idx}: {detected_usdt:.4f} USDT received (fee: {usdt_result['network_fee']:.4f} paid by customer)")
            else:
                logger.warning(f"Could not process USDT receipt {idx}")
        
        if total_detected_usdt == 0:
            # Use message amount as fallback
            total_detected_usdt = tx_info['usdt'] if tx_info['usdt'] else 0
            logger.warning(f"Could not detect USDT from receipts, using message amount: {total_detected_usdt:.4f}")
        
        # Check for mismatch
        if tx_info['usdt'] and tx_info['usdt'] > 0:
            if abs(total_detected_usdt - tx_info['usdt']) > max(0.5, tx_info['usdt'] * 0.01):
                await send_status_message(
                    context,
                    f"⚠️ <b>USDT Amount Mismatch Warning</b>\n\n"
                    f"<b>Transaction:</b> Buy (Bulk)\n"
                    f"<b>Staff:</b> {user_prefix}\n"
                    f"<b>Expected (from message):</b> {tx_info['usdt']:.4f} USDT\n"
                    f"<b>Detected (from OCR):</b> {total_detected_usdt:.4f} USDT\n"
                    f"<b>Receipts:</b> {len(photos)}",
                    parse_mode='HTML'
                )
        
        # Store for later
        sale_message_id = message.message_id
        
        pending_transactions[sale_message_id] = {
            'type': 'buy',
            'detected_usdt': total_detected_usdt,
            'expected_mmk': tx_info['mmk'],
            'expected_usdt': tx_info['usdt'],
            'user_prefix': user_prefix,
            'receipt_count': len(photos)
        }
        
        # Send notification
        await send_status_message(
            context,
            f"📥 <b>Buy Transaction - USDT Receipts Processed</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>USDT Detected:</b> {total_detected_usdt:.4f}\n"
            f"<b>Expected MMK:</b> {tx_info['mmk']:,.0f}\n"
            f"<b>Receipts:</b> {len(photos)}\n\n"
            f"⏳ Waiting for staff to send MMK receipt...",
            parse_mode='HTML'
        )
        
        logger.info(f"Buy transaction {sale_message_id} stored - waiting for MMK receipt")
        return
    
    else:
        # CASE 2: This is STAFF REPLY with MMK receipts
        logger.info(f"Buy (Bulk): Processing as STAFF REPLY - photos are MMK receipts")
        
        # Check for MMK fee
        staff_reply_text = message.text or message.caption or ""
        mmk_fee = 0
        fee_match = re.search(r'fee\s*-\s*([\d,]+(?:\.\d+)?)', staff_reply_text, re.IGNORECASE)
        if fee_match:
            mmk_fee = float(fee_match.group(1).replace(',', ''))
            logger.info(f"Detected MMK fee: {mmk_fee:,.0f} MMK")
        
        # OCR all MMK receipts
        total_detected_mmk = 0
        detected_bank = None
        
        for idx, photo in enumerate(photos, 1):
            logger.info(f"Processing MMK receipt {idx}/{len(photos)}")
            
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
            
            if result and result['amount']:
                total_detected_mmk += result['amount']
                if not detected_bank and result['bank']:
                    detected_bank = result['bank']
                logger.info(f"MMK receipt {idx}: {result['amount']:,.0f} MMK")
            else:
                logger.warning(f"Could not process MMK receipt {idx}")
        
        if not detected_bank:
            await send_alert(message, "❌ Could not detect bank from MMK receipts", context)
            return
        
        total_mmk = total_detected_mmk + mmk_fee
        
        # Get USDT amount from original message
        original_message_id = original_message.message_id
        stored_ocr = get_sale_receipt_ocr(original_message_id)
        detected_usdt = tx_info['usdt']
        
        if stored_ocr and stored_ocr[0].get('detected_usdt'):
            detected_usdt = stored_ocr[0]['detected_usdt']
            logger.info(f"Using pre-scanned USDT: {detected_usdt:.4f}")
            delete_sale_receipt_ocr(original_message_id)
        elif original_message.photo:
            # OCR the original USDT receipt - detect RECEIVED amount
            orig_photo = original_message.photo[-1]
            orig_file = await context.bot.get_file(orig_photo.file_id)
            orig_bytes = await orig_file.download_as_bytearray()
            orig_base64 = base64.b64encode(orig_bytes).decode('utf-8')
            
            usdt_result = await ocr_extract_usdt_received(orig_base64)
            if usdt_result and usdt_result['received_amount'] > 0:
                detected_usdt = usdt_result['received_amount']
                logger.info(f"Detected USDT RECEIVED from original receipt: {detected_usdt:.4f}")
        
        # Verify MMK amount
        if tx_info['mmk'] > 0 and abs(total_mmk - tx_info['mmk']) > max(1000, tx_info['mmk'] * 0.1):
            await send_status_message(
                context,
                f"⚠️ <b>MMK Amount Mismatch Warning</b>\n\n"
                f"<b>Transaction:</b> Buy (Bulk)\n"
                f"<b>Staff:</b> {user_prefix}\n"
                f"<b>Expected:</b> {tx_info['mmk']:,.0f} MMK\n"
                f"<b>Detected:</b> {total_mmk:,.0f} MMK",
                parse_mode='HTML'
            )
        
        # Check if sufficient MMK balance
        bank_found = False
        for bank in balances['mmk_banks']:
            if banks_match(bank['bank_name'], detected_bank['bank_name']):
                bank_found = True
                if bank['amount'] < total_mmk:
                    await send_alert(message, 
                        f"❌ Insufficient MMK balance!\n\n"
                        f"{bank['bank_name']}: {bank['amount']:,.0f} MMK\n"
                        f"Required: {total_mmk:,.0f} MMK", 
                        context)
                    return
                bank['amount'] -= total_mmk
                logger.info(f"Reduced {total_mmk:,.0f} MMK from {bank['bank_name']}")
                break
        
        if not bank_found:
            await send_alert(message, f"❌ Bank not found: {detected_bank['bank_name']}", context)
            return
        
        # Add USDT to receiving account
        receiving_usdt_account = get_receiving_usdt_account()
        usdt_updated = False
        
        for bank in balances['usdt_banks']:
            if banks_match(bank['bank_name'], receiving_usdt_account):
                bank['amount'] += detected_usdt
                usdt_updated = True
                logger.info(f"Added {detected_usdt:.4f} USDT to {receiving_usdt_account}")
                break
        
        if not usdt_updated:
            await send_alert(message, f"⚠️ USDT account '{receiving_usdt_account}' not found", context)
        
        # Send new balance
        new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
        
        if AUTO_BALANCE_TOPIC_ID:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                message_thread_id=AUTO_BALANCE_TOPIC_ID,
                text=new_balance
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                text=new_balance
            )
        
        context.chat_data['balances'] = balances
        
        # Send success message
        await send_status_message(
            context,
            f"✅ <b>Buy Transaction Processed (Bulk)</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>MMK:</b> -{total_mmk:,.0f} ({detected_bank['bank_name']})\n"
            f"<b>USDT:</b> +{detected_usdt:.4f} ({receiving_usdt_account})\n"
            f"<b>MMK Receipts:</b> {len(photos)}",
            parse_mode='HTML'
        )
        
async def process_sell_transaction_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict, photos: list, message):
    """Process SELL transaction with multiple photos sent as media group
    
    SELL FLOW:
    - Sale message contains MMK receipt(s) from customer
    - Staff reply (later) contains USDT receipt(s) showing transfer to customer
    
    When staff sends sale message with photos as reply:
    - The photos ARE the MMK receipts (customer's payment proof)
    - We OCR them as MMK, not USDT
    - Store the OCR results for later when staff sends USDT receipts
    """
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded", context)
        return
    
    # Get staff prefix
    user_id = message.from_user.id
    user_prefix = get_user_prefix(user_id)
    
    if not user_prefix:
        await send_alert(message, "❌ You don't have a prefix set. Admin needs to use /set_user command.", context)
        return
    
    # Get original message (the message being replied to)
    original_message = message.reply_to_message
    
    # Determine if the photos in this message are MMK receipts or USDT receipts
    # If original message has no photos, then the current photos are MMK receipts (sale message)
    # If original message has photos, then the current photos are USDT receipts (staff reply)
    
    original_has_photos = original_message and original_message.photo
    
    if not original_has_photos:
        # CASE 1: Staff is sending the SALE MESSAGE with MMK receipts
        # The photos in this message are MMK receipts from customer
        logger.info(f"Sell (Bulk): Processing as SALE MESSAGE - photos are MMK receipts")
        
        # OCR all MMK receipts
        total_detected_mmk = 0
        detected_bank = None
        mmk_receipt_count = 0
        
        for idx, photo in enumerate(photos, 1):
            logger.info(f"Processing MMK receipt {idx}/{len(photos)}")
            
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            # OCR as MMK receipt
            mmk_result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
            
            if not mmk_result or not mmk_result['amount']:
                logger.warning(f"Could not process MMK receipt {idx}")
                continue
            
            receipt_mmk = mmk_result['amount']
            total_detected_mmk += receipt_mmk
            mmk_receipt_count += 1
            
            # Store bank from first successful detection
            if not detected_bank and mmk_result['bank']:
                detected_bank = mmk_result['bank']
            
            logger.info(f"MMK receipt {idx}: {receipt_mmk:,.0f} MMK from {mmk_result['bank']['bank_name'] if mmk_result['bank'] else 'unknown'}")
        
        if mmk_receipt_count == 0:
            await send_alert(message, "❌ Could not detect MMK amount from receipt(s)", context)
            return
        
        if not detected_bank:
            await send_alert(message, "❌ Could not detect MMK bank from receipt(s)", context)
            return
        
        logger.info(f"Total MMK from {mmk_receipt_count} receipt(s): {total_detected_mmk:,.0f} MMK")
        
        # Check if staff reply contains fee (format: fee-3039)
        staff_text = message.text or message.caption or ""
        mmk_fee = 0
        fee_match = re.search(r'fee\s*-\s*([\d,]+(?:\.\d+)?)', staff_text, re.IGNORECASE)
        if fee_match:
            mmk_fee = float(fee_match.group(1).replace(',', ''))
            logger.info(f"Detected MMK fee: {mmk_fee:,.0f} MMK")
        
        total_mmk = total_detected_mmk + mmk_fee
        
        # Verify MMK amount
        if tx_info['mmk'] > 0 and abs(total_mmk - tx_info['mmk']) > max(1000, tx_info['mmk'] * 0.1):
            await send_status_message(
                context,
                f"⚠️ <b>MMK Amount Mismatch Warning</b>\n\n"
                f"<b>Transaction:</b> Sell\n"
                f"<b>Staff:</b> {user_prefix}\n"
                f"<b>Expected (from message):</b> {tx_info['mmk']:,.0f} MMK\n"
                f"<b>Detected (from OCR):</b> {total_mmk:,.0f} MMK\n"
                f"<b>Difference:</b> {abs(total_mmk - tx_info['mmk']):,.0f} MMK\n"
                f"<b>Receipts:</b> {mmk_receipt_count}",
                parse_mode='HTML'
            )
        
        # For now, just store the OCR results and send notification
        # The actual balance update will happen when staff sends USDT receipt
        # Store in pending_transactions for later use
        
        # Use message_id as key for pending transaction
        sale_message_id = message.message_id
        
        pending_transactions[sale_message_id] = {
            'type': 'sell',
            'mmk_amount': total_mmk,
            'mmk_receipts': total_detected_mmk,
            'mmk_fee': mmk_fee,
            'mmk_bank': detected_bank,
            'mmk_receipt_count': mmk_receipt_count,
            'expected_usdt': tx_info['usdt'],
            'user_prefix': user_prefix
        }
        
        # Send notification to alert topic
        await send_status_message(
            context,
            f"📥 <b>Sell Transaction - MMK Receipt Processed</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>MMK Detected:</b> {total_mmk:,.0f} ({detected_bank['bank_name']})\n"
            f"<b>Expected USDT:</b> {tx_info['usdt']:.4f}\n"
            f"<b>Receipts:</b> {mmk_receipt_count}\n\n"
            f"⏳ Waiting for staff to send USDT receipt...",
            parse_mode='HTML'
        )
        
        logger.info(f"Sell transaction {sale_message_id} stored - waiting for USDT receipt")
        return
    
    else:
        # CASE 2: Staff is sending USDT receipts as reply to sale message
        # The original message has MMK receipts, current photos are USDT receipts
        logger.info(f"Sell (Bulk): Processing as STAFF REPLY - photos are USDT receipts")
        
        # First, get MMK info from original message
        original_message_id = original_message.message_id
        media_group_id_to_cleanup = None
        
        # Check if we have stored OCR data for the original message
        stored_ocr_data = get_sale_receipt_ocr(original_message_id)
        
        total_detected_mmk = 0
        detected_bank = None
        mmk_receipt_count = 0
        mmk_fee = 0
        
        if stored_ocr_data:
            # Use stored OCR data
            logger.info(f"Using pre-scanned OCR data for MMK receipts")
            for ocr_record in stored_ocr_data:
                if ocr_record['detected_amount']:
                    total_detected_mmk += ocr_record['detected_amount']
                    mmk_receipt_count += 1
                    if not detected_bank and ocr_record['detected_bank']:
                        for bank in balances['mmk_banks']:
                            if banks_match(bank['bank_name'], ocr_record['detected_bank']):
                                detected_bank = bank
                                break
            
            # Clean up stored OCR data
            delete_sale_receipt_ocr(original_message_id)
            if stored_ocr_data[0].get('media_group_id'):
                delete_sale_receipt_ocr_by_media_group(stored_ocr_data[0]['media_group_id'])
        else:
            # OCR the original message's MMK receipts
            logger.info(f"No pre-scanned OCR data - processing MMK receipts now")
            
            # Get photos from original message
            mmk_photo_data_list = []
            media_group_id, stored_photos = get_media_group_by_message_id(original_message_id)
            
            if stored_photos and len(stored_photos) > 1:
                mmk_photo_data_list = stored_photos
                media_group_id_to_cleanup = media_group_id
            elif original_message.media_group_id:
                media_group_id = original_message.media_group_id
                stored_photos = get_media_group_photos(media_group_id)
                if stored_photos:
                    mmk_photo_data_list = stored_photos
                    media_group_id_to_cleanup = media_group_id
            
            if not mmk_photo_data_list:
                user_photo = original_message.photo[-1]
                user_file = await context.bot.get_file(user_photo.file_id)
                user_bytes = await user_file.download_as_bytearray()
                mmk_photo_data_list = [(original_message_id, bytes(user_bytes))]
            
            # OCR all MMK receipts
            for idx, photo_data in enumerate(mmk_photo_data_list, 1):
                msg_id, data = photo_data
                logger.info(f"Processing MMK receipt {idx}/{len(mmk_photo_data_list)}")
                
                if isinstance(data, str):
                    with open(data, 'rb') as f:
                        photo_bytes = f.read()
                    user_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                else:
                    user_base64 = base64.b64encode(data).decode('utf-8')
                
                mmk_result = await ocr_detect_mmk_bank_and_amount(user_base64, balances['mmk_banks'], user_prefix)
                
                if mmk_result and mmk_result['amount']:
                    total_detected_mmk += mmk_result['amount']
                    mmk_receipt_count += 1
                    if not detected_bank and mmk_result['bank']:
                        detected_bank = mmk_result['bank']
        
        if mmk_receipt_count == 0 or not detected_bank:
            await send_alert(message, "❌ Could not detect MMK bank/amount from sale receipt(s)", context)
            if media_group_id_to_cleanup:
                delete_media_group_photos(media_group_id_to_cleanup)
            return
        
        # Check for MMK fee in staff reply
        staff_text = message.text or message.caption or ""
        fee_match = re.search(r'fee\s*-\s*([\d,]+(?:\.\d+)?)', staff_text, re.IGNORECASE)
        if fee_match:
            mmk_fee = float(fee_match.group(1).replace(',', ''))
        
        total_mmk = total_detected_mmk + mmk_fee
        
        # Now process USDT receipts (the photos in current message)
        total_detected_usdt = 0
        detected_bank_type = None
        
        for idx, photo in enumerate(photos, 1):
            logger.info(f"Processing USDT receipt {idx}/{len(photos)}")
            
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            usdt_result = await ocr_extract_usdt_with_fee(photo_base64)
            
            if not usdt_result:
                logger.warning(f"Could not process USDT receipt {idx}")
                continue
            
            detected_usdt = usdt_result['total_amount']
            total_detected_usdt += detected_usdt
            
            if not detected_bank_type:
                detected_bank_type = usdt_result['bank_type']
            
            logger.info(f"USDT receipt {idx}: {detected_usdt:.4f} USDT from {usdt_result['bank_type']}")
        
        if total_detected_usdt == 0:
            await send_alert(message, "❌ Could not detect USDT amount from staff receipt(s)", context)
            if media_group_id_to_cleanup:
                delete_media_group_photos(media_group_id_to_cleanup)
            return
        
        # Default bank type if not detected
        if not detected_bank_type:
            detected_bank_type = 'swift'
        
        # Update MMK balance
        for bank in balances['mmk_banks']:
            if banks_match(bank['bank_name'], detected_bank['bank_name']):
                bank['amount'] += total_mmk
                logger.info(f"Added {total_mmk:,.0f} MMK to {bank['bank_name']}")
                break
        
        # Update USDT balance
        usdt_updated = False
        bank_type_capitalized = detected_bank_type.capitalize()
        expected_bank_name = f"{user_prefix}({bank_type_capitalized})"
        
        for bank in balances['usdt_banks']:
            if banks_match(bank['bank_name'], expected_bank_name):
                if bank['amount'] < total_detected_usdt:
                    await send_alert(message, 
                        f"❌ Insufficient USDT balance!\n\n"
                        f"{bank['bank_name']}: {bank['amount']:.4f} USDT\n"
                        f"Required: {total_detected_usdt:.4f} USDT", 
                        context)
                    if media_group_id_to_cleanup:
                        delete_media_group_photos(media_group_id_to_cleanup)
                    return
                bank['amount'] -= total_detected_usdt
                usdt_updated = True
                logger.info(f"Reduced {total_detected_usdt:.4f} USDT from {bank['bank_name']}")
                break
        
        if not usdt_updated:
            await send_alert(message, f"⚠️ USDT bank '{expected_bank_name}' not found", context)
        
        # Send new balance
        new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
        
        if AUTO_BALANCE_TOPIC_ID:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                message_thread_id=AUTO_BALANCE_TOPIC_ID,
                text=new_balance
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                text=new_balance
            )
        
        context.chat_data['balances'] = balances
        
        # Send success message
        await send_status_message(
            context,
            f"✅ <b>Sell Transaction Processed (Bulk)</b>\n\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>MMK:</b> +{total_mmk:,.0f} ({detected_bank['bank_name']})\n"
            f"<b>USDT:</b> -{total_detected_usdt:.4f} ({expected_bank_name})\n"
            f"<b>MMK Receipts:</b> {mmk_receipt_count}\n"
            f"<b>USDT Receipts:</b> {len(photos)}",
            parse_mode='HTML'
        )
        
async def process_p2p_sell_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict):
    """P2P SELL: Staff sells USDT to another exchange (not to customer)
    Format: sell 13000000/3222.6=4034.00981 fee-6.44
    
    Process:
    1. Detect MMK bank from receipt (using confidence matching)
    2. Add MMK to detected bank
    3. Reduce USDT from staff's account (USDT + fee)
    """
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_alert(message, "❌ Balance not loaded. Post balance message in auto balance topic first.", context)
        return
    
    if not message.photo:
        await send_alert(message, "❌ No MMK receipt photo", context)
        return
    
    # Get staff prefix
    user_id = message.from_user.id
    user_prefix = get_user_prefix(user_id)
    
    if not user_prefix:
        await send_alert(message, "❌ You don't have a prefix set. Admin needs to use /set_user command.", context)
        return
    
    # Get MMK receipt
    photo = message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
    
    # Get registered MMK bank accounts for matching
    registered_accounts = get_all_mmk_bank_accounts()
    
    if not registered_accounts:
        # Fallback to old method if no accounts registered
        result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
        if not result:
            await send_alert(message, "❌ Could not detect bank/amount from MMK receipt", context)
            return
        detected_mmk = result['amount']
        detected_bank = result['bank']
    else:
        # Use confidence-based matching
        mmk_banks_with_ids = []
        for idx, acc in enumerate(registered_accounts, 1):
            mmk_banks_with_ids.append({
                'bank_id': idx,
                'bank_name': acc['bank_name'],
                'account_number': acc['account_number'],
                'account_holder': acc['account_holder']
            })
        
        # OCR with confidence matching
        match_result = await ocr_match_mmk_receipt_to_banks(photo_base64, mmk_banks_with_ids)
        
        if not match_result:
            await send_alert(message, "❌ Could not analyze MMK receipt", context)
            return
        
        detected_mmk = match_result['amount']
        banks_confidence = match_result['banks']
        
        # Find bank with highest confidence
        best_bank_id = None
        best_confidence = 0
        for bank_id_str, confidence in banks_confidence.items():
            if confidence > best_confidence:
                best_confidence = confidence
                best_bank_id = int(bank_id_str)
        
        if best_confidence < 50:
            # Low confidence, show warning
            confidence_list = "\n".join([
                f"• {mmk_banks_with_ids[int(bid)-1]['bank_name']}: {conf}%"
                for bid, conf in banks_confidence.items()
            ])
            await message.reply_text(
                f"⚠️ Low confidence in bank detection!\n\n"
                f"Confidence scores:\n{confidence_list}\n\n"
                f"Best match: {best_confidence}%\n\n"
                f"Please check the receipt and try again, or register the correct bank account with /set_mmk_bank"
            )
            return
        
        # Get the matched bank
        matched_bank_info = mmk_banks_with_ids[best_bank_id - 1]
        matched_bank_name = matched_bank_info['bank_name']
        
        # Find the bank in balances
        detected_bank = None
        for bank in balances['mmk_banks']:
            if banks_match(bank['bank_name'], matched_bank_name):
                detected_bank = bank
                break
        
        if not detected_bank:
            await send_alert(message, f"❌ Matched bank '{matched_bank_name}' not found in balance", context)
            return
        
        logger.info(f"P2P Sell: Matched to {matched_bank_name} with {best_confidence}% confidence")
    
    # Verify MMK amount (compare OCR detected amount with message amount)
    if abs(detected_mmk - tx_info['mmk']) > max(1000, tx_info['mmk'] * 0.5):
        # Send warning to alert topic but continue processing
        await send_status_message(
            context,
            f"⚠️ <b>MMK Amount Mismatch Warning</b>\n\n"
            f"<b>Transaction:</b> P2P Sell\n"
            f"<b>Staff:</b> {user_prefix}\n"
            f"<b>Expected (from message):</b> {tx_info['mmk']:,.0f} MMK\n"
            f"<b>Detected (from OCR):</b> {detected_mmk:,.0f} MMK\n"
            f"<b>Difference:</b> {abs(detected_mmk - tx_info['mmk']):,.0f} MMK\n\n"
            f"⚠️ Processing with OCR detected amount: {detected_mmk:,.0f} MMK",
            parse_mode='HTML'
        )
        logger.warning(f"MMK amount mismatch! Expected: {tx_info['mmk']:,.0f} MMK, Detected: {detected_mmk:,.0f} MMK - Processing with detected amount")
    
    # Continue processing with OCR detected amount
    
    # Add MMK to detected bank
    for bank in balances['mmk_banks']:
        if banks_match(bank['bank_name'], detected_bank['bank_name']):
            bank['amount'] += detected_mmk
            logger.info(f"Added {detected_mmk:,.0f} MMK to {bank['bank_name']}")
            break
    
    # Reduce USDT from staff's account (USDT + fee)
    total_usdt = tx_info['total_usdt']  # This includes the fee
    usdt_updated = False
    
    for bank in balances['usdt_banks']:
        if bank.get('prefix') == user_prefix:
            # Check if sufficient USDT balance
            if bank['amount'] < total_usdt:
                await message.reply_text(
                    f"❌ Insufficient USDT balance!\n\n"
                    f"{bank['bank_name']}: {bank['amount']:.4f} USDT\n"
                    f"Required: {total_usdt:.4f} USDT (USDT: {tx_info['usdt']:.4f} + Fee: {tx_info['fee']:.4f})\n"
                    f"Shortage: {total_usdt - bank['amount']:.4f} USDT"
                )
                return
            bank['amount'] -= total_usdt
            usdt_updated = True
            logger.info(f"Reduced {total_usdt:.4f} USDT from {bank['bank_name']} (USDT: {tx_info['usdt']:.4f} + Fee: {tx_info['fee']:.4f})")
            break
    
    if not usdt_updated:
        await send_alert(message, f"❌ No USDT bank found for prefix '{user_prefix}'", context)
        return
    
    # Send new balance
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
    
    # Send to auto balance topic if configured, otherwise to main chat
    if AUTO_BALANCE_TOPIC_ID:
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=AUTO_BALANCE_TOPIC_ID,
            text=new_balance
        )
    else:
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=new_balance
        )
    
    context.chat_data['balances'] = balances
    
    # await message.reply_text(
    #     f"✅ P2P Sell processed!\n\n"
    #     f"MMK: +{detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
    #     f"USDT: -{total_usdt:.4f} (Amount: {tx_info['usdt']:.4f} + Fee: {tx_info['fee']:.4f})\n"
    #     f"Rate: {tx_info['rate']:.5f}"
    # )

# ============================================================================
# IMMEDIATE SALE RECEIPT OCR PROCESSING
# ============================================================================

async def process_sale_receipt_immediate(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict):
    """Process sale receipt immediately when sale message arrives (before staff reply)
    
    This function:
    1. OCR the sale receipt(s) to detect amount and bank
    2. Store OCR results in database
    3. Send notification to alert topic with detected info
    4. If mismatch detected, send warning
    
    Supports multiple receipts (media groups)
    """
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        logger.warning("Balance not loaded - cannot process sale receipt immediately")
        return
    
    if not message.photo:
        logger.warning("No photo in sale message")
        return
    
    message_id = message.message_id
    media_group_id = message.media_group_id
    transaction_type = tx_info.get('type')
    expected_mmk = tx_info.get('mmk', 0)
    expected_usdt = tx_info.get('usdt', 0)
    
    logger.info(f"🔍 Immediate OCR processing for sale message {message_id} (type: {transaction_type})")
    
    # For sell transactions: OCR the MMK receipt to detect amount and bank
    # For buy transactions: OCR the USDT receipt to detect amount
    
    if transaction_type == 'sell':
        # Sell: Customer sends MMK receipt, we need to detect MMK amount and bank
        photo = message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Use confidence-based bank matching for sell transactions
        mmk_banks_with_ids = []
        for idx, bank in enumerate(balances['mmk_banks']):
            bank_account = get_mmk_bank_account(bank['bank_name'])
            if bank_account:
                mmk_banks_with_ids.append({
                    'bank_id': idx + 1,
                    'bank_name': bank['bank_name'],
                    'account_number': bank_account['account_number'],
                    'account_holder': bank_account['account_holder']
                })
            else:
                # Use placeholder if no account registered
                mmk_banks_with_ids.append({
                    'bank_id': idx + 1,
                    'bank_name': bank['bank_name'],
                    'account_number': '0000',
                    'account_holder': 'Unknown'
                })
        
        # OCR with confidence matching
        ocr_result = await ocr_match_mmk_receipt_to_banks(photo_base64, mmk_banks_with_ids)
        
        if ocr_result:
            detected_amount = ocr_result.get('amount', 0)
            banks_confidence = ocr_result.get('banks', {})
            
            # Find best matching bank
            best_bank_id = None
            best_confidence = 0
            for bank_id_str, confidence in banks_confidence.items():
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_bank_id = int(bank_id_str)
            
            detected_bank = None
            if best_bank_id and best_bank_id <= len(mmk_banks_with_ids):
                detected_bank = mmk_banks_with_ids[best_bank_id - 1]['bank_name']
            
            # Save OCR result to database
            save_sale_receipt_ocr(
                message_id=message_id,
                receipt_index=0,
                transaction_type=transaction_type,
                detected_amount=detected_amount,
                detected_bank=detected_bank,
                detected_usdt=None,
                media_group_id=media_group_id,
                ocr_raw_data={'confidence': best_confidence, 'all_banks': banks_confidence}
            )
            
            # Check for amount mismatch
            amount_mismatch = abs(detected_amount - expected_mmk) > max(1000, expected_mmk * 0.1) if expected_mmk > 0 else False
            
            # Send notification to alert topic
            status_emoji = "⚠️" if amount_mismatch or best_confidence < 50 else "📥"
            
            alert_text = (
                f"{status_emoji} <b>Sale Receipt Detected</b>\n\n"
                f"<b>Type:</b> {transaction_type.upper()}\n"
                f"<b>Message ID:</b> {message_id}\n"
                f"<b>Expected MMK:</b> {expected_mmk:,.0f}\n"
                f"<b>Detected MMK:</b> {detected_amount:,.0f}\n"
                f"<b>Detected Bank:</b> {detected_bank or 'Unknown'}\n"
                f"<b>Confidence:</b> {best_confidence}%\n"
            )
            
            if amount_mismatch:
                alert_text += f"\n⚠️ <b>Amount Mismatch!</b> Difference: {abs(detected_amount - expected_mmk):,.0f} MMK"
            
            if best_confidence < 50:
                alert_text += f"\n⚠️ <b>Low Confidence!</b> Bank detection may be inaccurate"
            
            await send_status_message(context, alert_text, parse_mode='HTML')
            
            logger.info(f"✅ Sale receipt OCR saved: amount={detected_amount:,.0f}, bank={detected_bank}, confidence={best_confidence}%")
        else:
            logger.warning(f"❌ Could not OCR sale receipt for message {message_id}")
            
            # Send warning to alert topic
            await send_status_message(
                context,
                f"⚠️ <b>Sale Receipt OCR Failed</b>\n\n"
                f"<b>Message ID:</b> {message_id}\n"
                f"<b>Type:</b> {transaction_type.upper()}\n"
                f"<b>Expected MMK:</b> {expected_mmk:,.0f}\n\n"
                f"Could not detect amount/bank from receipt. Staff will need to verify manually.",
                parse_mode='HTML'
            )
    
    elif transaction_type == 'buy':
        # Buy: Customer sends USDT receipt, we need to detect USDT amount
        photo = message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # OCR USDT receipt
        usdt_result = await ocr_extract_usdt_with_fee(photo_base64)
        
        if usdt_result:
            detected_usdt = usdt_result.get('total_amount', 0)
            
            # Save OCR result to database
            save_sale_receipt_ocr(
                message_id=message_id,
                receipt_index=0,
                transaction_type=transaction_type,
                detected_amount=None,
                detected_bank=None,
                detected_usdt=detected_usdt,
                media_group_id=media_group_id,
                ocr_raw_data=usdt_result
            )
            
            # Check for amount mismatch
            amount_mismatch = abs(detected_usdt - expected_usdt) > max(0.5, expected_usdt * 0.01) if expected_usdt > 0 else False
            
            # Send notification to alert topic
            status_emoji = "⚠️" if amount_mismatch else "📥"
            
            alert_text = (
                f"{status_emoji} <b>Sale Receipt Detected</b>\n\n"
                f"<b>Type:</b> {transaction_type.upper()}\n"
                f"<b>Message ID:</b> {message_id}\n"
                f"<b>Expected USDT:</b> {expected_usdt:.4f}\n"
                f"<b>Detected USDT:</b> {detected_usdt:.4f}\n"
            )
            
            if amount_mismatch:
                alert_text += f"\n⚠️ <b>Amount Mismatch!</b> Difference: {abs(detected_usdt - expected_usdt):.4f} USDT"
            
            await send_status_message(context, alert_text, parse_mode='HTML')
            
            logger.info(f"✅ Sale receipt OCR saved: usdt={detected_usdt:.4f}")
        else:
            logger.warning(f"❌ Could not OCR sale receipt for message {message_id}")
            
            await send_status_message(
                context,
                f"⚠️ <b>Sale Receipt OCR Failed</b>\n\n"
                f"<b>Message ID:</b> {message_id}\n"
                f"<b>Type:</b> {transaction_type.upper()}\n"
                f"<b>Expected USDT:</b> {expected_usdt:.4f}\n\n"
                f"Could not detect amount from receipt. Staff will need to verify manually.",
                parse_mode='HTML'
            )

async def process_sale_media_group_immediate(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                              media_group_id: str, tx_info: dict):
    """Process multiple sale receipts (media group) immediately
    
    Called after a short delay to ensure all photos in the media group are collected
    """
    
    # Wait for all photos to arrive
    await asyncio.sleep(1.5)
    
    balances = context.chat_data.get('balances')
    if not balances:
        logger.warning("Balance not loaded - cannot process sale media group immediately")
        return
    
    # Get all photos from the media group
    stored_photos = get_media_group_photos(media_group_id)
    
    if not stored_photos:
        logger.warning(f"No photos found for media group {media_group_id}")
        return
    
    transaction_type = tx_info.get('type')
    expected_mmk = tx_info.get('mmk', 0)
    expected_usdt = tx_info.get('usdt', 0)
    
    logger.info(f"🔍 Immediate OCR processing for media group {media_group_id} with {len(stored_photos)} photos")
    
    total_detected_amount = 0
    detected_bank = None
    best_confidence = 0
    
    if transaction_type == 'sell':
        # Sell: OCR all MMK receipts
        mmk_banks_with_ids = []
        for idx, bank in enumerate(balances['mmk_banks']):
            bank_account = get_mmk_bank_account(bank['bank_name'])
            if bank_account:
                mmk_banks_with_ids.append({
                    'bank_id': idx + 1,
                    'bank_name': bank['bank_name'],
                    'account_number': bank_account['account_number'],
                    'account_holder': bank_account['account_holder']
                })
            else:
                mmk_banks_with_ids.append({
                    'bank_id': idx + 1,
                    'bank_name': bank['bank_name'],
                    'account_number': '0000',
                    'account_holder': 'Unknown'
                })
        
        for idx, (msg_id, file_path) in enumerate(stored_photos):
            try:
                with open(file_path, 'rb') as f:
                    photo_bytes = f.read()
                photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                
                ocr_result = await ocr_match_mmk_receipt_to_banks(photo_base64, mmk_banks_with_ids)
                
                if ocr_result:
                    receipt_amount = ocr_result.get('amount', 0)
                    banks_confidence = ocr_result.get('banks', {})
                    
                    # Find best matching bank for this receipt
                    receipt_best_bank_id = None
                    receipt_best_confidence = 0
                    for bank_id_str, confidence in banks_confidence.items():
                        if confidence > receipt_best_confidence:
                            receipt_best_confidence = confidence
                            receipt_best_bank_id = int(bank_id_str)
                    
                    receipt_bank = None
                    if receipt_best_bank_id and receipt_best_bank_id <= len(mmk_banks_with_ids):
                        receipt_bank = mmk_banks_with_ids[receipt_best_bank_id - 1]['bank_name']
                    
                    # Save OCR result
                    save_sale_receipt_ocr(
                        message_id=msg_id,
                        receipt_index=idx,
                        transaction_type=transaction_type,
                        detected_amount=receipt_amount,
                        detected_bank=receipt_bank,
                        detected_usdt=None,
                        media_group_id=media_group_id,
                        ocr_raw_data={'confidence': receipt_best_confidence, 'all_banks': banks_confidence}
                    )
                    
                    total_detected_amount += receipt_amount
                    
                    # Use bank from first receipt with good confidence
                    if not detected_bank and receipt_best_confidence >= 50:
                        detected_bank = receipt_bank
                        best_confidence = receipt_best_confidence
                    
                    logger.info(f"Receipt {idx+1}: {receipt_amount:,.0f} MMK, bank={receipt_bank}, confidence={receipt_best_confidence}%")
                    
            except Exception as e:
                logger.error(f"Error processing receipt {idx+1}: {e}")
        
        # Check for amount mismatch
        amount_mismatch = abs(total_detected_amount - expected_mmk) > max(1000, expected_mmk * 0.1) if expected_mmk > 0 else False
        
        # Send notification
        status_emoji = "⚠️" if amount_mismatch or best_confidence < 50 else "📥"
        
        alert_text = (
            f"{status_emoji} <b>Sale Receipts Detected ({len(stored_photos)} photos)</b>\n\n"
            f"<b>Type:</b> {transaction_type.upper()}\n"
            f"<b>Media Group:</b> {media_group_id[:8]}...\n"
            f"<b>Expected MMK:</b> {expected_mmk:,.0f}\n"
            f"<b>Total Detected MMK:</b> {total_detected_amount:,.0f}\n"
            f"<b>Detected Bank:</b> {detected_bank or 'Unknown'}\n"
            f"<b>Best Confidence:</b> {best_confidence}%\n"
        )
        
        if amount_mismatch:
            alert_text += f"\n⚠️ <b>Amount Mismatch!</b> Difference: {abs(total_detected_amount - expected_mmk):,.0f} MMK"
        
        if best_confidence < 50:
            alert_text += f"\n⚠️ <b>Low Confidence!</b> Bank detection may be inaccurate"
        
        await send_status_message(context, alert_text, parse_mode='HTML')
        
    elif transaction_type == 'buy':
        # Buy: OCR all USDT receipts
        for idx, (msg_id, file_path) in enumerate(stored_photos):
            try:
                with open(file_path, 'rb') as f:
                    photo_bytes = f.read()
                photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                
                usdt_result = await ocr_extract_usdt_with_fee(photo_base64)
                
                if usdt_result:
                    receipt_usdt = usdt_result.get('total_amount', 0)
                    
                    save_sale_receipt_ocr(
                        message_id=msg_id,
                        receipt_index=idx,
                        transaction_type=transaction_type,
                        detected_amount=None,
                        detected_bank=None,
                        detected_usdt=receipt_usdt,
                        media_group_id=media_group_id,
                        ocr_raw_data=usdt_result
                    )
                    
                    total_detected_amount += receipt_usdt
                    logger.info(f"Receipt {idx+1}: {receipt_usdt:.4f} USDT")
                    
            except Exception as e:
                logger.error(f"Error processing receipt {idx+1}: {e}")
        
        # Check for amount mismatch
        amount_mismatch = abs(total_detected_amount - expected_usdt) > max(0.5, expected_usdt * 0.01) if expected_usdt > 0 else False
        
        # Send notification
        status_emoji = "⚠️" if amount_mismatch else "📥"
        
        alert_text = (
            f"{status_emoji} <b>Sale Receipts Detected ({len(stored_photos)} photos)</b>\n\n"
            f"<b>Type:</b> {transaction_type.upper()}\n"
            f"<b>Media Group:</b> {media_group_id[:8]}...\n"
            f"<b>Expected USDT:</b> {expected_usdt:.4f}\n"
            f"<b>Total Detected USDT:</b> {total_detected_amount:.4f}\n"
        )
        
        if amount_mismatch:
            alert_text += f"\n⚠️ <b>Amount Mismatch!</b> Difference: {abs(total_detected_amount - expected_usdt):.4f} USDT"
        
        await send_status_message(context, alert_text, parse_mode='HTML')
    
    logger.info(f"✅ Media group OCR complete: {len(stored_photos)} receipts, total={total_detected_amount}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages"""
    message = update.message
    
    # Skip if no message (e.g., edited message, channel post, etc.)
    if not message:
        return
    
    # Log ALL messages received in target group (for debugging)
    if message.chat.id == TARGET_GROUP_ID:
        msg_type = "text" if message.text else ("photo" if message.photo else "other")
        logger.info(f"🔍 Received {msg_type} message - Chat: {message.chat.id}, Thread: {message.message_thread_id}, User: {message.from_user.id} (@{message.from_user.username})")
    
    if message.chat.id != TARGET_GROUP_ID:
        return
    
    # Auto-load balance from auto balance topic (if configured)
    if AUTO_BALANCE_TOPIC_ID and message.message_thread_id == AUTO_BALANCE_TOPIC_ID:
        if message.text and 'USDT' in message.text:
            balances = parse_balance_message(message.text)
            if balances:
                context.chat_data['balances'] = balances
                thb_count = len(balances.get('thb_banks', []))
                logger.info(f"✅ Balance loaded: {len(balances['mmk_banks'])} MMK banks, {len(balances['usdt_banks'])} USDT banks, {thb_count} THB banks")
        return
    
    # Handle internal transfers in Accounts Matter topic
    if ACCOUNTS_MATTER_TOPIC_ID and message.message_thread_id == ACCOUNTS_MATTER_TOPIC_ID:
        await process_internal_transfer(update, context)
        return
    
    # Process transactions in USDT transfers topic OR main chat
    # Note: In Telegram forum groups, when you reply to a message, the thread_id becomes the message_id of the original message
    # So we need to check if this is a reply, and if so, verify the original message location
    
    # Normalize thread_id: treat None as 1 for General topic
    current_thread_id = message.message_thread_id if message.message_thread_id is not None else 1
    
    # Determine if this message is in the correct location
    is_valid_location = False
    location_description = ""
    
    # Check if this is a reply to another message
    if message.reply_to_message:
        # For replies, check where the ORIGINAL message was posted
        original_thread_id = message.reply_to_message.message_thread_id if message.reply_to_message.message_thread_id is not None else 1
        
        if USDT_TRANSFERS_TOPIC_ID and USDT_TRANSFERS_TOPIC_ID > 1:
            # Specific topic mode
            if original_thread_id == USDT_TRANSFERS_TOPIC_ID:
                is_valid_location = True
                location_description = f"Reply to message in USDT Transfers topic {USDT_TRANSFERS_TOPIC_ID}"
        else:
            # Main chat mode (topic 1)
            if original_thread_id == 1:
                is_valid_location = True
                location_description = f"Reply to message in main chat (thread_id: {current_thread_id})"
    else:
        # Not a reply, check current location
        if USDT_TRANSFERS_TOPIC_ID and USDT_TRANSFERS_TOPIC_ID > 1:
            # Specific topic mode
            if current_thread_id == USDT_TRANSFERS_TOPIC_ID:
                is_valid_location = True
                location_description = f"Message in USDT Transfers topic {USDT_TRANSFERS_TOPIC_ID}"
        else:
            # Main chat mode (topic 1)
            if current_thread_id == 1:
                is_valid_location = True
                location_description = f"Message in main chat"
    
    if is_valid_location:
        logger.info(f"📝 {location_description} from user {message.from_user.id} (@{message.from_user.username})")
    else:
        expected = f"topic {USDT_TRANSFERS_TOPIC_ID}" if (USDT_TRANSFERS_TOPIC_ID and USDT_TRANSFERS_TOPIC_ID > 1) else "main chat/topic 1"
        logger.info(f"   ⏭️ Skipping: Wrong location (thread: {current_thread_id}, expected: {expected})")
        return
    
    # Log message details
    has_photo = bool(message.photo)
    is_reply = bool(message.reply_to_message)
    message_text = (message.text or message.caption or "")[:50]
    
    logger.info(f"   Has photo: {has_photo}, Is reply: {is_reply}, Text: '{message_text}...'")
    
    # ============================================================================
    # IMMEDIATE SALE RECEIPT OCR - Process sale messages when they arrive
    # ============================================================================
    # When a sale message arrives (not a reply, has photo with Buy/Sell text),
    # immediately OCR the receipt and store results for later use
    if has_photo and not is_reply:
        sale_message_text = message.text or message.caption or ""
        tx_info_check = extract_transaction_info(sale_message_text)
        
        # Check if this is a Buy/Sell transaction (not P2P sell which has 'fee')
        if tx_info_check.get('type') in ['buy', 'sell'] and 'fee' not in sale_message_text.lower():
            logger.info(f"   📥 Sale message detected - triggering immediate OCR")
            
            if message.media_group_id:
                # Media group - save photo and schedule delayed OCR for all photos
                media_group_id = message.media_group_id
                
                # Download and save photo to disk
                try:
                    photo = message.photo[-1]
                    photo_file = await context.bot.get_file(photo.file_id)
                    photo_bytes = await photo_file.download_as_bytearray()
                    
                    # Save to disk and database
                    file_path = save_media_group_photo(media_group_id, message.message_id, bytes(photo_bytes))
                    logger.info(f"   💾 Saved media group photo: {file_path}")
                    
                    # Check if this is the first photo in the group (has caption)
                    if sale_message_text:
                        # Schedule delayed OCR processing for the entire media group
                        asyncio.create_task(process_sale_media_group_immediate(update, context, media_group_id, tx_info_check))
                        logger.info(f"   ⏰ Scheduled immediate OCR for media group {media_group_id}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to save media group photo: {e}")
            else:
                # Single photo - process immediately
                await process_sale_receipt_immediate(update, context, tx_info_check)
            
            # Don't return here - continue to allow staff to reply later
    
    # Store incoming media groups from sale bot (photos with transaction info)
    # Download and save to disk for persistence across bot restarts
    # (This handles media group photos that weren't caught above)
    if has_photo and message.media_group_id and not is_reply:
        media_group_id = message.media_group_id
        
        # Check if already saved (from immediate OCR above)
        existing_photos = get_media_group_photos(media_group_id)
        already_saved = any(msg_id == message.message_id for msg_id, _ in existing_photos)
        
        if not already_saved:
            # Download and save photo to disk
            try:
                photo = message.photo[-1]
                photo_file = await context.bot.get_file(photo.file_id)
                photo_bytes = await photo_file.download_as_bytearray()
                
                # Save to disk and database
                file_path = save_media_group_photo(media_group_id, message.message_id, bytes(photo_bytes))
                logger.info(f"   💾 Saved media group photo: {file_path}")
                
            except Exception as e:
                logger.error(f"   ❌ Failed to save media group photo: {e}")
    
    # Check if this is a P2P sell (photo with "fee" in message text)
    # P2P sell can be either direct post OR a reply, but must have "fee" in the message
    if has_photo:
        current_message_text = message.text or message.caption or ""
        if 'fee' in current_message_text.lower():
            logger.info(f"   🔍 Detected P2P sell format (fee in message)")
            tx_info = extract_transaction_info(current_message_text)
            
            if tx_info.get('type') == 'p2p_sell':
                logger.info(f"   🔄 Processing P2P SELL transaction: {tx_info['usdt']} USDT + {tx_info['fee']} fee = {tx_info['mmk']:,.0f} MMK")
                await process_p2p_sell_transaction(update, context, tx_info)
                return
    
    # Regular Buy/Sell transactions require a reply
    if not message.reply_to_message or not message.photo:
        logger.info(f"   ⏭️ Skipping: Not a photo reply")
        return
    
    # If the original message is part of a media group and not in database, 
    # try to fetch and store all photos from the media group now
    if message.reply_to_message.media_group_id:
        original_media_group_id = message.reply_to_message.media_group_id
        stored_photos = get_media_group_photos(original_media_group_id)
        
        if not stored_photos:
            # Media group not in database - try to fetch adjacent messages
            logger.info(f"   📥 Fetching media group {original_media_group_id} photos...")
            original_msg_id = message.reply_to_message.message_id
            chat_id = message.reply_to_message.chat.id
            
            # Store the original message's photo first
            try:
                orig_photo = message.reply_to_message.photo[-1]
                orig_file = await context.bot.get_file(orig_photo.file_id)
                orig_bytes = await orig_file.download_as_bytearray()
                save_media_group_photo(original_media_group_id, original_msg_id, bytes(orig_bytes))
                logger.info(f"   💾 Saved original photo (msg {original_msg_id})")
            except Exception as e:
                logger.error(f"   ❌ Failed to save original photo: {e}")
            
            # Try to fetch adjacent messages (forward direction)
            for offset in range(1, 10):
                msg_id = original_msg_id + offset
                try:
                    forwarded = await context.bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=chat_id,
                        message_id=msg_id
                    )
                    if forwarded.photo:
                        # Download and save
                        fwd_file = await context.bot.get_file(forwarded.photo[-1].file_id)
                        fwd_bytes = await fwd_file.download_as_bytearray()
                        save_media_group_photo(original_media_group_id, msg_id, bytes(fwd_bytes))
                        logger.info(f"   💾 Saved adjacent photo (msg {msg_id})")
                        await context.bot.delete_message(chat_id=chat_id, message_id=forwarded.message_id)
                    else:
                        await context.bot.delete_message(chat_id=chat_id, message_id=forwarded.message_id)
                        break
                except:
                    break
            
            # Try backward direction
            for offset in range(1, 10):
                msg_id = original_msg_id - offset
                if msg_id <= 0:
                    break
                try:
                    forwarded = await context.bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=chat_id,
                        message_id=msg_id
                    )
                    if forwarded.photo:
                        fwd_file = await context.bot.get_file(forwarded.photo[-1].file_id)
                        fwd_bytes = await fwd_file.download_as_bytearray()
                        save_media_group_photo(original_media_group_id, msg_id, bytes(fwd_bytes))
                        logger.info(f"   💾 Saved adjacent photo (msg {msg_id})")
                        await context.bot.delete_message(chat_id=chat_id, message_id=forwarded.message_id)
                    else:
                        await context.bot.delete_message(chat_id=chat_id, message_id=forwarded.message_id)
                        break
                except:
                    break
            
            # Check how many photos we collected
            stored_photos = get_media_group_photos(original_media_group_id)
            logger.info(f"   📦 Collected {len(stored_photos)} photos for media group {original_media_group_id}")
    
    # Check if staff is sending multiple photos as a media group (USDT receipts)
    # This must be checked BEFORE the text check, because only the first photo has caption
    if message.media_group_id:
        logger.info(f"   📸 Staff media group detected: {message.media_group_id}")
        
        # Initialize media group storage if not exists
        if message.media_group_id not in media_groups:
            # Get original_text from the first photo's caption or reply message
            original_text = message.reply_to_message.text or message.reply_to_message.caption
            staff_text = message.text or message.caption or ""
            
            # If original has no text but staff caption has transaction info, use that
            if not original_text and staff_text:
                tx_info_check = extract_transaction_info(staff_text)
                if tx_info_check.get('type'):
                    original_text = staff_text
                    logger.info(f"   📝 Using staff reply text as transaction info")
            
            if not original_text:
                logger.info(f"   ⏭️ Skipping media group: No transaction text found")
                return
            
            media_groups[message.media_group_id] = {
                'photos': [],
                'message': message,
                'original_text': original_text
            }
            logger.info(f"   📦 Created new media group storage")
        
        # Add this photo to the group
        media_groups[message.media_group_id]['photos'].append(message.photo[-1])
        photo_count = len(media_groups[message.media_group_id]['photos'])
        logger.info(f"   ➕ Added photo to media group. Total photos: {photo_count}")
        
        # Only schedule processing once (from the first photo)
        if photo_count == 1:
            logger.info(f"   ⏰ Scheduling media group processing for {message.media_group_id}")
            asyncio.create_task(process_media_group_delayed(update, context, message.media_group_id))
        
        return
    
    # Single photo reply - check for text
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    
    # If original message has no text, check if staff included transaction info in their reply
    if not original_text:
        staff_text = message.text or message.caption or ""
        if staff_text:
            # Check if staff's message contains transaction info (Buy/Sell)
            tx_info_check = extract_transaction_info(staff_text)
            if tx_info_check.get('type'):
                original_text = staff_text
                logger.info(f"   📝 Using staff reply text as transaction info")
    
    if not original_text:
        logger.info(f"   ⏭️ Skipping: Original message has no text")
        return
    
    logger.info(f"   Original message: '{original_text[:80]}...'")
    
    # Extract transaction info from original text
    tx_info = extract_transaction_info(original_text)
    
    # Check if transaction type is valid (Buy or Sell)
    if not tx_info['type']:
        logger.info(f"   ⏭️ Skipping: Not a Buy/Sell transaction message")
        return
    
    # Allow transactions with 0 or missing amounts - will use OCR to detect
    if tx_info.get('usdt') is None or tx_info.get('mmk') is None or tx_info.get('usdt') == 0 or tx_info.get('mmk') == 0:
        logger.warning(f"   ⚠️ Transaction has invalid amounts (USDT: {tx_info.get('usdt')}, MMK: {tx_info.get('mmk')}) - Will use OCR to detect amounts")
        # Set to 0 if None to avoid errors
        if tx_info.get('usdt') is None:
            tx_info['usdt'] = 0
        if tx_info.get('mmk') is None:
            tx_info['mmk'] = 0
    
    logger.info(f"   🔄 Processing {tx_info['type'].upper()} transaction: {tx_info['usdt']} USDT = {tx_info['mmk']:,.0f} MMK")
    
    if tx_info['type'] == 'buy':
        await process_buy_transaction(update, context, tx_info)
    elif tx_info['type'] == 'sell':
        await process_sell_transaction(update, context, tx_info)

# ============================================================================
# COMMANDS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await send_command_response(
        context,
        "✅ <b>Infinity Balance Bot</b>\n\n"
        "🔧 Independent Mode (No Backend)\n"
        "📊 Balances stored in Telegram\n"
        "👥 Staff-specific balance tracking\n"
        "💰 Configurable USDT receiving account\n"
        "🏦 MMK account verification for accuracy\n\n"
        "<b>Commands:</b>\n"
        "/start - Status and help\n"
        "/balance - Show current balance\n"
        "/load - Load balance from message\n"
        "/set_user - Set user prefix (reply to user's message)\n"
        "/list_users - List all user-prefix mappings\n"
        "/remove_user - Remove user mapping\n\n"
        "<b>USDT Configuration:</b>\n"
        "/set_receiving_usdt_acc - Set USDT receiving account\n"
        "/show_receiving_usdt_acc - Show current receiving account\n\n"
        "<b>MMK Bank Management:</b>\n"
        "/set_mmk_bank - Register MMK bank account\n"
        "/list_mmk_bank - List all registered banks\n"
        "/edit_mmk_bank - Edit existing bank account\n"
        "/remove_mmk_bank - Remove bank account\n\n"
        "<b>System:</b>\n"
        "/test - Test connection and configuration",
        parse_mode='HTML'
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance"""
    balances = context.chat_data.get('balances')
    
    if not balances:
        await send_command_response(context, "❌ No balance loaded")
        return
    
    msg = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
    await send_command_response(context, f"📊 <b>Balance:</b>\n\n<pre>{msg}</pre>", parse_mode='HTML')

async def load_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load balance from replied message"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await send_command_response(context, "Reply to a balance message with /load")
        return
    
    balances = parse_balance_message(update.message.reply_to_message.text)
    
    if balances:
        context.chat_data['balances'] = balances
        thb_count = len(balances.get('thb_banks', []))
        thb_info = f"\nTHB Banks: {thb_count}" if thb_count > 0 else ""
        await send_command_response(
            context,
            f"✅ Loaded!\n\n"
            f"MMK Banks: {len(balances['mmk_banks'])}\n"
            f"USDT Banks: {len(balances['usdt_banks'])}"
            f"{thb_info}"
        )
    else:
        await send_command_response(context, "❌ Could not parse balance")

async def set_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user prefix mapping: /set_user @username prefix_name"""
    message = update.message
    
    # Check if user has admin rights (you can customize this check)
    # For now, anyone can set mappings
    
    if len(context.args) < 2:
        await send_command_response(context, 
            "Usage: /set_user @username prefix_name\n\n"
            "Examples:\n"
            "/set_user @john San\n"
            "/set_user @mary TZT\n"
            "/set_user @bob MMN\n"
            "/set_user @alice NDT"
        )
        return
    
    username_arg = context.args[0]
    prefix_name = context.args[1]
    
    # Extract user_id from mention or username
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                # @username format - we need to get user_id from the mentioned user
                # This requires the user to have interacted with the bot before
                await send_command_response(context, 
                    "⚠️ Please reply to a message from the user instead, or provide their user ID.\n"
                    "Usage: /set_user <user_id> <prefix_name>"
                )
                return
            elif entity.type == "text_mention":
                # User object is available
                user_id = entity.user.id
                username = entity.user.username or entity.user.first_name
                set_user_prefix(user_id, prefix_name, username)
                await send_command_response(context, 
                    f"✅ Set prefix '{prefix_name}' for user {username} (ID: {user_id})"
                )
                return
    
    # Try to parse as user_id directly
    try:
        user_id = int(username_arg)
        set_user_prefix(user_id, prefix_name)
        await send_command_response(context, 
            f"✅ Set prefix '{prefix_name}' for user ID: {user_id}"
        )
    except ValueError:
        await send_command_response(context, 
            "❌ Invalid format. Please use:\n"
            "/set_user <user_id> <prefix_name>\n\n"
            "Or reply to a user's message with:\n"
            "/set_user <prefix_name>"
        )

async def set_user_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user prefix by replying to their message: reply with /set_user prefix_name"""
    message = update.message
    
    if not message.reply_to_message:
        await send_command_response(context, "Please reply to a user's message")
        return
    
    if len(context.args) < 1:
        await send_command_response(context, "Usage: Reply to user's message with /set_user <prefix_name>")
        return
    
    prefix_name = context.args[0]
    user_id = message.reply_to_message.from_user.id
    username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
    
    set_user_prefix(user_id, prefix_name, username)
    await send_command_response(context, 
        f"✅ Set prefix '{prefix_name}' for @{username} (ID: {user_id})"
    )

async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all user-prefix mappings"""
    users = get_all_user_prefixes()
    
    if not users:
        await send_command_response(context, 
            "📋 <b>User-Prefix Mappings</b>\n\n"
            "No users registered yet.\n\n"
            "Use /set_user to register a user.",
            parse_mode='HTML'
        )
        return
    
    message = "📋 <b>User-Prefix Mappings</b>\n\n"
    
    for idx, user in enumerate(users, 1):
        user_id = user['user_id']
        prefix_name = user['prefix_name']
        username = user['username'] or 'Unknown'
        
        message += f"<b>{idx}. {prefix_name}</b>\n"
        message += f"   User: @{username}\n"
        message += f"   ID: <code>{user_id}</code>\n\n"
    
    message += "<b>Commands:</b>\n"
    message += "• /set_user - Map user to prefix\n"
    message += "• /list_users - Show all mappings\n"
    message += "• /remove_user - Remove user mapping"
    
    await send_command_response(context, message, parse_mode='HTML')

async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user-prefix mapping"""
    if len(context.args) < 1:
        await send_command_response(context, 
            "📋 <b>Remove User Mapping</b>\n\n"
            "<b>Usage:</b>\n"
            "/remove_user &lt;user_id&gt;\n\n"
            "<b>Example:</b>\n"
            "/remove_user 123456789\n\n"
            "Use /list_users to see all user IDs.",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
    except ValueError:
        await send_command_response(context, "❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    # Check if user exists
    existing_prefix = get_user_prefix(user_id)
    if not existing_prefix:
        await send_command_response(context, f"❌ User ID {user_id} not found in mappings.")
        return
    
    # Remove from database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_prefixes WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Removed user mapping: {user_id} → {existing_prefix}")
    
    await send_command_response(context, 
        f"✅ <b>User Mapping Removed!</b>\n\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Prefix:</b> {existing_prefix}",
        parse_mode='HTML'
    )

async def set_receiving_usdt_acc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the receiving USDT account for buy transactions"""
    message = update.message
    
    if len(context.args) < 1:
        # Show current setting
        current_account = get_receiving_usdt_account()
        await send_command_response(context, 
            f"📊 <b>Current Receiving USDT Account:</b>\n"
            f"<code>{current_account}</code>\n\n"
            f"<b>Usage:</b>\n"
            f"/set_receiving_usdt_acc &lt;account_name&gt;\n\n"
            f"<b>Example:</b>\n"
            f"/set_receiving_usdt_acc ACT(Wallet)\n"
            f"/set_receiving_usdt_acc San(Swift)",
            parse_mode='HTML'
        )
        return
    
    account_name = ' '.join(context.args)
    set_receiving_usdt_account(account_name)
    
    await send_command_response(context, 
        f"✅ <b>Receiving USDT Account Updated!</b>\n\n"
        f"New account: <code>{account_name}</code>\n\n"
        f"All buy transactions will now add USDT to this account.",
        parse_mode='HTML'
    )

async def set_mmk_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set MMK bank account details for verification
    Usage: /set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
    """
    message = update.message
    
    if len(context.args) < 1:
        # Show current settings
        accounts = get_all_mmk_bank_accounts()
        if accounts:
            account_list = "\n".join([
                f"• <code>{acc['bank_name']}</code>\n"
                f"  Account: {acc['account_number']}\n"
                f"  Holder: {acc['account_holder']}"
                for acc in accounts
            ])
            await send_command_response(context, 
                f"🏦 <b>Registered MMK Bank Accounts:</b>\n\n"
                f"{account_list}\n\n"
                f"<b>Usage:</b>\n"
                f"/set_mmk_bank &lt;bank_name&gt; | &lt;account_number&gt; | &lt;holder_name&gt;\n\n"
                f"<b>Examples:</b>\n"
                f"/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR\n"
                f"/set_mmk_bank San(CB) | 02251009000260 42 | CHAW SU THU ZAR\n"
                f"/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal\n"
                f"/set_mmk_bank San(Wave) | 09783275630 | San Wint Htal",
                parse_mode='HTML'
            )
        else:
            await send_command_response(context, 
                f"🏦 <b>No MMK Bank Accounts Registered</b>\n\n"
                f"<b>Usage:</b>\n"
                f"/set_mmk_bank &lt;bank_name&gt; | &lt;account_number&gt; | &lt;holder_name&gt;\n\n"
                f"<b>Examples:</b>\n"
                f"/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR\n"
                f"/set_mmk_bank San(CB) | 02251009000260 42 | CHAW SU THU ZAR\n"
                f"/set_mmk_bank San(Kpay P) | 09783275630 | San Wint Htal\n"
                f"/set_mmk_bank San(Wave) | 09783275630 | San Wint Htal",
                parse_mode='HTML'
            )
        return
    
    # Parse command: /set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR
    full_text = ' '.join(context.args)
    parts = [p.strip() for p in full_text.split('|')]
    
    if len(parts) != 3:
        await send_command_response(context, 
            f"❌ <b>Invalid Format!</b>\n\n"
            f"<b>Usage:</b>\n"
            f"/set_mmk_bank &lt;bank_name&gt; | &lt;account_number&gt; | &lt;holder_name&gt;\n\n"
            f"<b>Example:</b>\n"
            f"/set_mmk_bank San(KBZ) | 27251127201844001 | CHAW SU THU ZAR\n\n"
            f"Make sure to use | (pipe) to separate the three parts.",
            parse_mode='HTML'
        )
        return
    
    bank_name = parts[0]
    account_number = parts[1].replace(' ', '')  # Remove spaces
    account_holder = parts[2]
    
    # Validate bank name format
    if '(' not in bank_name or ')' not in bank_name:
        await message.reply_text(
            f"❌ <b>Invalid Bank Name Format!</b>\n\n"
            f"Bank name should be in format: <code>Prefix(BankName)</code>\n\n"
            f"<b>Examples:</b>\n"
            f"• San(KBZ)\n"
            f"• San(CB)\n"
            f"• TZT(Wave)",
            parse_mode='HTML'
        )
        return
    
    # Save to database
    set_mmk_bank_account(bank_name, account_number, account_holder)
    
    await message.reply_text(
        f"✅ <b>MMK Bank Account Registered!</b>\n\n"
        f"<b>Bank:</b> <code>{bank_name}</code>\n"
        f"<b>Account:</b> <code>{account_number}</code>\n"
        f"<b>Holder:</b> <code>{account_holder}</code>\n\n"
        f"The bot will now verify recipient details when processing buy transactions for this account.",
        parse_mode='HTML'
    )

async def edit_mmk_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit existing MMK bank account details
    Usage: /edit_mmk_bank San(KBZ) | NEW_ACCOUNT | NEW_HOLDER
    """
    message = update.message
    
    if len(context.args) < 1:
        # Show current settings
        accounts = get_all_mmk_bank_accounts()
        if accounts:
            account_list = "\n".join([
                f"• <code>{acc['bank_name']}</code>\n"
                f"  Account: {acc['account_number']}\n"
                f"  Holder: {acc['account_holder']}"
                for acc in accounts
            ])
            await send_command_response(context, 
                f"🏦 <b>Edit MMK Bank Account:</b>\n\n"
                f"<b>Current Accounts:</b>\n{account_list}\n\n"
                f"<b>Usage:</b>\n"
                f"/edit_mmk_bank &lt;bank_name&gt; | &lt;new_account&gt; | &lt;new_holder&gt;\n\n"
                f"<b>Example:</b>\n"
                f"/edit_mmk_bank San(KBZ) | 99999999999999999 | NEW NAME",
                parse_mode='HTML'
            )
        else:
            await send_command_response(context, 
                f"🏦 <b>No MMK Bank Accounts to Edit</b>\n\n"
                f"Use /set_mmk_bank to add accounts first.",
                parse_mode='HTML'
            )
        return
    
    # Parse command
    full_text = ' '.join(context.args)
    parts = [p.strip() for p in full_text.split('|')]
    
    if len(parts) != 3:
        await send_command_response(context, 
            f"❌ <b>Invalid Format!</b>\n\n"
            f"<b>Usage:</b>\n"
            f"/edit_mmk_bank &lt;bank_name&gt; | &lt;new_account&gt; | &lt;new_holder&gt;\n\n"
            f"<b>Example:</b>\n"
            f"/edit_mmk_bank San(KBZ) | 99999999999999999 | NEW NAME",
            parse_mode='HTML'
        )
        return
    
    bank_name = parts[0]
    new_account_number = parts[1].replace(' ', '')
    new_account_holder = parts[2]
    
    # Check if bank exists
    existing = get_mmk_bank_account(bank_name)
    if not existing:
        await message.reply_text(
            f"❌ <b>Bank Not Found!</b>\n\n"
            f"<code>{bank_name}</code> is not registered.\n\n"
            f"Use /set_mmk_bank to add it first.",
            parse_mode='HTML'
        )
        return
    
    # Update the account
    set_mmk_bank_account(bank_name, new_account_number, new_account_holder)
    
    await message.reply_text(
        f"✅ <b>MMK Bank Account Updated!</b>\n\n"
        f"<b>Bank:</b> <code>{bank_name}</code>\n\n"
        f"<b>Old Details:</b>\n"
        f"Account: {existing['account_number']}\n"
        f"Holder: {existing['account_holder']}\n\n"
        f"<b>New Details:</b>\n"
        f"Account: {new_account_number}\n"
        f"Holder: {new_account_holder}",
        parse_mode='HTML'
    )

async def remove_mmk_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove MMK bank account
    Usage: /remove_mmk_bank San(KBZ)
    """
    message = update.message
    
    if len(context.args) < 1:
        # Show current settings
        accounts = get_all_mmk_bank_accounts()
        if accounts:
            account_list = "\n".join([
                f"• <code>{acc['bank_name']}</code>"
                for acc in accounts
            ])
            await send_command_response(context, 
                f"🏦 <b>Remove MMK Bank Account:</b>\n\n"
                f"<b>Current Accounts:</b>\n{account_list}\n\n"
                f"<b>Usage:</b>\n"
                f"/remove_mmk_bank &lt;bank_name&gt;\n\n"
                f"<b>Example:</b>\n"
                f"/remove_mmk_bank San(KBZ)",
                parse_mode='HTML'
            )
        else:
            await send_command_response(context, 
                f"🏦 <b>No MMK Bank Accounts to Remove</b>",
                parse_mode='HTML'
            )
        return
    
    bank_name = ' '.join(context.args)
    
    # Check if bank exists
    existing = get_mmk_bank_account(bank_name)
    if not existing:
        await send_command_response(context, 
            f"❌ <b>Bank Not Found!</b>\n\n"
            f"<code>{bank_name}</code> is not registered.",
            parse_mode='HTML'
        )
        return
    
    # Remove from database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM mmk_bank_accounts WHERE bank_name = ?', (bank_name,))
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Removed MMK bank account: {bank_name}")
    
    await message.reply_text(
        f"✅ <b>MMK Bank Account Removed!</b>\n\n"
        f"<b>Bank:</b> <code>{bank_name}</code>\n"
        f"<b>Account:</b> {existing['account_number']}\n"
        f"<b>Holder:</b> {existing['account_holder']}\n\n"
        f"This account has been removed from the system.",
        parse_mode='HTML'
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test command to verify group and topic configuration"""
    message = update.message
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.message_thread_id else None
    
    # Normalize thread_id: treat None as 1 for General topic
    normalized_thread_id = thread_id if thread_id is not None else 1
    
    # Determine USDT transfers location
    if not USDT_TRANSFERS_TOPIC_ID or USDT_TRANSFERS_TOPIC_ID <= 1:
        usdt_location = "Main Chat (Topic 1/General)"
    else:
        usdt_location = f"Topic {USDT_TRANSFERS_TOPIC_ID}"
    
    balance_location = "Main Chat (No Topic)" if not AUTO_BALANCE_TOPIC_ID else f"Topic {AUTO_BALANCE_TOPIC_ID}"
    
    test_result = f"""🧪 <b>Connection Test</b>

<b>Current Message Info:</b>
• Chat ID: <code>{chat_id}</code>
• Thread ID: <code>{thread_id}</code> (normalized: {normalized_thread_id})
• Chat Type: {message.chat.type}

<b>Bot Configuration:</b>
• Target Group: <code>{TARGET_GROUP_ID}</code>
• USDT Transfers: {usdt_location}
• Auto Balance: {balance_location}

<b>Connection Status:</b>"""
    
    # Check if in correct group
    if chat_id == TARGET_GROUP_ID:
        test_result += "\n✅ In correct group"
    else:
        test_result += f"\n❌ Wrong group (expected {TARGET_GROUP_ID})"
    
    # Check if in correct location for USDT transfers
    if USDT_TRANSFERS_TOPIC_ID and USDT_TRANSFERS_TOPIC_ID > 1:
        # Specific topic mode (not main chat)
        if normalized_thread_id == USDT_TRANSFERS_TOPIC_ID:
            test_result += "\n✅ In USDT Transfers topic"
        elif normalized_thread_id == AUTO_BALANCE_TOPIC_ID:
            test_result += "\n✅ In Auto Balance topic"
        else:
            test_result += f"\n⚠️ In different topic (ID: {normalized_thread_id}, expected {USDT_TRANSFERS_TOPIC_ID})"
    else:
        # Main chat mode (topic 1 or None)
        if normalized_thread_id == 1:
            test_result += "\n✅ In main chat/General topic (USDT transfers location)"
        elif normalized_thread_id == AUTO_BALANCE_TOPIC_ID:
            test_result += "\n✅ In Auto Balance topic"
        else:
            test_result += f"\n⚠️ In topic {normalized_thread_id} (USDT transfers use main chat/topic 1)"
    
    test_result += "\n\n<b>Tip:</b> Send this command in different locations to verify configuration."
    
    await message.reply_text(test_result, parse_mode='HTML')

async def list_mmk_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered MMK bank accounts"""
    accounts = get_all_mmk_bank_accounts()
    
    if not accounts:
        await send_command_response(context, 
            "📋 <b>Registered MMK Bank Accounts</b>\n\n"
            "No banks registered yet.\n\n"
            "Use /set_mmk_bank to register a bank account.",
            parse_mode='HTML'
        )
        return
    
    message = "📋 <b>Registered MMK Bank Accounts</b>\n\n"
    
    for idx, acc in enumerate(accounts, 1):
        bank_name = acc['bank_name']
        account_number = acc['account_number']
        account_holder = acc['account_holder']
        
        # Mask middle digits of account number for security
        if len(account_number) > 8:
            masked_account = account_number[:4] + "****" + account_number[-4:]
        else:
            masked_account = account_number
        
        message += f"<b>{idx}. {bank_name}</b>\n"
        message += f"   Account: <code>{masked_account}</code>\n"
        message += f"   Holder: {account_holder}\n\n"
    
    message += "<b>Commands:</b>\n"
    message += "• /set_mmk_bank - Register new bank\n"
    message += "• /edit_mmk_bank - Edit existing bank\n"
    message += "• /remove_mmk_bank - Remove bank"
    
    await send_command_response(context, message, parse_mode='HTML')

async def show_receiving_usdt_acc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current receiving USDT account for buy transactions"""
    receiving_account = get_receiving_usdt_account()
    
    message = (
        "💰 <b>USDT Receiving Account Configuration</b>\n\n"
        f"<b>Current Account:</b> <code>{receiving_account}</code>\n\n"
        "<b>Purpose:</b>\n"
        "This account receives USDT when customers buy USDT from us.\n\n"
        "<b>How it works:</b>\n"
        "• Customer: Buy 100 USDT = 2,500,000 MMK\n"
        "• Staff sends MMK to customer\n"
        f"• Bot adds 100 USDT to <code>{receiving_account}</code>\n\n"
        "<b>Note:</b> For sell transactions, USDT is reduced from staff-specific accounts "
        "(Binance/Swift/Wallet) based on the receipt type.\n\n"
        "<b>Change Account:</b>\n"
        "Use /set_receiving_usdt_acc to change the receiving account.\n"
        "Example: <code>/set_receiving_usdt_acc ACT(Wallet)</code>"
    )
    
    await send_command_response(context, message, parse_mode='HTML')

# ============================================================================
# MAIN
# ============================================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Log the error but don't crash - network errors are transient
    import traceback
    logger.error("".join(traceback.format_exception(None, context.error, context.error.__traceback__)))

def main():
    """Start bot"""
    # Initialize database
    init_database()
    
    # Build application with connection pool settings and timeouts
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("load", load_command))
    app.add_handler(CommandHandler("set_user", set_user_reply_command))
    app.add_handler(CommandHandler("list_users", list_users_command))
    app.add_handler(CommandHandler("remove_user", remove_user_command))
    app.add_handler(CommandHandler("set_receiving_usdt_acc", set_receiving_usdt_acc_command))
    app.add_handler(CommandHandler("set_mmk_bank", set_mmk_bank_command))
    app.add_handler(CommandHandler("edit_mmk_bank", edit_mmk_bank_command))
    app.add_handler(CommandHandler("remove_mmk_bank", remove_mmk_bank_command))
    app.add_handler(CommandHandler("list_mmk_bank", list_mmk_bank_command))
    app.add_handler(CommandHandler("show_receiving_usdt_acc", show_receiving_usdt_acc_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    
    logger.info("🤖 Infinity Balance Bot Started")
    logger.info(f"📱 Group: {TARGET_GROUP_ID}")
    logger.info(f"💱 USDT Topic: {USDT_TRANSFERS_TOPIC_ID}")
    logger.info(f"📊 Balance Topic: {AUTO_BALANCE_TOPIC_ID}")
    logger.info(f"🏦 Accounts Matter Topic: {ACCOUNTS_MATTER_TOPIC_ID}")
    
    # Run with error handling for network issues
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        # Automatically retry on network errors
        close_loop=False
    )

if __name__ == '__main__':
    main()
