# Entity-Relationship (ER) Diagram

## Database Relationships

```mermaid
erDiagram
    USER ||--|| WALLET : owns
    USER ||--o{ RECHARGE_TRANSACTION : makes
    USER ||--|| USER_PROFILE : has
    USER ||--o{ CONSULTATION_SESSION : books
    USER o|--o{ CONSULTATION_SESSION : provides
    CONSULTATION_SESSION ||--o{ SESSION_BILLING : contains

    USER {
        int id PK
        string username
    }

    WALLET {
        int id PK
        int user_id FK
        decimal balance
    }

    USER_PROFILE {
        int id PK
        int user_id FK
        string role
    }

    RECHARGE_TRANSACTION {
        int id PK
        int user_id FK
        decimal amount
        string reference UK
        string status
        datetime created_at
    }

    CONSULTATION_SESSION {
        int id PK
        int user_id FK
        int provider_id FK
        string status
        decimal price_per_minute
        datetime started_at
        datetime ended_at
        int billed_minutes
        decimal total_amount
        string ended_by
        string end_reason
    }

    SESSION_BILLING {
        int id PK
        int session_id FK
        int minute_number
        decimal amount
        datetime billed_at
    }
```

## Constraints

- Each wallet belongs to one user.
- Each user has one profile with a role such as `USER` or `PROVIDER`.
- Recharge references are unique.
- Each consultation session belongs to a user and may have an assigned provider.
- Each session can have multiple billing records.
- The combination of session and minute number is unique in `SessionBilling`, preventing duplicate records for the same billed minute.
