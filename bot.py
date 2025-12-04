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

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Missing required environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

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
    """Parse balance message: MMKKpay P -13,205,369KBZ -11044185...USDTWallet -5607.1401"""
    try:
        text = message_text.strip()
        
        mmk_start = text.find('MMK')
        usdt_start = text.find('USDT')
        
        if mmk_start == -1 or usdt_start == -1:
            logger.error("Missing MMK or USDT markers")
            return None
        
        mmk_section = text[mmk_start + 3:usdt_start]
        usdt_section = text[usdt_start + 4:]
        
        # Parse MMK banks
        mmk_banks = []
        mmk_pattern = r'([A-Za-z\s]+?)\s*-\s*([\d,]+(?:\.\d+)?)'
        
        for match in re.finditer(mmk_pattern, mmk_section):
            bank_name = match.group(1).strip()
            amount = float(match.group(2).replace(',', ''))
            mmk_banks.append({'bank_name': bank_name, 'amount': amount})
        
        # Parse USDT
        usdt_amount = 0.0
        usdt_match = re.search(r'Wallet\s*-\s*([\d,]+(?:\.\d+)?)', usdt_section)
        if usdt_match:
            usdt_amount = float(usdt_match.group(1).replace(',', ''))
        
        logger.info(f"Parsed {len(mmk_banks)} banks, USDT: {usdt_amount}")
        return {'mmk_banks': mmk_banks, 'usdt_amount': usdt_amount}
    
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None

def format_balance_message(mmk_banks, usdt_amount):
    """Format balance: 
MMK
Kpay P -13,205,369
KBZ -11,044,185
...
USDT
Wallet -5607.1401"""
    message = "MMK\n"
    for bank in mmk_banks:
        formatted = f"{int(bank['amount']):,}"
        message += f"{bank['bank_name']} -{formatted} \n"
    message += f"\nUSDT\nWallet -{usdt_amount:.4f}"
    return message

# ============================================================================
# OCR FUNCTIONS
# ============================================================================

async def ocr_detect_mmk_bank_and_amount(image_base64, mmk_banks):
    """Detect MMK bank and amount from receipt"""
    try:
        bank_list = ", ".join([f"{i+1}. {b['bank_name']}" for i, b in enumerate(mmk_banks)])
        
        prompt = f"""Analyze this MMK payment receipt.

Available banks:
{bank_list}

Extract:
1. Transaction amount (integer, no decimals)
2. Bank number (1-{len(mmk_banks)})

Bank Recognition:
- CB: Blue "Account History" OR rainbow "CB BANK" logo
- KBZ: "INTERNAL TRANSFER - CONFIRM" with green banner
- Kpay P: RED/CORAL color with "Payment Successful"
- Kpay: BLUE with Myanmar text and "KBZ Pay"
- Wave: YELLOW header OR green "Successful" with "Cash In"
- AYA: "Payment Complete" OR "AYA PAY" logo
- Yoma: "Flexi Everyday Account"

Return JSON:
{{"amount": <integer>, "bank_number": <1-{len(mmk_banks)}>}}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
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
        amount = float(data['amount'])
        bank_idx = int(data['bank_number']) - 1
        
        if 0 <= bank_idx < len(mmk_banks):
            return {'amount': amount, 'bank': mmk_banks[bank_idx]}
        
        return None
    
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return None

async def ocr_extract_usdt_amount(image_base64):
    """Extract USDT amount from receipt"""
    try:
        prompt = """Extract USDT amount from this receipt.
Return JSON: {"amount": <number>}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
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
        return float(data['amount'])
    
    except Exception as e:
        logger.error(f"USDT OCR error: {e}")
        return None

# ============================================================================
# TRANSACTION PROCESSING
# ============================================================================

