#!/usr/bin/env python3
"""
Test script to verify balance message parsing
"""

import re

def parse_balance_message(message_text):
    """Parse new balance format with staff prefixes including THB"""
    try:
        text = message_text.strip()
        
        # Remove "MMK" prefix if present at the start
        if text.startswith('MMK'):
            text = text[3:]
        
        # Find currency sections
        usdt_start = text.find('USDT')
        thb_start = text.find('THB')
        
        if usdt_start == -1:
            print("❌ Missing USDT marker")
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
                print(f"⚠️  Could not parse amount for {prefix}({bank_name}): {amount_str}")
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
                print(f"⚠️  Could not parse USDT amount for {prefix}({bank_name}): {amount_str}")
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
                    print(f"⚠️  Could not parse THB amount for {prefix}({bank_name}): {amount_str}")
                    continue
        
        print(f"✅ Parsed {len(banks)} MMK banks, {len(usdt_banks)} USDT banks, {len(thb_banks)} THB banks")
        return {'mmk_banks': banks, 'usdt_banks': usdt_banks, 'thb_banks': thb_banks}
    
    except Exception as e:
        print(f"❌ Parse error: {e}")
        import traceback
        traceback.print_exc()
        return None

def format_balance_message(mmk_banks, usdt_banks, thb_banks=None):
    """Format balance with staff prefixes (hyphen as separator)"""
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

def test_parsing():
    """Test balance parsing with sample data"""
    
    # Sample balance message - single line format (as received from Telegram)
    sample_balance = """MMKSan(Kpay P) -2639565San(CB M) -0San(CB)-10000San(KBZ)-11044185San(AYA M )-0San(AYA) -0San(AYA Wallet) -0San(Wave) -0San(Wave M )-1220723San(Wave Channel) - 1970347San(Yoma)-0NDT (Wave) -2864900MMM (Kpay p)-8839154USDTSan(Swift) -81.99MMN(Binance)-(15.86)NDT(Binance)-6.96(52.96)TZT (Binance)-(222.6)PPK (Binance) - 0ACT(Wallet)-1104.9051OKM(Swift) -5000THBACT(Bkk B) -13223ACT(SCB) -25000"""

    print("🧪 Testing Balance Parsing")
    print("=" * 60)
    print("\n📝 Input:")
    print(sample_balance)
    print("\n" + "=" * 60)
    
    # Parse
    result = parse_balance_message(sample_balance)
    
    if not result:
        print("\n❌ Parsing failed!")
        return
    
    print("\n✅ Parsing successful!")
    print("\n📊 MMK Banks:")
    for bank in result['mmk_banks']:
        print(f"  {bank['bank_name']:30} → {bank['amount']:>15,.0f} (prefix: {bank['prefix']})")
    
    print("\n💵 USDT Banks:")
    for bank in result['usdt_banks']:
        print(f"  {bank['bank_name']:30} → {bank['amount']:>15,.2f} (prefix: {bank['prefix']})")
    
    print("\n💴 THB Banks:")
    for bank in result['thb_banks']:
        print(f"  {bank['bank_name']:30} → {bank['amount']:>15,.2f} (prefix: {bank['prefix']})")
    
    # Test formatting
    print("\n" + "=" * 60)
    print("📤 Formatted Output:")
    print("=" * 60)
    formatted = format_balance_message(result['mmk_banks'], result['usdt_banks'], result['thb_banks'])
    print(formatted)
    
    # Test filtering by prefix
    print("\n" + "=" * 60)
    print("🔍 Filter by Prefix 'San':")
    print("=" * 60)
    san_banks = [b for b in result['mmk_banks'] if b['prefix'] == 'San']
    for bank in san_banks:
        print(f"  {bank['bank_name']:30} → {bank['amount']:>15,.0f}")

if __name__ == '__main__':
    test_parsing()
