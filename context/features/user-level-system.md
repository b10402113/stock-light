# User Level System Spec

## Overview

Implement a user tier/level system with four distinct levels managed through a separate Plan domain. Plans track user-level relationships with expiration dates and pricing.

## Requirements

### User Levels Definition

| Level | Name | Monthly Price | Yearly Price | Description |
|-------|------|---------------|--------------|-------------|
| 1 | 普通用戶 (Regular) | $0 | $0 | Free tier, default for new users |
| 2 | Pro用戶 (Pro) | TBD | TBD | Enhanced features with higher quotas |
| 3 | Pro Max用戶 (Pro Max) | TBD | TBD | Premium tier with maximum quotas |
| 4 | Admin | N/A | N/A | Administrative access (not purchasable) |

**Note:** Please specify the monthly and yearly prices for Level 2 and Level 3.

### Plan Domain (New Module)

Create new `src/plans/` domain module following project structure:

```
src/plans/
├── model.py      # Plan SQLAlchemy model
├── schema.py     # Plan Request/Response schemas
├── service.py    # Plan business logic
└── router.py     # Plan API endpoints (if needed)
```

### Database Changes

#### New `plans` Table

- `id`: BIGSERIAL PRIMARY KEY
- `user_id`: BIGINT (FK to users.id, indexed)
- `level`: Integer (1-4, NOT NULL)
- `billing_cycle`: String(10) (NOT NULL, 'monthly' or 'yearly')
- `price`: Decimal(10,2) (NOT NULL, price paid at purchase time)
- `due_date`: DateTime (NOT NULL, expiration date)
- `is_active`: Boolean (NOT NULL, default=True)
- `created_at`: DateTime (NOT NULL)
- `updated_at`: DateTime (NOT NULL)

#### New `level_configs` Table

Store configuration and pricing per level:

- `level`: Integer (1-4, PRIMARY KEY)
- `name`: String(50) (NOT NULL, display name)
- `monthly_price`: Decimal(10,2) (NOT NULL, default=0.00)
- `yearly_price`: Decimal(10,2) (NOT NULL, default=0.00)
- `max_subscriptions`: Integer (NOT NULL)
- `max_alerts`: Integer (NOT NULL)
- `features`: JSON (nullable, feature flags)
- `is_purchasable`: Boolean (NOT NULL, default=True)
- `created_at`: DateTime (NOT NULL)
- `updated_at`: DateTime (NOT NULL)

**Default Level Configs:**

| level | name | monthly_price | yearly_price | max_subscriptions | max_alerts | is_purchasable |
|-------|------|---------------|--------------|-------------------|------------|----------------|
| 1 | Regular | 0.00 | 0.00 | 10 | 10 | false |
| 2 | Pro | TBD | TBD | 50 | 50 | true |
| 3 | Pro Max | TBD | TBD | 100 | 100 | true |
| 4 | Admin | 0.00 | 0.00 | unlimited | unlimited | false |

#### User Model Changes

- Keep existing fields unchanged
- Remove `subscription_status` field (replaced by Plan relationship)
- User's current level determined by active Plan record

### Business Logic

- User can have multiple Plan records (history tracking)
- Only one active Plan per user at any time
- Billing cycle determines duration:
  - Monthly: due_date = purchase_date + 1 month
  - Yearly: due_date = purchase_date + 1 year
- When Plan expires (due_date < now), auto-downgrade to Level 1
- Admin level (4) should NOT have due_date restrictions (permanent)
- New users automatically get Level 1 Plan with permanent due_date
- Plan price recorded at purchase time (may differ from current level_config price)

### API Endpoints

- GET `/plans/me` - Get current user's active plan
- GET `/plans/levels` - List all purchasable levels with prices
- POST `/plans` (Admin only) - Create/upgrade plan for user
- PUT `/plans/{plan_id}` (Admin only) - Update plan details
- DELETE `/plans/{plan_id}` (Admin only) - Cancel plan

### Level Capabilities

Each level defines:
- Level 1: 10 subscriptions, 10 alerts, basic features (free)
- Level 2: 50 subscriptions, 50 alerts, advanced features (paid)
- Level 3: 100 subscriptions, 100 alerts, all features (paid)
- Level 4: Unlimited, admin features (not purchasable)

### Migration Strategy

1. Create `level_configs` table with default data
2. Create `plans` table
3. Seed existing users with Level 1 Plan records
4. Remove `subscription_status` column from `users` table
5. Update quota validation to use Plan level

## References

- @src/users/model.py - Current User model structure
- @docs/rules/architecture.md - Domain module structure
- @docs/rules/database.md - Database migration guidelines
- @src/subscriptions/service.py - Quota validation logic