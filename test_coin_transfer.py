#!/usr/bin/env python3
"""
Test coin transfer pattern matching
"""

import re

def test_coin_transfer_pattern():
    """Test the coin transfer regex pattern"""
    
    # Pattern from bot.py
    coin_transfer_pattern = r'([A-Za-z\s]+)\s*\(([^)]+)\)\s+to\s+([A-Za-z\s]+)\s*\(([^)]+)\)\s+([\d.]+)\s*USDT\s*-\s*([\d.]+)\s*USDT\s*\(fee\)\s*=\s*([\d.]+)\s*USDT'
    
    # Test cases
    test_cases = [
        {
            'text': 'San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT',
            'expected': {
                'from_prefix': 'San',
                'from_bank': 'binance',
                'to_prefix': 'OKM',
                'to_bank': 'Wallet',
                'sent': 10.0,
                'fee': 0.47,
                'received': 9.53
            }
        },
        {
            'text': 'MMN (Wallet) to MMN (binance) 50 USDT-1.2 USDT(fee) = 48.8 USDT',
            'expected': {
                'from_prefix': 'MMN',
                'from_bank': 'Wallet',
                'to_prefix': 'MMN',
                'to_bank': 'binance',
                'sent': 50.0,
                'fee': 1.2,
                'received': 48.8
            }
        },
        {
            'text': 'TZT (Swift) to TZT (Wallet) 100 USDT-0.15 USDT(fee) = 99.85 USDT',
            'expected': {
                'from_prefix': 'TZT',
                'from_bank': 'Swift',
                'to_prefix': 'TZT',
                'to_bank': 'Wallet',
                'sent': 100.0,
                'fee': 0.15,
                'received': 99.85
            }
        },
        {
            'text': 'San(binance) to OKM (Wallet) 10 USDT - 0.47 USDT(fee) = 9.53 USDT',
            'expected': {
                'from_prefix': 'San',
                'from_bank': 'binance',
                'to_prefix': 'OKM',
                'to_bank': 'Wallet',
                'sent': 10.0,
                'fee': 0.47,
                'received': 9.53
            }
        }
    ]
    
    print("Testing Coin Transfer Pattern Matching\n")
    print("=" * 80)
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        text = test['text']
        expected = test['expected']
        
        print(f"\nTest {i}: {text}")
        
        match = re.search(coin_transfer_pattern, text, re.IGNORECASE)
        
        if match:
            from_prefix = match.group(1).strip()
            from_bank = match.group(2).strip()
            to_prefix = match.group(3).strip()
            to_bank = match.group(4).strip()
            sent_amount = float(match.group(5))
            fee_amount = float(match.group(6))
            received_amount = float(match.group(7))
            
            # Check if matches expected
            passed = (
                from_prefix == expected['from_prefix'] and
                from_bank == expected['from_bank'] and
                to_prefix == expected['to_prefix'] and
                to_bank == expected['to_bank'] and
                sent_amount == expected['sent'] and
                fee_amount == expected['fee'] and
                received_amount == expected['received']
            )
            
            if passed:
                print(f"  ✅ PASSED")
                print(f"     From: {from_prefix}({from_bank})")
                print(f"     To: {to_prefix}({to_bank})")
                print(f"     Sent: {sent_amount} USDT")
                print(f"     Fee: {fee_amount} USDT")
                print(f"     Received: {received_amount} USDT")
            else:
                print(f"  ❌ FAILED - Values don't match expected")
                print(f"     Expected: {expected}")
                print(f"     Got: from={from_prefix}({from_bank}), to={to_prefix}({to_bank}), sent={sent_amount}, fee={fee_amount}, received={received_amount}")
                all_passed = False
        else:
            print(f"  ❌ FAILED - Pattern did not match")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    
    return all_passed

if __name__ == '__main__':
    test_coin_transfer_pattern()