def extract_transaction_info(text):
    """Extract Buy/Sell, USDT amount, MMK amount from message"""
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
        await message.reply_text("❌ Balance not loaded. Post balance message in auto balance topic first.")
        return
    
    if not message.photo:
        await message.reply_text("❌ No receipt photo")
        return
    
    original_message_id = message.reply_to_message.message_id
    
    # Get photo
    photo = message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
    
    # OCR
    result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'])
    
    if not result:
        await message.reply_text("❌ Could not detect bank/amount")
        return
    
    detected_mmk = result['amount']
    detected_bank = result['bank']
    
    # Initialize or update pending transaction
    if original_message_id not in pending_transactions:
        pending_transactions[original_message_id] = {
            'amounts': [],
            'bank': detected_bank,
            'expected_mmk': tx_info['mmk'],
            'expected_usdt': tx_info['usdt'],
            'type': 'buy'
        }
    
    # Add this amount to the list
    pending_transactions[original_message_id]['amounts'].append(detected_mmk)
    total_detected_mmk = sum(pending_transactions[original_message_id]['amounts'])
    photo_count = len(pending_transactions[original_message_id]['amounts'])
    
    logger.info(f"Buy transaction {original_message_id}: Added {detected_mmk:,.0f}, Total: {total_detected_mmk:,.0f} from {photo_count} photo(s)")
    
    # Check if total amount matches (allow 100 MMK difference)
    if abs(total_detected_mmk - tx_info['mmk']) > 100:
        await message.reply_text(
            f"📝 Received {photo_count} photo(s)\n"
            f"Total: {total_detected_mmk:,.0f} MMK\n"
            f"Expected: {tx_info['mmk']:,.0f} MMK\n\n"
            f"⏳ Send more photos if needed"
        )
        return
    
    # Amount matches! Process the transaction
    await message.reply_text(f"✅ Total amount matched!\n{photo_count} photo(s): {total_detected_mmk:,.0f} MMK\n\nProcessing...")
    
    # Update balances
    for bank in balances['mmk_banks']:
        if bank['bank_name'] == detected_bank['bank_name']:
            bank['amount'] -= total_detected_mmk
            break
    
    balances['usdt_amount'] += tx_info['usdt']
    
    # Send new balance
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_amount'])
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        message_thread_id=AUTO_BALANCE_TOPIC_ID,
        text=new_balance
    )
    
    context.chat_data['balances'] = balances
    
    await message.reply_text(
        f"✅ Buy processed!\n\n"
        f"MMK: -{total_detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
        f"USDT: +{tx_info['usdt']:.4f}"
    )
    
    # Clean up pending transaction
    if original_message_id in pending_transactions:
        del pending_transactions[original_message_id]

