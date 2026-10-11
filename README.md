# Django Wallet-Based Per-Minute Session Billing

## Overview

A Django REST Framework application for wallet-based billing of one-to-one consultation sessions. Users recharge their wallets, book sessions with providers, and are charged for billable minutes.

## Technologies

- Python
- Django
- Django REST Framework
- SQLite (local development)
- Django authentication

## Features

- Wallet balance management
- Mock wallet recharge and callback processing
- Duplicate successful recharge callback protection
- User and provider roles
- Consultation session lifecycle management
- Per-minute wallet deductions
- Automatic session termination when the wallet cannot cover the next minute
- Prevention of duplicate minute billing
- Automated tests

## Project Structure

- `config/` — Django project configuration and root URLs
- `user_accounts/` — wallet, recharge, and user profile functionality
- `consultations/` — consultation sessions and billing
- `manage.py` — Django management command
- `db.sqlite3` — local development database

## Setup

Run these commands from the project root.

1. Create and activate a virtual environment.

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies.

   ```powershell
   pip install django djangorestframework
   ```

   Install any additional packages required by your project if applicable.

3. Apply database migrations.

   ```powershell
   python manage.py migrate
   ```

4. Create a superuser if needed.

   ```powershell
   python manage.py createsuperuser
   ```

5. Start the development server.

   ```powershell
   python manage.py runserver
   ```

## Running Tests

Run the complete test suite:

```powershell
python manage.py test
```

Run consultation tests:

```powershell
python manage.py test consultations
```

Run wallet and recharge tests:

```powershell
python manage.py test user_accounts
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/wallet/recharge/` | Create a mock recharge |
| POST | `/api/wallet/recharge/callback/` | Process a recharge callback |
| POST | `/api/consultations/sessions/` | Create a consultation session |
| POST | `/api/consultations/sessions/<id>/accept/` | Provider accepts a session |
| POST | `/api/consultations/sessions/<id>/start/` | User starts a session |
| POST | `/api/consultations/sessions/<id>/bill/` | Process elapsed-minute billing |
| POST | `/api/consultations/sessions/<id>/end/` | End a session |

Authenticated requests are required for these endpoints.

## Billing Rules

- The wallet must contain at least five times the session price per minute before a session can be created.
- The session price is fixed when the session is created.
- Billing records identify the billed minute for each session.
- The wallet must not become negative.
- If the wallet cannot cover the next minute, the system ends the session automatically.
- A successful recharge callback must not credit the same recharge twice.

## Notes

- Recharge processing is mocked; this project does not integrate with a real payment gateway.
- SQLite is used for local development.
- Run the automated tests before submitting changes.
