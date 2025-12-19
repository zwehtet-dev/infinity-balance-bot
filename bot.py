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

# Storage for tracking multiple photo replies to same transaction
# Format: {original_message_id: {'amounts': [amount1, amount2], 'bank': bank_obj, 'expected': amount, 'type': 'buy/sell'}}
pending_transactions = {}

# Storage for media groups (bulk photos sent together)
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
        import traceback
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
        result = re.sub(r'```json\s*|\s*```', '', result)
        
        json_start = result.find('{')
        json_end = result.rfind('}')
        if json_start != -1 and json_end != -1:
            result = result[json_start:json_end + 1]
        
        data = json.loads(result)
        
        # Ensure all values are positive and properly formatted
        amount = abs(float(data.get('amount', 0)))
        network_fee = abs(float(data.get('network_fee', 0)))
        bank_type = data.get('bank_type', 'wallet').lower()
        
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
        import traceback
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
        import traceback
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
    """BUY: User buys USDT, we send MMK (supports multiple receipts)"""
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
    
    original_message_id = message.reply_to_message.message_id
    
    # Get photo
    photo = message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
    
    # For buy process: Use simple bank type detection (not account verification)
    # Just detect bank type (1-11) and match with staff prefix
    result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
    
    if not result:
        await send_alert(message, "❌ Could not detect bank/amount", context)
        return
    
    detected_mmk = result['amount']
    detected_bank = result['bank']
    
    logger.info(f"Buy: Detected {detected_mmk:,.0f} MMK from {detected_bank['bank_name']}")
    
    # Initialize or update pending transaction
    if original_message_id not in pending_transactions:
        pending_transactions[original_message_id] = {
            'amounts': [],
            'bank': detected_bank,
            'expected_mmk': tx_info['mmk'],
            'expected_usdt': tx_info['usdt'],
            'type': 'buy',
            'user_prefix': user_prefix
        }
    
    # Add this amount to the list
    pending_transactions[original_message_id]['amounts'].append(detected_mmk)
    total_detected_mmk = sum(pending_transactions[original_message_id]['amounts'])
    photo_count = len(pending_transactions[original_message_id]['amounts'])
    
    logger.info(f"Buy transaction {original_message_id}: Added {detected_mmk:,.0f}, Total: {total_detected_mmk:,.0f} from {photo_count} photo(s)")
    
    # Check if total amount matches (allow 100 MMK difference)
    if abs(total_detected_mmk - tx_info['mmk']) > 100:
        # await message.reply_text(
        #     f"📝 Received {photo_count} photo(s)\n"
        #     f"Total: {total_detected_mmk:,.0f} MMK\n"
        #     f"Expected: {tx_info['mmk']:,.0f} MMK\n\n"
        #     f"⏳ Send more photos if needed"
        # )
        logger.info(f"Received {photo_count} photo(s), Total: {total_detected_mmk:,.0f} MMK, Expected: {tx_info['mmk']:,.0f} MMK - waiting for more photos")
        return
    
    # Amount matches! Process the transaction
    # await message.reply_text(f"✅ Total amount matched!\n{photo_count} photo(s): {total_detected_mmk:,.0f} MMK\n\nProcessing...")
    
    # Check if sufficient balance before reducing
    bank_found = False
    for bank in balances['mmk_banks']:
        if banks_match(bank['bank_name'], detected_bank['bank_name']):
            bank_found = True
            if bank['amount'] < total_detected_mmk:
                # await message.reply_text(
                #     f"❌ Insufficient balance!\n\n"
                #     f"{bank['bank_name']}: {bank['amount']:,.0f} MMK\n"
                #     f"Required: {total_detected_mmk:,.0f} MMK\n"
                #     f"Shortage: {total_detected_mmk - bank['amount']:,.0f} MMK"
                # )
                logger.error(f"Insufficient balance! {bank['bank_name']}: {bank['amount']:,.0f} MMK, Required: {total_detected_mmk:,.0f} MMK, Shortage: {total_detected_mmk - bank['amount']:,.0f} MMK")
                # Clean up pending transaction
                if original_message_id in pending_transactions:
                    del pending_transactions[original_message_id]
                return
            bank['amount'] -= total_detected_mmk
            break
    
    if not bank_found:
        await send_alert(message, f"❌ Bank not found: {detected_bank['bank_name']}", context)
        if original_message_id in pending_transactions:
            del pending_transactions[original_message_id]
        return
    
    # Update USDT to the receiving account (not staff-specific)
    receiving_usdt_account = get_receiving_usdt_account()
    usdt_updated = False
    
    for bank in balances['usdt_banks']:
        if banks_match(bank['bank_name'], receiving_usdt_account):
            bank['amount'] += tx_info['usdt']
            usdt_updated = True
            logger.info(f"Added {tx_info['usdt']:.4f} USDT to receiving account: {receiving_usdt_account}")
            break
    
    if not usdt_updated:
        await send_alert(message, f"⚠️ Warning: Receiving USDT account '{receiving_usdt_account}' not found in balance. USDT not added.", context)
    
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
    #     f"✅ Buy processed!\n\n"
    #     f"MMK: -{total_detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
    #     f"USDT: +{tx_info['usdt']:.4f}"
    # )
    
    # Clean up pending transaction
    if original_message_id in pending_transactions:
        del pending_transactions[original_message_id]