async def process_sell_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict):
    """SELL: User sells USDT, we receive MMK (supports multiple receipts)"""
    message = update.message
    balances = context.chat_data.get('balances')
    
    if not balances:
        await message.reply_text("❌ Balance not loaded")
        return
    
    # Get user's MMK receipt
    original_message = message.reply_to_message
    if not original_message or not original_message.photo:
        await message.reply_text("❌ Original message has no receipt")
        return
    
    # OCR user's receipt (only once, not accumulated)
    user_photo = original_message.photo[-1]
    user_file = await context.bot.get_file(user_photo.file_id)
    user_bytes = await user_file.download_as_bytearray()
    user_base64 = base64.b64encode(user_bytes).decode('utf-8')
    
    user_result = await ocr_detect_mmk_bank_and_amount(user_base64, balances['mmk_banks'])
    
    if not user_result:
        await message.reply_text("❌ Could not detect bank/amount from user receipt")
        return
    
    detected_mmk = user_result['amount']
    detected_bank = user_result['bank']
    
    # Verify MMK
    if abs(detected_mmk - tx_info['mmk']) > 100:
        await message.reply_text(
            f"⚠️ MMK mismatch!\n"
            f"Expected: {tx_info['mmk']:,.0f}\n"
            f"Detected: {detected_mmk:,.0f}"
        )
        return
    
    # Get staff's USDT receipt(s) - support multiple photos
    if not message.photo:
        await message.reply_text("❌ No USDT receipt")
        return
    
    original_message_id = message.reply_to_message.message_id
    
    staff_photo = message.photo[-1]
    staff_file = await context.bot.get_file(staff_photo.file_id)
    staff_bytes = await staff_file.download_as_bytearray()
    staff_base64 = base64.b64encode(staff_bytes).decode('utf-8')
    
    detected_usdt = await ocr_extract_usdt_amount(staff_base64)
    
    if not detected_usdt:
        await message.reply_text("❌ Could not detect USDT amount")
        return
    
    # Initialize or update pending transaction for sell
    if original_message_id not in pending_transactions:
        pending_transactions[original_message_id] = {
            'amounts': [],
            'mmk_bank': detected_bank,
            'detected_mmk': detected_mmk,
            'expected_usdt': tx_info['usdt'],
            'type': 'sell'
        }
    
    # Add this USDT amount to the list
    pending_transactions[original_message_id]['amounts'].append(detected_usdt)
    total_detected_usdt = sum(pending_transactions[original_message_id]['amounts'])
    photo_count = len(pending_transactions[original_message_id]['amounts'])
    
    logger.info(f"Sell transaction {original_message_id}: Added {detected_usdt:.4f} USDT, Total: {total_detected_usdt:.4f} from {photo_count} photo(s)")
    
    # Check if USDT amount matches (allow small difference for crypto)
    if abs(total_detected_usdt - tx_info['usdt']) > 0.01:
        await message.reply_text(
            f"📝 Received {photo_count} photo(s)\n"
            f"Total: {total_detected_usdt:.4f} USDT\n"
            f"Expected: {tx_info['usdt']:.4f} USDT\n\n"
            f"⏳ Send more photos if needed"
        )
        return
    
    # Amount matches! Process the transaction
    await message.reply_text(f"✅ Total amount matched!\n{photo_count} photo(s): {total_detected_usdt:.4f} USDT\n\nProcessing...")
    
    # Update balances
    for bank in balances['mmk_banks']:
        if bank['bank_name'] == detected_bank['bank_name']:
            bank['amount'] += detected_mmk
            break
    
    balances['usdt_amount'] -= total_detected_usdt
    
    # Send new balance
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_amount'])
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        message_thread_id=AUTO_BALANCE_TOPIC_ID,
        text=new_balance
    )
    
    context.chat_data['balances'] = balances
    
    await message.reply_text(
        f"✅ Sell processed!\n\n"
        f"MMK: +{detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
        f"USDT: -{total_detected_usdt:.4f}"
    )
    
    # Clean up pending transaction
    if original_message_id in pending_transactions:
        del pending_transactions[original_message_id]

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
        await message.reply_text("❌ Balance not loaded. Post balance message in auto balance topic first.")
        return
    
    await message.reply_text(f"📸 Processing {len(photos)} photos...")
    
    total_detected_mmk = 0
    detected_bank = None
    
    for idx, photo in enumerate(photos, 1):
        logger.info(f"Processing bulk photo {idx}/{len(photos)}")
        
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        result = await ocr_detect_mmk_bank_and_amount(photo_base64, balances['mmk_banks'])
        
        if not result or not result['amount']:
            logger.warning(f"Could not process bulk photo {idx}")
            continue
        
        detected_mmk = result['amount']
        photo_bank = result['bank']
        
        total_detected_mmk += detected_mmk
        logger.info(f"Bulk photo {idx}: {detected_mmk:,.0f} MMK")
        
        if photo_bank and not detected_bank:
            detected_bank = photo_bank
    
    if not detected_bank:
        await message.reply_text("❌ Could not detect bank from receipts")
        return
    
    logger.info(f"Bulk processing complete: Total {total_detected_mmk:,.0f} MMK from {len(photos)} photos")
    
    # Check if total amount matches
    if abs(total_detected_mmk - tx_info['mmk']) > 100:
        await message.reply_text(
            f"⚠️ Amount mismatch!\n"
            f"Expected: {tx_info['mmk']:,.0f} MMK\n"
            f"Detected: {total_detected_mmk:,.0f} MMK (from {len(photos)} photos)"
        )
        return
    
    # Amount matches! Process the transaction
    await message.reply_text(f"✅ Total amount matched!\n{len(photos)} photos: {total_detected_mmk:,.0f} MMK\n\nProcessing...")
    
    # Update balances
    for bank in balances['mmk_banks']:
        if bank['bank_name'] == detected_bank['bank_name']:
            bank['amount'] -= total_detected_mmk
            break
    
    balances['usdt_amount'] += tx_info['usdt']
    
    # Send new balance
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_amount'])
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        message_thread_id=AUTO_BALANCE_TOPIC_ID,
        text=new_balance
    )
    
    context.chat_data['balances'] = balances
    
    await message.reply_text(
        f"✅ Buy processed!\n\n"
        f"MMK: -{total_detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
        f"USDT: +{tx_info['usdt']:.4f}"
    )

