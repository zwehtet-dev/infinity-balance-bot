# Swift/Wallet Network Fee Support

## Overview

The bot now automatically detects and includes network fees when processing USDT transactions from Swift or Wallet accounts. This ensures accurate balance tracking when network fees are charged.

## Features

### 1. Automatic Bank Type Detection

The bot can distinguish between three types of USDT accounts:
- **Binance**: Shows "Withdrawal Details" with network fee listed separately (fee already included in amount)
- **Swift**: Shows "USDT Sent" with dark theme and network fee in BNB (need to add fee)
- **Wallet**: Other wallets like Trust Wallet, MetaMask, etc. (need to add fee if shown)

### 2. Network Fee Handling

When processing USDT receipts, the bot handles fees differently based on the platform:

**Binance:**
- Amount shown already includes the network fee
- Bot uses the displayed amount as-is (does NOT add fee again)
- Example: Shows "-47.84175 USDT" with "Network fee: 0.01 USDT" → Bot uses 47.84175 USDT

**Swift/Wallet:**
- Network fee is separate and needs to be added
- Bot calculates total = amount + network fee
- Example: Shows "-24.813896 USDT" with "Network fee: 0.12 USD" → Bot uses 24.933896 USDT (24.813896 + 0.12)

### 3. Staff-Specific Account Matching

For sell transactions, the bot:
1. Detects if the receipt is from Swift or Wallet
2. Matches to the staff member's corresponding account
3. Reduces USDT from the correct account (Swift or Wallet)

**Example Balance:**
```
USDT
San(Swift) -81.99
San(Wallet) -1104.9051
San(Binance) -50.00
MMN(Binance) -(15.86)
```

If San sends a Swift receipt → reduces from `San(Swift)`
If San sends a Wallet receipt → reduces from `San(Wallet)`
If San sends a Binance receipt → reduces from `San(Binance)`

## Use Cases

### Sell Transaction (Single Photo)

**Scenario:** Customer sells 100 USDT, staff sends MMK and provides USDT receipt

**Process:**
1. Customer posts: "Sell 100 USDT = 2,500,000 MMK" with their MMK receipt
2. Staff (San) replies with Swift receipt showing:
   - Amount: 99.88 USDT
   - Network fee: 0.12 USD
3. Bot detects:
   - Total: 100.00 USDT (99.88 + 0.12)
   - Bank type: Swift
4. Bot reduces 100.00 USDT from `San(Swift)`
5. Bot adds 2,500,000 MMK to `San(KBZ)` (or detected bank)

### Sell Transaction (Multiple Photos)

**Scenario:** Large transaction requiring multiple USDT transfers

**Process:**
1. Customer posts: "Sell 500 USDT = 12,500,000 MMK"
2. Staff sends 3 Swift receipts:
   - Photo 1: 200 USDT (199.88 + 0.12 fee)
   - Photo 2: 200 USDT (199.88 + 0.12 fee)
   - Photo 3: 100 USDT (99.88 + 0.12 fee)
3. Bot calculates total: 500.00 USDT
4. Bot reduces 500.00 USDT from staff's Swift account

### Internal Transfer (Swift/Wallet to Binance)

**Scenario:** Staff transfers USDT from Swift to Binance

**Format:**
```
San(Swift) to San(Binance)
[attach Swift receipt]
```

**Process:**
1. Staff posts transfer message with Swift receipt showing:
   - Amount: 99.88 USDT
   - Network fee: 0.12 USD
2. Bot detects:
   - Total: 100.00 USDT (includes network fee)
   - Transfer type: Swift to Binance
3. Bot reduces 100.00 USDT from `San(Swift)`
4. Bot adds 99.88 USDT to `San(Binance)` (amount received)

**Note:** For Swift/Wallet to Binance transfers, the network fee is deducted from the source account, but only the actual amount received is added to the destination.

### Internal Transfer (Binance to Swift/Wallet)

