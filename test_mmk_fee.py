#!/usr/bin/env python3
"""
Test MMK fee detection in staff replies
"""

import re

def test_mmk_fee_detection():
    """Test the MMK fee regex pattern"""
    
    # Pattern from bot.py
    fee_pattern = r'fee\s*-\s*([\d,]+(?:\.\d+)?)'
    
    # Test cases
    test_cases = [
        {
            'text': 'fee-3039',
            'expected_fee': 3039.0
        },
        {
            'text': 'fee - 3039',
            'expected_fee': 3039.0
        },
        {
            'text': 'Fee-5000',
            'expected_fee': 5000.0
        },
        {
            'text': 'FEE - 1,234',
            'expected_fee': 1234.0
        },
        {
            'text': 'fee-100.50',
            'expected_fee': 100.5
        },
        {
            'text': 'Some text fee-3039 more text',
            'expected_fee': 3039.0
        },
        {
            'text': 'No fee here',
            'expected_fee': None
        }
    ]
    
    print("Testing MMK Fee Detection\n")
    print("=" * 80)
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        text = test['text']
        expected_fee = test['expected_fee']
        
        print(f"\nTest {i}: '{text}'")
        
        match = re.search(fee_pattern, text, re.IGNORECASE)
        
        if match:
            detected_fee = float(match.group(1).replace(',', ''))
            
            if expected_fee is not None and detected_fee == expected_fee:
                print(f"  ✅ PASSED - Detected fee: {detected_fee:,.2f}")
            else:
                print(f"  ❌ FAILED - Expected: {expected_fee}, Got: {detected_fee}")
                all_passed = False
        else:
            if expected_fee is None:
                print(f"  ✅ PASSED - No fee detected (as expected)")
            else:
                print(f"  ❌ FAILED - Expected fee: {expected_fee}, but no match found")
                all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    
    return all_passed

def test_mmk_calculation():
    """Test MMK amount calculation with fee"""
    
    print("\n\nTesting MMK Amount Calculation\n")
    print("=" * 80)
    
    test_cases = [
        {
            'receipt_amount': 15197246,
            'fee': 3039,
            'expected_total': 15200285
        },
        {
            'receipt_amount': 1000000,
            'fee': 5000,
            'expected_total': 1005000
        },
        {
            'receipt_amount': 500000,
            'fee': 0,
            'expected_total': 500000
        }
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        receipt = test['receipt_amount']
        fee = test['fee']
        expected = test['expected_total']
        
        total = receipt + fee
        
        print(f"\nTest {i}:")
        print(f"  Receipt: {receipt:,} MMK")
        print(f"  Fee: {fee:,} MMK")
        print(f"  Total: {total:,} MMK")
        
        if total == expected:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED - Expected: {expected:,}, Got: {total:,}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All calculation tests passed!")
    else:
        print("❌ Some calculation tests failed")
    
    return all_passed

if __name__ == '__main__':
    result1 = test_mmk_fee_detection()
    result2 = test_mmk_calculation()
    
    if result1 and result2:
        print("\n\n🎉 All tests passed successfully!")
    else:
        print("\n\n❌ Some tests failed")
