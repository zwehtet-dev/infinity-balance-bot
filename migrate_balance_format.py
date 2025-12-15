#!/usr/bin/env python3
"""
Migration script to convert old balance format to new format with staff prefixes
"""

def convert_old_to_new(old_balance, default_prefix="San"):
    """
    Convert old balance format to new format with staff prefix
    
    Old format:
    MMK
    Kpay P -13,205,369
    KBZ -11,044,185
    USDT
    Wallet -5607.1401
    
    New format:
    San(Kpay P) -13205369
    San(KBZ) -11044185
    USDT
    San(Wallet) -5607.14
    """
    
    lines = old_balance.strip().split('\n')
    new_lines = []
    in_usdt_section = False
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        if line == 'MMK':
            # Skip MMK header in new format
            continue
        elif line == 'USDT':
            new_lines.append('\nUSDT')
            in_usdt_section = True
            continue
        
        # Parse bank line: "BankName -amount"
        parts = line.split('-')
        if len(parts) == 2:
            bank_name = parts[0].strip()
            amount_str = parts[1].strip().replace(',', '')
            
            try:
                amount = float(amount_str)
                
                # Format based on section
                if in_usdt_section:
                    # USDT: 2 decimal places
                    formatted_amount = f"{amount:.2f}"
                else:
                    # MMK: integer, with commas
                    formatted_amount = f"{int(amount):,}"
                
                # Create new format line
                new_line = f"{default_prefix}({bank_name}) -{formatted_amount}"
                new_lines.append(new_line)
            except ValueError:
                print(f"⚠️  Could not parse amount: {line}")
                continue
    
    return '\n'.join(new_lines)

def interactive_convert():
    """Interactive conversion tool"""
    print("🔄 Balance Format Migration Tool")
    print("=" * 60)
    print("\nThis tool converts old balance format to new format with staff prefixes.")
    print("\nPaste your old balance message (press Enter twice when done):")
    print("-" * 60)
    
    lines = []
    empty_count = 0
    
    while True:
        try:
            line = input()
            if not line:
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break
    
    if not lines:
        print("\n❌ No input provided")
        return
    
    old_balance = '\n'.join(lines)
    
    print("\n" + "=" * 60)
    print("📝 Original Balance:")
    print("=" * 60)
    print(old_balance)
    
    # Get default prefix
    print("\n" + "=" * 60)
    default_prefix = input("Enter default staff prefix (default: San): ").strip() or "San"
    
    # Convert
    new_balance = convert_old_to_new(old_balance, default_prefix)
    
    print("\n" + "=" * 60)
    print("✨ Converted Balance:")
    print("=" * 60)
    print(new_balance)
    print("=" * 60)
    
    # Save option
    save = input("\nSave to file? (y/n): ").strip().lower()
    if save == 'y':
        filename = input("Enter filename (default: new_balance.txt): ").strip() or "new_balance.txt"
        with open(filename, 'w') as f:
            f.write(new_balance)
        print(f"✅ Saved to {filename}")

def example_conversion():
    """Show example conversion"""
    print("📚 Example Conversion")
    print("=" * 60)
    
    old_balance = """MMK
Kpay P -13,205,369
KBZ -11,044,185
Wave -6,351,481
AYA -0
CB -10,000
Yoma -0
USDT
Wallet -5607.1401"""
    
    print("\n📝 Old Format:")
    print("-" * 60)
    print(old_balance)
    
    new_balance = convert_old_to_new(old_balance, "San")
    
    print("\n✨ New Format (with prefix 'San'):")
    print("-" * 60)
    print(new_balance)
    print("=" * 60)

def main():
    """Main function"""
    print("\n🤖 Infinity Balance Bot - Format Migration")
    print("=" * 60)
    print("\nOptions:")
    print("1. Interactive conversion")
    print("2. Show example")
    print("3. Exit")
    print()
    
    choice = input("Select option (1-3): ").strip()
    
    if choice == '1':
        interactive_convert()
    elif choice == '2':
        example_conversion()
    elif choice == '3':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid option")

if __name__ == '__main__':
    main()