**Scenario:** Staff transfers USDT from Binance to Swift

**Format:**
```
San(Binance) to San(Swift)
[attach receipt]
```

**Process:**
1. Bot detects amount from receipt (no network fee for Binance withdrawals in this direction)
2. Reduces from `San(Binance)`
3. Adds to `San(Swift)`

## OCR Detection

### Binance Receipt Indicators
- Title: "Withdrawal Details"
- Shows amount like "-47.84175 USDT"
- Network fee listed separately at bottom: "Network fee: 0.01 USDT"
- Status: "Awaiting Approval" or "Completed"
- Network type shown (BSC, ETH, etc.)
- **Important**: The displayed amount already includes the network fee

### Swift Receipt Indicators
- Title: "USDT Sent"
- Dark theme interface
- Network fee shown in BNB with USD equivalent: "0.000138566835 BNB (0.12 $)"
- Recipient address shown
- Status: "Completed"

### Wallet Receipt Indicators
- Various wallet interfaces (Trust Wallet, MetaMask, etc.)
- May or may not show network fees
- Different UI layouts

### OCR Response Format

**Binance Example:**
```json
{
    "amount": 47.84175,
    "network_fee": 0.01,
    "total_amount": 47.84175,
    "bank_type": "binance"
}
```

**Swift Example:**
```json
{
    "amount": 24.813896,
    "network_fee": 0.12,
    "total_amount": 24.933896,
    "bank_type": "swift"
}
```

**Fields:**
- `amount`: Main transaction amount (positive number)
- `network_fee`: Network fee if shown (0 if not shown)
- `total_amount`: Final amount to use (Binance: same as amount, Swift/Wallet: amount + fee)
- `bank_type`: "binance", "swift", or "wallet" (lowercase)

## Balance Format

Staff can have multiple USDT accounts:

```
USDT
San(Swift) -81.99          # Swift wallet
San(Wallet) -1104.9051     # Other wallet
MMN(Binance) -(15.86)      # Binance account
NDT(Binance) -6.96         # Another Binance account
```

## Configuration

No additional configuration needed. The feature works automatically when:
1. Staff has both Swift and Wallet accounts in the balance
2. Receipts are from Swift or Wallet transactions
3. Network fees are shown on the receipt

## Important Notes

1. **Binance Fee Handling**: Binance displays the withdrawal amount with the network fee already included. The bot uses this amount as-is and does NOT add the network fee again.

2. **Swift/Wallet Fee Handling**: For Swift and Wallet receipts, the network fee is separate and must be added to get the total amount deducted from the account.

3. **Network Fee Detection**: The bot automatically detects network fees from receipts. If no fee is shown, it uses 0.

4. **Bank Type Matching**: The bot matches receipts to accounts by checking if the account name contains "Binance", "Swift", or "Wallet" (case-insensitive).

5. **Total Amount**: The bot uses the correct total based on platform:
   - Binance: Uses displayed amount (already includes fee)
   - Swift/Wallet: Adds network fee to transaction amount

6. **Internal Transfers**: For Swift/Wallet to Binance transfers, the network fee is included in the amount deducted from the source account.

7. **USDT Tolerance**: The bot allows 0.03 USDT tolerance for amount matching to account for small discrepancies.

## Examples

### Example 1: Binance Withdrawal Receipt

**Receipt shows:**
```
-47.84175 USDT
Network fee: 0.01 USDT
```

**Bot processes:**
```
Amount: 47.84175 USDT
Network fee: 0.01 USDT
Total: 47.84175 USDT (fee already included in amount)
Bank type: binance
```

**Balance update:**
```
San(Binance): 100.00 → 52.15825 USDT
(100.00 - 47.84175 = 52.15825)
```

**Note:** The 47.84175 USDT shown includes the 0.01 USDT network fee. Binance deducts 47.85175 total (47.84175 + 0.01) but shows 47.84175 as the withdrawal amount.

### Example 2: Swift Receipt with Network Fee