async def process_sell_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict):
    """SELL: User sells USDT, we receive MMK (supports multiple receipts)"""
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
    
    # Get user's MMK receipt
    original_message = message.reply_to_message
    if not original_message or not original_message.photo:
        await send_alert(message, "❌ Original message has no receipt", context)
        return
    
    # OCR user's receipt (only once, not accumulated)
    user_photo = original_message.photo[-1]
    user_file = await context.bot.get_file(user_photo.file_id)
    user_bytes = await user_file.download_as_bytearray()
    user_base64 = base64.b64encode(user_bytes).decode('utf-8')
    
    user_result = await ocr_detect_mmk_bank_and_amount(user_base64, balances['mmk_banks'], user_prefix)
    
    if not user_result:
        await send_alert(message, "❌ Could not detect bank/amount from user receipt", context)
        return
    
    detected_mmk = user_result['amount']
    detected_bank = user_result['bank']
    
    # Verify MMK
    if abs(detected_mmk - tx_info['mmk']) > 100:
        # await message.reply_text(
        #     f"⚠️ MMK mismatch!\n"
        #     f"Expected: {tx_info['mmk']:,.0f}\n"
        #     f"Detected: {detected_mmk:,.0f}"
        # )
        logger.error(f"MMK mismatch! Expected: {tx_info['mmk']:,.0f}, Detected: {detected_mmk:,.0f}")
        return
    
    # Get staff's USDT receipt(s) - support multiple photos
    if not message.photo:
        await send_alert(message, "❌ No USDT receipt", context)
        return
    
    original_message_id = message.reply_to_message.message_id
    
    staff_photo = message.photo[-1]
    staff_file = await context.bot.get_file(staff_photo.file_id)
    staff_bytes = await staff_file.download_as_bytearray()
    staff_base64 = base64.b64encode(staff_bytes).decode('utf-8')
    
    # Extract USDT with network fee and bank type
    usdt_result = await ocr_extract_usdt_with_fee(staff_base64)
    
    if not usdt_result:
        await send_alert(message, "❌ Could not detect USDT amount", context)
        return
    
    detected_usdt = usdt_result['total_amount']  # Use total (amount + network fee)
    bank_type = usdt_result['bank_type']  # 'swift' or 'wallet'
    
    logger.info(f"Detected USDT: {detected_usdt:.4f} (amount: {usdt_result['amount']:.4f} + fee: {usdt_result['network_fee']:.4f}) from {bank_type}")
    
    # Initialize or update pending transaction for sell
    if original_message_id not in pending_transactions:
        pending_transactions[original_message_id] = {
            'amounts': [],
            'mmk_bank': detected_bank,
            'detected_mmk': detected_mmk,
            'expected_usdt': tx_info['usdt'],
            'type': 'sell',
            'user_prefix': user_prefix,
            'bank_type': bank_type  # Store bank type (swift/wallet)
        }
    
    # Add this USDT amount to the list
    pending_transactions[original_message_id]['amounts'].append(detected_usdt)
    total_detected_usdt = sum(pending_transactions[original_message_id]['amounts'])
    photo_count = len(pending_transactions[original_message_id]['amounts'])
    
    logger.info(f"Sell transaction {original_message_id}: Added {detected_usdt:.4f} USDT, Total: {total_detected_usdt:.4f} from {photo_count} photo(s)")
    
    # Check if USDT amount matches (allow 0.03 tolerance for USDT)
    if abs(total_detected_usdt - tx_info['usdt']) > 0.03:
        # await message.reply_text(
        #     f"📝 Received {photo_count} photo(s)\n"
        #     f"Total: {total_detected_usdt:.4f} USDT\n"
        #     f"Expected: {tx_info['usdt']:.4f} USDT\n\n"
        #     f"⏳ Send more photos if needed"
        # )
        logger.info(f"Received {photo_count} photo(s), Total: {total_detected_usdt:.4f} USDT, Expected: {tx_info['usdt']:.4f} USDT - waiting for more photos")
        return
    
    # Amount matches! Process the transaction
    # await message.reply_text(f"✅ Total amount matched!\n{photo_count} photo(s): {total_detected_usdt:.4f} USDT\n\nProcessing...")
    
    # Update balances for the specific staff member's bank
    for bank in balances['mmk_banks']:
        if banks_match(bank['bank_name'], detected_bank['bank_name']):
            bank['amount'] += detected_mmk
            break
    
    # Update USDT for the specific staff member's Swift or Wallet account
    usdt_updated = False
    stored_bank_type = pending_transactions[original_message_id].get('bank_type', 'wallet')
    
    # Find the staff's USDT bank that matches the bank type
    for bank in balances['usdt_banks']:
        if bank.get('prefix') == user_prefix:
            # Check if bank name contains Swift, Wallet, or Binance based on detected type
            bank_name_lower = bank['bank_name'].lower()
            is_swift = 'swift' in bank_name_lower
            is_wallet = 'wallet' in bank_name_lower
            is_binance = 'binance' in bank_name_lower
            
            # Match bank type
            type_matches = (
                (stored_bank_type == 'swift' and is_swift) or
                (stored_bank_type == 'wallet' and is_wallet) or
                (stored_bank_type == 'binance' and is_binance)
            )
            
            if type_matches:
                # Check if sufficient USDT balance
                if bank['amount'] < total_detected_usdt:
                    # await message.reply_text(
                    #     f"❌ Insufficient USDT balance!\n\n"
                    #     f"{bank['bank_name']}: {bank['amount']:.4f} USDT\n"
                    #     f"Required: {total_detected_usdt:.4f} USDT\n"
                    #     f"Shortage: {total_detected_usdt - bank['amount']:.4f} USDT"
                    # )
                    logger.error(f"Insufficient USDT balance! {bank['bank_name']}: {bank['amount']:.4f} USDT, Required: {total_detected_usdt:.4f} USDT, Shortage: {total_detected_usdt - bank['amount']:.4f} USDT")
                    # Clean up pending transaction
                    if original_message_id in pending_transactions:
                        del pending_transactions[original_message_id]
                    return
                bank['amount'] -= total_detected_usdt
                usdt_updated = True
                logger.info(f"Reduced {total_detected_usdt:.4f} USDT from {bank['bank_name']} ({stored_bank_type})")
                break
    
    if not usdt_updated:
        logger.warning(f"No USDT {stored_bank_type} bank found for prefix '{user_prefix}'")
    
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
    #     f"✅ Sell processed!\n\n"
    #     f"MMK: +{detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
    #     f"USDT: -{total_detected_usdt:.4f}"
    # )
    
    # Clean up pending transaction
    if original_message_id in pending_transactions:
        del pending_transactions[original_message_id]

