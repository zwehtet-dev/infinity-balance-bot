# Bot Flow — Infinity Balance Bot

This document describes how `bot.py` works end-to-end: configuration, storage, message routing, and every transaction flow it supports. It reflects the code as of the current `main` branch.

## 1. What the bot does

A Telegram bot for a MMK ⇄ USDT (and THB) exchange operation. It runs inside a single Telegram **group** that uses **forum topics**. Staff post transaction messages (Buy / Sell / P2P Sell / internal transfer) together with receipt photos, the bot OCRs the receipts with GPT-4o vision, matches them against registered bank accounts, and keeps a running balance sheet in memory (`context.chat_data['balances']`), persisted back to the group as a formatted message.

There is no external backend — balances live in the bot process's chat data and are reloaded from a pinned/posted balance message (see §4).

## 2. Configuration (env vars)

| Var | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token (required) |
| `OPENAI_API_KEY` | Used for GPT-4o OCR calls (required) |
| `TARGET_GROUP_ID` | The only chat the bot listens to; everything else is ignored |
| `USDT_TRANSFERS_TOPIC_ID` | Topic where Buy/Sell/P2P Sell transactions are posted (0/unset = main chat / topic 1) |
| `AUTO_BALANCE_TOPIC_ID` | Topic where balance snapshots are posted/read |
| `ACCOUNTS_MATTER_TOPIC_ID` | Topic for internal transfers between the business's own accounts |
| `ALERT_TOPIC_ID` | Where errors/status messages go (0 = reply to the triggering message instead) |
| `DATABASE_URL` | If set to a `postgres...` URL, uses Postgres; otherwise falls back to SQLite (`SQLITE_DB_FILE`, default `bot_data.db`) |

`main()` builds the `Application` with generous timeouts (60s) for slow networks, registers command handlers plus one catch-all `MessageHandler(filters.ALL, handle_message)`, and runs polling with `drop_pending_updates=True`.

## 3. Storage

Two tiers:

- **In-memory / per-chat** (`context.chat_data`): the current `balances` dict (`mmk_banks`, `usdt_banks`, `thb_banks` — each a list of `{bank_name, amount, prefix, bank}`), plus transient media-group collection buffers. This is lost on bot restart unless a fresh balance message is loaded.
- **Database** (Postgres or SQLite, `get_db_connection()` / `init_database()`): durable config and OCR cache —
  - `user_prefixes` — maps a Telegram `user_id` to a staff prefix (e.g. `San`, `OKM`) used to pick "their" bank accounts.
  - `settings` — key/value, currently just the default receiving USDT account.
  - `mmk_bank_accounts` / `usdt_bank_accounts` — registered account numbers/wallets used to verify OCR'd receipts actually belong to the business (seeded with default banks on first run).
  - `media_group_photos` — downloaded photos for a Telegram media group, keyed by `(media_group_id, message_id)`, so photos survive across handler calls / restarts.
  - `sale_receipt_ocr` — pre-computed OCR results for a sale message's receipt(s), keyed by `(message_id, receipt_index)`, so the staff's later reply doesn't need to re-OCR.
  - Periodic cleanup (`_periodic_cleanup`, started from `_post_init`) deletes old media-group photos (>24h) and OCR cache rows (>48h).

## 4. Balance loading & format

Balance is a plain-text message posted in the Auto Balance topic, e.g.:

```
San(Kpay P) -2639565
San(KBZ)-11044185
USDT
San(Swift) -81.99
THB
ACT(Bkk B) -13223
```

`parse_balance_message()` splits on the `USDT`/`THB` markers and regexes out `Prefix(Bank) -amount` triples for each section (hyphen is a separator, not a sign). Any message containing `USDT` posted in `AUTO_BALANCE_TOPIC_ID` is auto-loaded into `context.chat_data['balances']`; `/load` does the same by replying to a message anywhere. `format_balance_message()` renders it back (MMK/THB as integers, USDT to 4 decimals) and is what gets posted after every balance-changing transaction.

## 5. Message routing (`handle_message`)

Every non-command message in the target group passes through one big router:

1. Ignore anything outside `TARGET_GROUP_ID`, and anything without `from_user` (anonymous admins/channel posts — transactions need a real sender).
2. **Auto Balance topic** → parse as balance and cache; stop.
3. **Accounts Matter topic** → treat as an internal transfer (`process_internal_transfer`); stop.
4. Otherwise, must be in `USDT_TRANSFERS_TOPIC_ID` (or main chat if unset) — either directly, or as a reply to a message that was posted there (Telegram forum reply semantics: `reply_to_message.message_thread_id` is the real location). Anything else is skipped.
5. **Immediate sale OCR**: if the message has a photo, is not a reply, and its text is a Buy/Sell (not P2P/fee) message, the receipt is OCR'd right away and cached in `sale_receipt_ocr` — so when staff reply later, no OCR round-trip is needed. Media-group sale photos are saved to disk immediately and OCR'd after a short delay once all photos have arrived.
6. **Staff P2P Sell** (`P2P Sell ... From X(Y)` shorthand) — detected from message text alone, no photos required; processed and routed away immediately.
7. **P2P Sell** (`fee` in text) — either has an explicit bank breakdown (no OCR) or needs receipt photo(s) (single photo processed immediately; media group is buffered in `context.chat_data['p2p_sell_media_groups']` and processed after an 8s delay to let all photos land).
8. Any other non-first photo in a P2P-sell or internal-transfer media group is appended to the pending group's buffer and the handler returns (waiting for the delayed processor).
9. **Regular Buy/Sell**: requires the message to be a **reply to a photo**. If the replied-to message was part of a Telegram media group not yet seen, the bot best-effort re-fetches sibling messages by forwarding/deleting adjacent message IDs to recover all photos (Telegram doesn't expose media groups directly). Single photo vs. media-group replies are routed to the immediate or delayed (`process_media_group_delayed`, 1.5s) processors respectively, which in turn call `process_buy_transaction[_bulk]` / `process_sell_transaction[_bulk]`.

## 6. Transaction detection (`extract_transaction_info`)

Parses the *original* (non-reply) message text into a `tx_info` dict. Checked in this order:

1. **Staff P2P Sell**: `P2P Sell 440.18x4021 =1770000 ... to OKM (KBZ) From OKM(Swift)` → `{type: 'staff_p2p_sell', mmk, usdt, rate, dest_bank, src_bank}`. Direct bank-to-bank move, no OCR.
2. **P2P Sell (new format)**: `P2P Sell 1277.27×4148.30=5298500fee-0.12 ...` → `{type: 'p2p_sell', mmk, usdt, rate, fee, total_usdt = usdt+fee, bank_breakdown?}`. Optionally includes a bank breakdown (`AMOUNT to PREFIX (BANK)` repeated).
3. **P2P Sell (legacy format, `fee-`)**: `sell 13000000/3222.6=4034.00981 fee-6.44` → same shape as above.
4. **Regular Buy/Sell**: any text containing the word `buy` or `sell` → `{type, usdt, mmk}` (amount after the type word, MMK after `=`). Missing/zero amounts are allowed — OCR fills them in later.

## 7. Transaction flows

All flows share the same pattern: OCR receipt(s) → validate against registered accounts/balances → mutate `balances` in place → post the new balance to `AUTO_BALANCE_TOPIC_ID` → post a ✅/⚠️/❌ status via `send_status_message` / `send_alert` to `ALERT_TOPIC_ID`. Validation (bank exists, sufficient balance) always happens **before** any mutation so a failed check can't leave balances half-updated.

### Buy — `process_buy_transaction` / `process_buy_transaction_bulk`
The business buys USDT from the customer: customer sends USDT to one of the business's wallets, business sends MMK to the customer.
- **Sale message** (no reply, has photo): treated as the customer's USDT-received receipt. OCR'd with `ocr_match_usdt_receipt_to_banks` against all registered USDT wallets to find which wallet and how much came in; cached as a `pending_transaction` + `sale_receipt_ocr` row; bot posts "waiting for MMK receipt".
- **Staff reply** (photo replying to the sale message): OCR'd with `ocr_detect_mmk_bank_and_amount` restricted to the replying staff's prefix — this is the MMK the staff paid out. Supports a `fee-NNN` suffix in the staff's caption, added to the MMK total. Reuses the cached USDT OCR from the sale message when available (falls back to re-OCRing the original photo). Verifies MMK subtotal against the message's stated amount (10% / 1000 MMK tolerance, warn-only), checks the staff's MMK bank has sufficient funds, then: **-MMK** from staff's bank, **+USDT** to the detected (or default) receiving wallet.
- `_bulk` variant is the same logic driven by an in-memory list of photos (media group) instead of a single `message.photo`.

### Sell — `process_sell_transaction` / `process_sell_transaction_bulk`
Customer sells USDT to the business (sends MMK to us, we send USDT to them).
- **Sale message**: photo is the customer's MMK-receipt; OCR'd with `ocr_detect_mmk_bank_multi` against **all** registered MMK banks (not staff-specific, since anyone can post a sale). Cached as `pending_transaction` + `sale_receipt_ocr`.
- **Staff reply**: photo(s) are the USDT sent to the customer, OCR'd with `ocr_extract_usdt_with_fee` (handles Swift/Wallet vs. exchange fee semantics). Staff caption can include `fee-NNN` (added to MMK) and/or `From Prefix(Bank)` to force which MMK bank receives the funds (bypassing OCR bank detection, only amount is OCR'd in that case). Supports multiple MMK receipts (media group) summed together, either from the pre-scanned cache or by fetching photos from `media_group_photos`. Validates USDT balance in `Prefix(BankType)` (e.g. `San(Swift)`) is sufficient, then: **+MMK** to detected bank, **-USDT** from staff's account.
- `_bulk` variant mirrors this for delayed media-group processing.