**Receipt shows:**
```
-24.813896 USDT
Network fee: 0.000138566835 BNB (0.12 $)
```

**Bot processes:**
```
Amount: 24.813896 USDT
Network fee: 0.12 USDT
Total: 24.933896 USDT (need to add fee)
Bank type: swift
```

**Balance update:**
```
San(Swift): 81.99 → 57.056104 USDT
(81.99 - 24.933896 = 57.056104)
```

### Example 3: Wallet Receipt without Network Fee

**Receipt shows:**
```
Sent: 50.5 USDT
```

**Bot processes:**
```
Amount: 50.5 USDT
Network fee: 0 USDT
Total: 50.5 USDT
Bank type: wallet
```

**Balance update:**
```
San(Wallet): 1104.9051 → 1054.4051 USDT
(1104.9051 - 50.5 = 1054.4051)
```

### Example 4: Internal Transfer with Network Fee

**Message:**
```
San(Swift) to San(Binance)
[Swift receipt: 99.88 USDT + 0.12 fee]
```

**Bot processes:**
```
Total deducted from Swift: 100.00 USDT (99.88 + 0.12)
Amount added to Binance: 99.88 USDT
```

**Balance update:**
```
San(Swift): 81.99 → -18.01 USDT (insufficient balance error)
```

## Troubleshooting

### Issue: Wrong account updated

**Cause:** Account name doesn't contain "Binance", "Swift", or "Wallet"