# ============================================================================
# INTERNAL TRANSFER PROCESSING
# ============================================================================

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
        import traceback
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
        # await message.reply_text(
        #     f"⚠️ Insufficient balance!\n"
        #     f"{from_full_name}: {from_bank_obj['amount']:,.2f}\n"
        #     f"Transfer: {amount:,.2f}"
        # )
        logger.error(f"Insufficient balance! {from_full_name}: {from_bank_obj['amount']:,.2f}, Transfer: {amount:,.2f}")
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
    
    # await message.reply_text(
    #     f"✅ Internal transfer processed!\n\n"
    #     f"From: {from_full_name}\n"
    #     f"To: {to_full_name}\n"
    #     f"Amount: {amount:,.2f}\n\n"
    #     f"New balances:\n"
    #     f"{from_full_name}: {from_bank_obj['amount']:,.2f}\n"
    #     f"{to_full_name}: {to_bank_obj['amount']:,.2f}"
    # )

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

async def process_media_group_delayed(update: Update, context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
    """Process a media group after a short delay to ensure all photos are collected"""
    import asyncio
    
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
    
    if not tx_info['type'] or not tx_info['usdt'] or not tx_info['mmk']:
        logger.info(f"❌ Original message is not a valid buy/sell message")
        if media_group_id in media_groups:
            del media_groups[media_group_id]
        if media_group_id in media_group_locks:
            del media_group_locks[media_group_id]
        return
    
    try:
        if tx_info['type'] == 'buy':
            await process_buy_transaction_bulk(update, context, tx_info, photos, message)
        elif tx_info['type'] == 'sell':
            await process_sell_transaction_bulk(update, context, tx_info, photos, message)
    except Exception as e:
        logger.error(f"Error processing media group: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Clean up media group
        if media_group_id in media_groups:
            del media_groups[media_group_id]
        if media_group_id in media_group_locks:
            del media_group_locks[media_group_id]

async def process_buy_transaction_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict, photos: list, message):
    """Process BUY transaction with multiple photos sent as media group"""
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
    
    # await message.reply_text(f"📸 Processing {len(photos)} photos...")
    
    # For buy process: Use simple bank type detection (not account verification)
    total_detected_mmk = 0
    detected_bank = None
    
    for idx, photo in enumerate(photos, 1):
        logger.info(f"Processing bulk photo {idx}/{len(photos)}")
        
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'], user_prefix)
        
        if not result or not result['amount']:
            logger.warning(f"Could not process bulk photo {idx}")
            continue
        
        detected_mmk = result['amount']
        photo_bank = result['bank']
        
        total_detected_mmk += detected_mmk
        logger.info(f"Bulk photo {idx}: {detected_mmk:,.0f} MMK from {photo_bank['bank_name']}")
        
        if photo_bank and not detected_bank:
            detected_bank = photo_bank
    
    if not detected_bank:
        await send_alert(message, "❌ Could not detect bank from receipts", context)
        return
    
    logger.info(f"Bulk processing complete: Total {total_detected_mmk:,.0f} MMK from {len(photos)} photos")
    
    # Check if total amount matches
    if abs(total_detected_mmk - tx_info['mmk']) > 100:
        # await message.reply_text(
        #     f"⚠️ Amount mismatch!\n"
        #     f"Expected: {tx_info['mmk']:,.0f} MMK\n"
        #     f"Detected: {total_detected_mmk:,.0f} MMK (from {len(photos)} photos)"
        # )
        logger.error(f"Amount mismatch! Expected: {tx_info['mmk']:,.0f} MMK, Detected: {total_detected_mmk:,.0f} MMK (from {len(photos)} photos)")
        return
    
    # Amount matches! Process the transaction
    # await message.reply_text(f"✅ Total amount matched!\n{len(photos)} photos: {total_detected_mmk:,.0f} MMK\n\nProcessing...")
    
    # Check if sufficient balance before reducing
    bank_found = False
    for bank in balances['mmk_banks']:
        if banks_match(bank['bank_name'], detected_bank['bank_name']):
            bank_found = True
            if bank['amount'] < total_detected_mmk:
                # await message.reply_text(
                #     f"❌ Insufficient balance!\n\n"
                #     f"{bank['bank_name']}: {bank['amount']:,.0f} MMK\n"
                #     f"Required: {total_detected_mmk:,.0f} MMK\n"
                #     f"Shortage: {total_detected_mmk - bank['amount']:,.0f} MMK"
                # )
                logger.error(f"Insufficient balance! {bank['bank_name']}: {bank['amount']:,.0f} MMK, Required: {total_detected_mmk:,.0f} MMK, Shortage: {total_detected_mmk - bank['amount']:,.0f} MMK")
                return
            bank['amount'] -= total_detected_mmk
            break
    
    if not bank_found:
        await send_alert(message, f"❌ Bank not found: {detected_bank['bank_name']}", context)
        return
    
    # Update USDT to the receiving account (not staff-specific)
    receiving_usdt_account = get_receiving_usdt_account()
    usdt_updated = False
    
    for bank in balances['usdt_banks']:
        if banks_match(bank['bank_name'], receiving_usdt_account):
            bank['amount'] += tx_info['usdt']
            usdt_updated = True
            logger.info(f"Added {tx_info['usdt']:.4f} USDT to receiving account: {receiving_usdt_account}")
            break
    
    if not usdt_updated:
        await send_alert(message, f"⚠️ Warning: Receiving USDT account '{receiving_usdt_account}' not found in balance. USDT not added.", context)
    
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
    #     f"✅ Buy processed!\n\n"
    #     f"MMK: -{total_detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
    #     f"USDT: +{tx_info['usdt']:.4f}"
    # )

async def process_sell_transaction_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict, photos: list, message):
    """Process SELL transaction with multiple USDT photos sent as media group"""
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
    
    # Get user's MMK receipt
    original_message = message.reply_to_message
    if not original_message or not original_message.photo:
        await send_alert(message, "❌ Original message has no receipt", context)
        return
    
    # OCR user's receipt
    user_photo = original_message.photo[-1]
    user_file = await context.bot.get_file(user_photo.file_id)
    user_bytes = await user_file.download_as_bytearray()
    user_base64 = base64.b64encode(user_bytes).decode('utf-8')
    
    user_result = await ocr_detect_mmk_bank_and_amount(user_base64, balances['mmk_banks'], user_prefix)
    
    if not user_result:
        await send_alert(message, "❌ Could not detect bank/amount from user receipt", context)
        return
    
    detected_mmk = user_result['amount']
    detected_bank = user_result['bank']
    
    # Verify MMK
    if abs(detected_mmk - tx_info['mmk']) > 100:
        # await message.reply_text(
        #     f"⚠️ MMK mismatch!\n"
        #     f"Expected: {tx_info['mmk']:,.0f}\n"
        #     f"Detected: {detected_mmk:,.0f}"
        # )
        logger.error(f"MMK mismatch! Expected: {tx_info['mmk']:,.0f}, Detected: {detected_mmk:,.0f}")
        return
    
    # Process all USDT photos in bulk
    # await message.reply_text(f"📸 Processing {len(photos)} USDT photos...")
    
    total_detected_usdt = 0
    detected_bank_type = None
    
    for idx, photo in enumerate(photos, 1):
        logger.info(f"Processing bulk USDT photo {idx}/{len(photos)}")
        
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Use new USDT OCR with network fee detection
        usdt_result = await ocr_extract_usdt_with_fee(photo_base64)
        
        if not usdt_result:
            logger.warning(f"Could not process bulk USDT photo {idx}")
            continue
        
        detected_usdt = usdt_result['total_amount']  # Use total (amount + network fee)
        total_detected_usdt += detected_usdt
        
        # Store bank type from first photo
        if not detected_bank_type:
            detected_bank_type = usdt_result['bank_type']
        
        logger.info(f"Bulk USDT photo {idx}: {detected_usdt:.4f} USDT (amount: {usdt_result['amount']:.4f} + fee: {usdt_result['network_fee']:.4f}) from {usdt_result['bank_type']}")
    
    logger.info(f"Bulk USDT processing complete: Total {total_detected_usdt:.4f} USDT from {len(photos)} photos, bank type: {detected_bank_type}")
    
    # Check if total USDT amount matches (allow 0.03 tolerance)
    if abs(total_detected_usdt - tx_info['usdt']) > 0.03:
        # await message.reply_text(
        #     f"⚠️ USDT amount mismatch!\n"
        #     f"Expected: {tx_info['usdt']:.4f} USDT\n"
        #     f"Detected: {total_detected_usdt:.4f} USDT (from {len(photos)} photos)"
        # )
        logger.error(f"USDT amount mismatch! Expected: {tx_info['usdt']:.4f} USDT, Detected: {total_detected_usdt:.4f} USDT (from {len(photos)} photos)")
        return
    
    # Amount matches! Process the transaction
    # await message.reply_text(f"✅ Total amount matched!\n{len(photos)} photos: {total_detected_usdt:.4f} USDT\n\nProcessing...")
    
    # Update balances for the specific staff member's bank
    for bank in balances['mmk_banks']:
        if banks_match(bank['bank_name'], detected_bank['bank_name']):
            bank['amount'] += detected_mmk
            break
    
    # Update USDT for the specific staff member's Swift, Wallet, or Binance account
    usdt_updated = False
    
    # Find the staff's USDT bank that matches the bank type
    for bank in balances['usdt_banks']:
        if bank.get('prefix') == user_prefix:
            # Check if bank name contains Swift, Wallet, or Binance based on detected type
            bank_name_lower = bank['bank_name'].lower()
            is_swift = 'swift' in bank_name_lower
            is_wallet = 'wallet' in bank_name_lower
            is_binance = 'binance' in bank_name_lower
            
            # Match bank type
            type_matches = (
                (detected_bank_type == 'swift' and is_swift) or
                (detected_bank_type == 'wallet' and is_wallet) or
                (detected_bank_type == 'binance' and is_binance)
            )
            
            if type_matches:
                # Check if sufficient USDT balance
                if bank['amount'] < total_detected_usdt:
                    # await message.reply_text(
                    #     f"❌ Insufficient USDT balance!\n\n"
                    #     f"{bank['bank_name']}: {bank['amount']:.4f} USDT\n"
                    #     f"Required: {total_detected_usdt:.4f} USDT\n"
                    #     f"Shortage: {total_detected_usdt - bank['amount']:.4f} USDT"
                    # )
                    logger.error(f"Insufficient USDT balance! {bank['bank_name']}: {bank['amount']:.4f} USDT, Required: {total_detected_usdt:.4f} USDT, Shortage: {total_detected_usdt - bank['amount']:.4f} USDT")
                    return
                bank['amount'] -= total_detected_usdt
                usdt_updated = True
                logger.info(f"Reduced {total_detected_usdt:.4f} USDT from {bank['bank_name']} ({detected_bank_type})")
                break
    
    if not usdt_updated:
        logger.warning(f"No USDT {detected_bank_type} bank found for prefix '{user_prefix}'")
    
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
    #     f"✅ Sell processed!\n\n"
    #     f"MMK: +{detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
    #     f"USDT: -{total_detected_usdt:.4f}"
    # )

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
    
    # Verify MMK amount matches
    if abs(detected_mmk - tx_info['mmk']) > 100:
        await message.reply_text(
            f"⚠️ MMK amount mismatch!\n"
            f"Expected: {tx_info['mmk']:,.0f} MMK\n"
            f"Detected: {detected_mmk:,.0f} MMK"
        )
        return
    
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
    
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    if not original_text:
        logger.info(f"   ⏭️ Skipping: Original message has no text")
        return
    
    logger.info(f"   Original message: '{original_text[:80]}...'")
    
    # Check if this is part of a media group (bulk photos sent together)
    if message.media_group_id:
        logger.info(f"   📸 Media group detected: {message.media_group_id}")
        
        # Initialize media group storage if not exists
        if message.media_group_id not in media_groups:
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
            import asyncio
            asyncio.create_task(process_media_group_delayed(update, context, message.media_group_id))
        
        return
    
    # Single photo (not part of media group)
    tx_info = extract_transaction_info(original_text)
    
    if not tx_info['type'] or not tx_info.get('usdt') or not tx_info.get('mmk'):
        logger.info(f"   ⏭️ Skipping: Not a valid Buy/Sell transaction message")
        return
    
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
    await update.message.reply_text(
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
        "/set_user - Set user prefix (reply to user's message)\n\n"
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
        await update.message.reply_text("❌ No balance loaded")
        return
    
    msg = format_balance_message(balances['mmk_banks'], balances['usdt_banks'], balances.get('thb_banks', []))
    await update.message.reply_text(f"📊 <b>Balance:</b>\n\n<pre>{msg}</pre>", parse_mode='HTML')

async def load_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load balance from replied message"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("Reply to a balance message with /load")
        return
    
    balances = parse_balance_message(update.message.reply_to_message.text)
    
    if balances:
        context.chat_data['balances'] = balances
        thb_count = len(balances.get('thb_banks', []))
        thb_info = f"\nTHB Banks: {thb_count}" if thb_count > 0 else ""
        await update.message.reply_text(
            f"✅ Loaded!\n\n"
            f"MMK Banks: {len(balances['mmk_banks'])}\n"
            f"USDT Banks: {len(balances['usdt_banks'])}"
            f"{thb_info}"
        )
    else:
        await update.message.reply_text("❌ Could not parse balance")

async def set_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user prefix mapping: /set_user @username prefix_name"""
    message = update.message
    
    # Check if user has admin rights (you can customize this check)
    # For now, anyone can set mappings
    
    if len(context.args) < 2:
        await message.reply_text(
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
                await message.reply_text(
                    "⚠️ Please reply to a message from the user instead, or provide their user ID.\n"
                    "Usage: /set_user <user_id> <prefix_name>"
                )
                return
            elif entity.type == "text_mention":
                # User object is available
                user_id = entity.user.id
                username = entity.user.username or entity.user.first_name
                set_user_prefix(user_id, prefix_name, username)
                await message.reply_text(
                    f"✅ Set prefix '{prefix_name}' for user {username} (ID: {user_id})"
                )
                return
    
    # Try to parse as user_id directly
    try:
        user_id = int(username_arg)
        set_user_prefix(user_id, prefix_name)
        await message.reply_text(
            f"✅ Set prefix '{prefix_name}' for user ID: {user_id}"
        )
    except ValueError:
        await message.reply_text(
            "❌ Invalid format. Please use:\n"
            "/set_user <user_id> <prefix_name>\n\n"
            "Or reply to a user's message with:\n"
            "/set_user <prefix_name>"
        )

async def set_user_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user prefix by replying to their message: reply with /set_user prefix_name"""
    message = update.message
    
    if not message.reply_to_message:
        await message.reply_text("Please reply to a user's message")
        return
    
    if len(context.args) < 1:
        await message.reply_text("Usage: Reply to user's message with /set_user <prefix_name>")
        return
    
    prefix_name = context.args[0]
    user_id = message.reply_to_message.from_user.id
    username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
    
    set_user_prefix(user_id, prefix_name, username)
    await message.reply_text(
        f"✅ Set prefix '{prefix_name}' for @{username} (ID: {user_id})"
    )

async def set_receiving_usdt_acc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the receiving USDT account for buy transactions"""
    message = update.message
    
    if len(context.args) < 1:
        # Show current setting
        current_account = get_receiving_usdt_account()
        await message.reply_text(
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
    
    await message.reply_text(
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
            await message.reply_text(
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
            await message.reply_text(
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
        await message.reply_text(
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
            await message.reply_text(
                f"🏦 <b>Edit MMK Bank Account:</b>\n\n"
                f"<b>Current Accounts:</b>\n{account_list}\n\n"
                f"<b>Usage:</b>\n"
                f"/edit_mmk_bank &lt;bank_name&gt; | &lt;new_account&gt; | &lt;new_holder&gt;\n\n"
                f"<b>Example:</b>\n"
                f"/edit_mmk_bank San(KBZ) | 99999999999999999 | NEW NAME",
                parse_mode='HTML'
            )
        else:
            await message.reply_text(
                f"🏦 <b>No MMK Bank Accounts to Edit</b>\n\n"
                f"Use /set_mmk_bank to add accounts first.",
                parse_mode='HTML'
            )
        return
    
    # Parse command
    full_text = ' '.join(context.args)
    parts = [p.strip() for p in full_text.split('|')]
    
    if len(parts) != 3:
        await message.reply_text(
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
            await message.reply_text(
                f"🏦 <b>Remove MMK Bank Account:</b>\n\n"
                f"<b>Current Accounts:</b>\n{account_list}\n\n"
                f"<b>Usage:</b>\n"
                f"/remove_mmk_bank &lt;bank_name&gt;\n\n"
                f"<b>Example:</b>\n"
                f"/remove_mmk_bank San(KBZ)",
                parse_mode='HTML'
            )
        else:
            await message.reply_text(
                f"🏦 <b>No MMK Bank Accounts to Remove</b>",
                parse_mode='HTML'
            )
        return
    
    bank_name = ' '.join(context.args)
    
    # Check if bank exists
    existing = get_mmk_bank_account(bank_name)
    if not existing:
        await message.reply_text(
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
        await update.message.reply_text(
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
    
    await update.message.reply_text(message, parse_mode='HTML')

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
    
    await update.message.reply_text(message, parse_mode='HTML')
    logger.info(f"Test command - Chat: {chat_id}, Thread: {thread_id}")

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