async def process_sell_transaction_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_info: dict, photos: list, message):
    """Process SELL transaction with multiple USDT photos sent as media group"""
    balances = context.chat_data.get('balances')
    
    if not balances:
        await message.reply_text("❌ Balance not loaded")
        return
    
    # Get user's MMK receipt
    original_message = message.reply_to_message
    if not original_message or not original_message.photo:
        await message.reply_text("❌ Original message has no receipt")
        return
    
    # OCR user's receipt
    user_photo = original_message.photo[-1]
    user_file = await context.bot.get_file(user_photo.file_id)
    user_bytes = await user_file.download_as_bytearray()
    user_base64 = base64.b64encode(user_bytes).decode('utf-8')
    
    user_result = await ocr_detect_mmk_bank_and_amount(user_base64, balances['mmk_banks'])
    
    if not user_result:
        await message.reply_text("❌ Could not detect bank/amount from user receipt")
        return
    
    detected_mmk = user_result['amount']
    detected_bank = user_result['bank']
    
    # Verify MMK
    if abs(detected_mmk - tx_info['mmk']) > 100:
        await message.reply_text(
            f"⚠️ MMK mismatch!\n"
            f"Expected: {tx_info['mmk']:,.0f}\n"
            f"Detected: {detected_mmk:,.0f}"
        )
        return
    
    # Process all USDT photos in bulk
    await message.reply_text(f"📸 Processing {len(photos)} USDT photos...")
    
    total_detected_usdt = 0
    
    for idx, photo in enumerate(photos, 1):
        logger.info(f"Processing bulk USDT photo {idx}/{len(photos)}")
        
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        detected_usdt = await ocr_extract_usdt_amount(photo_base64)
        
        if not detected_usdt:
            logger.warning(f"Could not process bulk USDT photo {idx}")
            continue
        
        total_detected_usdt += detected_usdt
        logger.info(f"Bulk USDT photo {idx}: {detected_usdt:.4f} USDT")
    
    logger.info(f"Bulk USDT processing complete: Total {total_detected_usdt:.4f} USDT from {len(photos)} photos")
    
    # Check if total USDT amount matches
    if abs(total_detected_usdt - tx_info['usdt']) > 0.01:
        await message.reply_text(
            f"⚠️ USDT amount mismatch!\n"
            f"Expected: {tx_info['usdt']:.4f} USDT\n"
            f"Detected: {total_detected_usdt:.4f} USDT (from {len(photos)} photos)"
        )
        return
    
    # Amount matches! Process the transaction
    await message.reply_text(f"✅ Total amount matched!\n{len(photos)} photos: {total_detected_usdt:.4f} USDT\n\nProcessing...")
    
    # Update balances
    for bank in balances['mmk_banks']:
        if bank['bank_name'] == detected_bank['bank_name']:
            bank['amount'] += detected_mmk
            break
    
    balances['usdt_amount'] -= total_detected_usdt
    
    # Send new balance
    new_balance = format_balance_message(balances['mmk_banks'], balances['usdt_amount'])
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        message_thread_id=AUTO_BALANCE_TOPIC_ID,
        text=new_balance
    )
    
    context.chat_data['balances'] = balances
    
    await message.reply_text(
        f"✅ Sell processed!\n\n"
        f"MMK: +{detected_mmk:,.0f} ({detected_bank['bank_name']})\n"
        f"USDT: -{total_detected_usdt:.4f}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages"""
    message = update.message
    
    if message.chat.id != TARGET_GROUP_ID:
        return
    
    # Auto-load balance from auto balance topic
    if message.message_thread_id == AUTO_BALANCE_TOPIC_ID:
        if message.text and 'MMK' in message.text and 'USDT' in message.text:
            balances = parse_balance_message(message.text)
            if balances:
                context.chat_data['balances'] = balances
                logger.info(f"✅ Balance loaded: {len(balances['mmk_banks'])} banks")
        return
    
    # Process transactions in USDT transfers topic
    if message.message_thread_id != USDT_TRANSFERS_TOPIC_ID:
        return
    
    if not message.reply_to_message or not message.photo:
        return
    
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    if not original_text:
        return
    
    # Check if this is part of a media group (bulk photos sent together)
    if message.media_group_id:
        logger.info(f"📸 Media group detected: {message.media_group_id}")
        
        # Initialize media group storage if not exists
        if message.media_group_id not in media_groups:
            media_groups[message.media_group_id] = {
                'photos': [],
                'message': message,
                'original_text': original_text
            }
        
        # Add this photo to the group
        media_groups[message.media_group_id]['photos'].append(message.photo[-1])
        photo_count = len(media_groups[message.media_group_id]['photos'])
        logger.info(f"Added photo to media group. Total photos: {photo_count}")
        
        # Only schedule processing once (from the first photo)
        if photo_count == 1:
            logger.info(f"Scheduling media group processing for {message.media_group_id}")
            import asyncio
            asyncio.create_task(process_media_group_delayed(update, context, message.media_group_id))
        
        return
    
    # Single photo (not part of media group)
    tx_info = extract_transaction_info(original_text)
    
    if not tx_info['type'] or not tx_info['usdt'] or not tx_info['mmk']:
        return
    
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
        "📊 Balances stored in Telegram\n\n"
        "<b>Commands:</b>\n"
        "/start - Status\n"
        "/balance - Show current balance\n"
        "/load - Load balance from message\n"
        "/test - Test connection and configuration",
        parse_mode='HTML'
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance"""
    balances = context.chat_data.get('balances')
    
    if not balances:
        await update.message.reply_text("❌ No balance loaded")
        return
    
    msg = format_balance_message(balances['mmk_banks'], balances['usdt_amount'])
    await update.message.reply_text(f"📊 <b>Balance:</b>\n\n<pre>{msg}</pre>", parse_mode='HTML')

async def load_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load balance from replied message"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("Reply to a balance message with /load")
        return
    
    balances = parse_balance_message(update.message.reply_to_message.text)
    
    if balances:
        context.chat_data['balances'] = balances
        await update.message.reply_text(
            f"✅ Loaded!\n\n"
            f"MMK Banks: {len(balances['mmk_banks'])}\n"
            f"USDT: {balances['usdt_amount']:.4f}"
        )
    else:
        await update.message.reply_text("❌ Could not parse balance")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test command to verify group and topic configuration"""
    message = update.message
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.message_thread_id else None
    
    test_result = f"""🧪 <b>Connection Test</b>

<b>Current Message Info:</b>
• Chat ID: <code>{chat_id}</code>
• Thread ID: <code>{thread_id}</code>
• Chat Type: {message.chat.type}

<b>Bot Configuration:</b>
• Target Group: <code>{TARGET_GROUP_ID}</code>
• USDT Transfers Topic: <code>{USDT_TRANSFERS_TOPIC_ID}</code>
• Auto Balance Topic: <code>{AUTO_BALANCE_TOPIC_ID}</code>

<b>Connection Status:</b>"""
    
    # Check if in correct group
    if chat_id == TARGET_GROUP_ID:
        test_result += "\n✅ In correct group"
    else:
        test_result += f"\n❌ Wrong group (expected {TARGET_GROUP_ID})"
    
    # Check if in correct topic
    if thread_id == USDT_TRANSFERS_TOPIC_ID:
        test_result += "\n✅ In USDT Transfers topic"
    elif thread_id == AUTO_BALANCE_TOPIC_ID:
        test_result += "\n✅ In Auto Balance topic"
    elif thread_id:
        test_result += f"\n⚠️ In different topic (ID: {thread_id})"
    else:
        test_result += "\n⚠️ Not in a topic (main chat)"
    
    test_result += "\n\n<b>Tip:</b> Send this command in different topics to verify IDs."
    
    await message.reply_text(test_result, parse_mode='HTML')
    logger.info(f"Test command - Chat: {chat_id}, Thread: {thread_id}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Start bot"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("load", load_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    
    logger.info("🤖 Infinity Balance Bot Started")
    logger.info(f"� Grou p: {TARGET_GROUP_ID}")
    logger.info(f"�  USDT Topic: {USDT_TRANSFERS_TOPIC_ID}")
    logger.info(f"📊 Balance Topic: {AUTO_BALANCE_TOPIC_ID}")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