**Solution:** Ensure account names in balance message include the platform name:
- ✅ `San(Binance)`
- ✅ `San(Swift)`
- ✅ `San(Wallet)`
- ❌ `San(USDT)` (won't match any receipt type)

### Issue: Network fee not detected

**Cause:** Receipt doesn't show network fee clearly

**Solution:** 
- Ensure receipt shows network fee in USD
- Bot will use 0 if fee is not detected
- Check OCR logs for detection details

### Issue: Amount mismatch

**Cause:** Expected amount doesn't include network fee

**Solution:** When posting transaction, include network fee in expected amount:
- If sending 99.88 USDT with 0.12 fee
- Post as: "Sell 100 USDT" (not "Sell 99.88 USDT")

## Technical Details

### Functions Updated

1. **`ocr_extract_usdt_with_fee()`**: New function that detects amount, network fee, and bank type
2. **`ocr_extract_usdt_amount()`**: Updated to use new function (backward compatible)
3. **`process_sell_transaction()`**: Updated to use bank type matching
4. **`process_sell_transaction_bulk()`**: Updated to use bank type matching
5. **`process_internal_transfer()`**: Updated to include network fees for Swift/Wallet transfers

### Database Changes

No database changes required. The feature uses existing balance structure.

### Logging

The bot logs detailed information about USDT detection:
```
USDT OCR: {'amount': 24.813896, 'network_fee': 0.12, 'total_amount': 24.933896, 'bank_type': 'swift'}
Detected USDT: 24.9339 (amount: 24.8139 + fee: 0.1200) from swift
Reduced 24.9339 USDT from San(Swift) (swift)
```

## Migration

No migration needed. The feature works automatically with existing balance messages. Just ensure staff accounts include "Swift" or "Wallet" in their names.


---

## BNB and Other Crypto Support

### Overview

Sometimes staff need to transfer BNB or other cryptocurrencies instead of USDT for network fees or other reasons. The bot automatically handles this by using the USD equivalent values shown in the receipt.

### How It Works

**The bot always uses USD values, never crypto amounts for non-USDT coins.**

When analyzing a receipt:
1. If it's USDT → use USDT amount directly
2. If it's BNB/ETH/other → use the USD equivalent shown in the receipt
3. Network fees are always extracted in USD

### Example: BNB Transfer

**Receipt shows:**
```
-0.005 BNB
4.31 $

Network fee: 0.000072 BNB (0.06 $)
```

**Bot processes:**
```
Amount: 4.31 USD (ignores -0.005 BNB)
Network fee: 0.06 USD (ignores 0.000072 BNB)
Total: 4.37 USD (4.31 + 0.06)
```

**Balance update:**
```
San(Swift): 100.0000 → 95.6300 USDT
(100.0000 - 4.37 = 95.63)
```

### Supported Coins

The bot can handle any cryptocurrency as long as the receipt shows the USD equivalent:
- **BNB** (Binance Coin)
- **ETH** (Ethereum)
- **USDT** (Tether)
- **BUSD** (Binance USD)
- **Any other coin** with USD value shown

### Key Rules

1. **Always use USD values** - Bot looks for "$" symbol in the receipt
2. **Ignore crypto amounts** - For non-USDT coins, crypto amounts are ignored
3. **Network fees in USD** - Always extract network fee USD value from parentheses
4. **USDT is special** - For USDT transfers, use USDT amount directly (no conversion needed)

### Examples

#### Example 1: BNB Transfer (Swift)

**Receipt:**
```
BNB Sent
-0.005 BNB
4.31 $

Network fee: 0.000072 BNB (0.06 $)
```

**Bot extracts:**
- Amount: 4.31 (from "4.31 $")
- Network fee: 0.06 (from "(0.06 $)")
- Total: 4.37
- Bank type: swift

**Transaction message:**
```
✅ Sell processed!

MMK: +2,500,000 (San(KBZ))
USDT: -4.3700
```

#### Example 2: ETH Transfer (Wallet)

**Receipt:**
```
Sent: 0.002 ETH
Value: 8.50 $

Gas fee: 0.00015 ETH (0.25 $)
```

**Bot extracts:**
- Amount: 8.50 (from "8.50 $")
- Network fee: 0.25 (from "(0.25 $)")
- Total: 8.75
- Bank type: wallet

#### Example 3: USDT Transfer (Normal)

**Receipt:**
```
USDT Sent
-24.813896 USDT

Network fee: (0.12 $)
```

**Bot extracts:**
- Amount: 24.813896 (from USDT amount)
- Network fee: 0.12 (from "(0.12 $)")
- Total: 24.933896
- Bank type: swift

### Why This Matters

**Problem:** Staff sends 0.005 BNB (worth $4.31) but bot would try to deduct 0.005 USDT (wrong!)

**Solution:** Bot uses the USD equivalent ($4.31) and deducts 4.31 USDT from balance (correct!)

### Technical Details

The OCR prompt specifically instructs:
```
IMPORTANT: We work with USD/USDT values, NOT other crypto amounts!

- If receipt shows USDT: use the USDT amount
- If receipt shows BNB/ETH/other coins: use the USD equivalent shown
- IGNORE the crypto amount (e.g., ignore "-0.005 BNB", use "4.31 $")
- Look for "$" symbol to find USD values
```

### Troubleshooting

**Issue: Bot deducts wrong amount for BNB transfer**

**Cause:** Receipt doesn't show USD equivalent

**Solution:** Ensure the receipt displays the USD value. Most wallets and exchanges show this automatically.

**Issue: Bot uses BNB amount instead of USD**

**Cause:** OCR couldn't find USD value

**Solution:** Check that the receipt clearly shows the USD amount with "$" symbol. If not visible, the transaction may need manual processing.

### Logging

The bot logs the extracted values:
```
USDT OCR: {'amount': 4.31, 'network_fee': 0.06, 'total_amount': 4.37, 'bank_type': 'swift'}
Detected USDT: 4.3700 (amount: 4.3100 + fee: 0.0600) from swift
Reduced 4.3700 USDT from San(Swift) (swift)
```

### Important Notes

1. **USD = USDT** - For balance purposes, $1 USD = 1 USDT
2. **Always check receipts** - Ensure USD values are visible in receipts
3. **Network fees included** - Total amount includes network fee for Swift/Wallet
4. **Binance is different** - Binance already includes fee in displayed amount
