# Design Decisions

## 1. Framework and Database

- Django is used for the application structure and data models.
- Django REST Framework provides the API endpoints.
- SQLite is used for local development to keep setup simple.

## 2. Wallet and Recharge

- Wallet balances and recharge amounts use decimal fields to avoid floating-point rounding errors.
- Each recharge has a unique reference.
- Recharge transactions begin with `pending` status and can be marked `success` or `failed`.
- Successful recharge processing checks the transaction status to avoid crediting the same recharge more than once.
- Recharge processing is mocked; no real payment gateway is integrated.

## 3. Session Lifecycle

- Sessions move through defined states: `unassigned`, `assigned`, `accepted_by_provider`, `in_progress`, and `completed`.
- API actions validate the current state before changing it.
- Invalid transitions return HTTP 400 with an explanatory error.
- Only the assigned provider can accept a session.
- Only the booking user can start a session.

## 4. Billing

- The per-minute price is stored on the session.
- Each billed minute is represented by a `SessionBilling` record.
- A unique constraint on the session and minute number prevents duplicate billing records.
- Database transactions and row locking are used to protect billing and wallet updates.
- A minute is charged only when the wallet can cover its full price.
- If the wallet cannot cover the next minute, the system completes the session automatically without charging that unaffordable minute.

## 5. Starting Balance

- Session creation requires a wallet balance of at least five times the session's per-minute price.
- This ensures the user has a minimum balance before beginning a consultation.

## 6. Authentication and Roles

- Authenticated API requests are required for session and recharge operations.
- User profiles distinguish `USER` and `PROVIDER` roles.
- API views enforce permissions based on the action being performed.

## 7. Testing

- Automated Django tests cover billing calculations, insufficient balance, duplicate billing, recharge callback idempotency, session lifecycle, invalid transitions, and session creation rules.

## 8. Scope Limitations

- No frontend, real payment gateway, chat/video functionality, or production background worker is included.
- SQLite is intended for local development.