### P2P Sell — three sub-flows, staff sells USDT to another exchange (not to a customer)
- **`process_staff_p2p_sell`** — shorthand `... to DEST(BANK) From SRC(BANK)`, both banks parsed directly from text, no OCR: **+MMK** to `dest_bank`, **-USDT** from `src_bank`.
- **`process_p2p_sell_with_breakdown`** — message specifies `AMOUNT to Prefix(Bank)` one or more times; resolves and validates every destination bank first, resolves the staff's USDT source via `find_staff_usdt_bank` (prefers a `Binance` account matching the staff's prefix, else any of their USDT banks), verifies balance, then applies all MMK credits and the single USDT debit (`usdt + fee`).
- **`process_p2p_sell_with_photos` / `process_p2p_sell_transaction`** — no breakdown given; OCRs each MMK receipt with `ocr_detect_mmk_bank_and_amount` scoped to the staff's own prefix (unlike regular Sell, P2P sell receipts belong to staff, not customers), sums them, same Binance-preferred USDT debit as above. The `_with_photos` variant takes photos already buffered in memory (media group case); `_transaction` variant handles the single-photo / fetch-from-db cases.

### Internal transfer — `process_internal_transfer` / `_with_photos`, `process_coin_transfer`
Posted in the **Accounts Matter** topic. Text format `Prefix(Bank) to Prefix(Bank)`, one or more receipt photos (media group buffered 8s in `context.chat_data['internal_transfer_media_groups']`).
- First tries `process_coin_transfer`: a stricter pattern with an explicit network fee, `X(bank) to Y(bank) AMOUNT USDT-FEE USDT(fee) = RECEIVED USDT` — sent amount is debited, received (post-fee) amount is credited, no OCR needed.
- Otherwise `process_internal_transfer_with_photos`: OCRs each receipt with GPT-4o (choosing `ocr_extract_usdt_with_fee` for Swift/Wallet/Binance-flavoured USDT moves, or a generic "extract the amount" JSON prompt for everything else including MMK/THB), sums them, validates source balance, and moves the **same** amount from source to destination (no fee differential). Currency label in the confirmation message is inferred from the account names (`swift/wallet/binance` → USDT, `thb` → THB, else MMK).

## 8. OCR functions (all GPT-4o vision via `AsyncOpenAI`, JSON-mode responses)

| Function | Used for | Notes |
|---|---|---|
| `ocr_detect_mmk_bank_and_amount` | Buy staff-reply, P2P sell receipts | Filters candidate banks to one staff prefix first |
| `ocr_detect_mmk_bank_multi` | Sell sale-message, Sell staff-reply | Matches against **all** registered MMK banks with a confidence score |
| `ocr_detect_mmk_banks_multiple` | (multi-image variant, batch detection) | |
| `ocr_match_mmk_receipt_to_banks` | Immediate sale OCR cache | Confidence-scored match against a bank list carrying account numbers |
| `ocr_extract_usdt_amount` | legacy/unused fallback | kept for backward compatibility |
| `ocr_extract_usdt_with_fee` | Sell/Internal-transfer staff USDT receipts | Extracts sent amount + network fee + bank type (swift/wallet/binance) |
| `ocr_extract_usdt_received` | Buy customer USDT-received receipts | |
| `ocr_match_usdt_receipt_to_banks` | Buy sale-message | Confidence-scored match against registered wallets |

All OCR calls degrade gracefully: on failure or `None` result, the code falls back to the amount stated in the message text (if any) and/or sends an alert instead of silently proceeding.

## 9. Commands

| Command | Purpose |
|---|---|
| `/start` | Help text |
| `/balance` | Show current in-memory balance |
| `/load` (reply to a balance text) | Re-parse and cache balances |
| `/set_user <user_id\|reply> <prefix>` | Map a Telegram user to a staff prefix (e.g. `San`) |
| `/list_users`, `/remove_user` | Manage prefix mappings |
| `/set_receiving_usdt_acc`, `/show_receiving_usdt_acc` | Default USDT wallet credited on Buy when OCR can't detect one |
| `/set_mmk_bank`, `/edit_mmk_bank`, `/remove_mmk_bank`, `/list_mmk_bank` | Manage registered MMK bank accounts (used for OCR verification) |
| `/set_usdt_bank`, `/edit_usdt_bank`, `/remove_usdt_bank`, `/list_usdt_banks` | Manage registered USDT wallets |
| `/test` | Connectivity/config check |

Command responses go to `ALERT_TOPIC_ID` via `send_command_response` (or the main chat if unset).

## 10. Error handling

`error_handler` is registered as the global PTB error handler (logs uncaught exceptions). Within flows, `send_alert` is used for user-facing failures (missing balance, bank not found, insufficient funds, unreadable receipt) and `send_status_message` for warnings/success, both routed to `ALERT_TOPIC_ID` when configured.
