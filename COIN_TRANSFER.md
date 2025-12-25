# Coin Transfer with Network Fee

## Overview
The bot now supports coin transfers between USDT accounts with automatic network fee handling. This is useful when staff transfer USDT between different platforms (e.g., Binance to Wallet) using blockchain networks like TRC20 (Tron).

**Important:** Photo is optional - bot uses amounts from text, not OCR!

## Format
When staff sends a coin transfer message in the **Accounts Matter** topic, they should use this format:

```
San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT
```

Or with optional photo:
```
[Receipt Photo]
San (binance) to OKM(swift) 10 USDT-0.47 USDT(fee) = 9.53 USDT
```

### Format Breakdown:
- **Source Account**: `San (binance)` - The account sending USDT
- **Destination Account**: `OKM(Wallet)` - The account receiving USDT
- **Sent Amount**: `10 USDT` - The amount withdrawn/sent from source
- **Network Fee**: `0.47 USDT(fee)` - The blockchain network fee
- **Received Amount**: `9.53 USDT` - The amount received at destination

## How It Works

1. **Staff sends message** in Accounts Matter topic with:
   - Text in the format above (REQUIRED)
   - Receipt photo (OPTIONAL - for reference only)

2. **Bot processes**:
   - Extracts amounts **from text** (NO OCR)
   - Reduces **10 USDT** from `San(binance)`
   - Adds **9.53 USDT** to `OKM(Wallet)`
   - The 0.47 USDT fee is automatically accounted for

3. **Balance updated** and posted to Auto Balance topic

4. **Success message** sent to Alert topic

## Key Points

### Photo is Optional
- Bot reads amounts from text, not from photo OCR
- Photo can be attached for reference/proof
- This makes processing faster and more accurate

### Text Format is Required
- Staff must type the amounts correctly in the message
- Format must match: `Prefix(Bank) to Prefix(Bank) AMOUNT USDT-FEE USDT(fee) = RECEIVED USDT`

### Only in Accounts Matter Topic
- This feature only works in Accounts Matter topic
- Will not process in USDT Transfers topic or main chat

## Examples

### Example 1: Binance to Wallet Transfer (No Photo)
```
San (binance) to OKM(Wallet) 10 USDT-0.47 USDT(fee) = 9.53 USDT
```
- Reduces 10 USDT from San(binance)
- Adds 9.53 USDT to OKM(Wallet)

### Example 2: With TRC20 Receipt Photo
```
[TRC20 Receipt Photo]
San (binance) to OKM(swift) 10 USDT-0.47 USDT(fee) = 9.53 USDT
```
- Photo is for reference only
- Bot uses amounts from text: 10, 0.47, 9.53

### Example 3: Wallet to Binance Transfer
```
MMN (Wallet) to MMN (binance) 50 USDT-1.2 USDT(fee) = 48.8 USDT
```
- Reduces 50 USDT from MMN(Wallet)
- Adds 48.8 USDT to MMN(binance)

### Example 3: Swift to Wallet Transfer
```
[BEP20 Receipt Photo]
TZT (Swift) to TZT (Wallet) 100 USDT-0.15 USDT(fee) = 99.85 USDT
```
- Reduces 100 USDT from TZT(Swift)
- Adds 99.85 USDT to TZT(Wallet)

## Important Notes

1. **Account Names Must Match**: The account names in the message must exactly match the names in your balance (case-insensitive, spaces ignored)

2. **USDT Accounts Only**: This feature only works with USDT accounts (not MMK or THB)

3. **Sufficient Balance Required**: The source account must have enough USDT to cover the sent amount

4. **Accounts Matter Topic**: This feature only works in the Accounts Matter topic

5. **Receipt Photo Required**: A receipt photo must be attached (though it's not OCR'd, it's for record keeping)

## Error Messages

- **❌ Balance not loaded**: Post balance message in auto balance topic first
- **❌ Source USDT account not found**: Check the source account name spelling
- **❌ Destination USDT account not found**: Check the destination account name spelling
- **❌ Insufficient USDT balance**: Source account doesn't have enough USDT

## Format Requirements

The message must follow this exact pattern:
```
Prefix(Bank) to Prefix(Bank) AMOUNT USDT-FEE USDT(fee) = RECEIVED USDT
```

Key points:
- Use `to` (lowercase) between accounts
- Include `USDT` after amounts
- Use `-` before fee
- Include `(fee)` after fee amount
- Use `=` before received amount
- Spaces around parentheses are optional

## Difference from Regular Internal Transfer

| Feature | Coin Transfer | Regular Internal Transfer |
|---------|--------------|---------------------------|
| Format | Includes fee calculation | Simple "A to B" format |
| OCR | No OCR needed | OCR detects amount from receipt |
| Amounts | Two amounts (sent & received) | One amount |
| Use Case | Blockchain transfers with fees | Bank-to-bank transfers |
| Topic | Accounts Matter | Accounts Matter |

## Related Features

- [Internal Transfers](FEATURES_OVERVIEW.md#internal-transfers) - Regular transfers without fees
- [USDT Network Fees](SWIFT_WALLET_NETWORK_FEE.md) - Network fee handling in buy/sell
- [Accounts Matter Topic](ALERT_TOPIC.md) - Topic configuration
