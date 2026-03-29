# Booking Management System
Backend REST API for managing organizational resources and their bookings.
The system allows users to browse available resources, check availability, create and manage reservations, while managers and administrators have additional resource and booking management capabilities.
The project focuses on production-oriented backend concepts rather than simple CRUD:
- business logic separated into service and selector layers;
- booking overlap detection;
- transaction safety;
- PostgreSQL row-level locking;
- race-condition protection;
- role-based authorization;
- object-level ownership security;
- audit history;
- structured logging;
- automated tests;
- Docker;
- OpenAPI / Swagger documentation.
---
## Tech Stack
### Backend
- Python 3.12+
- Django 5.2
- Django REST Framework
- SimpleJWT
- django-filter
- drf-spectacular
- Redis
- Celery
- Celery Beat
- django-celery-beat
### Database
- PostgreSQL 16
### Infrastructure
- Docker
- Docker Compose
### Testing and Code Quality
- pytest
- pytest-django
- Ruff
---
## Main Features
### Authentication
The project uses a custom Django user model with email-based authentication.
Roles:
```text
USER
MANAGER
ADMIN
```
Authentication is handled using JWT access and refresh tokens.
Available authentication operations include:
```text
registration
login
token refresh
current user
```
---
## Resource Management
Resources represent bookable organizational assets such as:
```text
meeting rooms
workplaces
classrooms
vehicles
equipment
projectors
```
Each resource contains information about:
```text
category
location
capacity
active status
minimum booking duration
maximum booking duration
available working hours
```
Resources support soft deletion through:
```text
is_active = False
```
Historical resources used by bookings are not physically deleted.
---
## Booking Management
Users can:
```text
create bookings
view their bookings
view booking details
update bookings
cancel bookings
check resource availability
```
Managers and administrators can additionally manage bookings belonging to other users.
Business cancellation does not delete the booking.
Instead:
```text
CONFIRMED
    ↓
CANCELLED
```
and:
```text
cancelled_at
```
is recorded.
---
## Booking Validation
Booking creation and modification are handled through the service layer.
The system validates:
```text
start_at < end_at
booking is not in the past
resource is active
minimum booking duration
maximum booking duration
resource working hours
same-day booking policy
booking overlap
```
Validation logic is not implemented directly inside API views.
---
## Booking Conflict Detection
Two active bookings for the same resource cannot overlap.
The overlap rule is:
```python
existing.start_at < new_end
and
existing.end_at > new_start
```
Example:
```text
Existing:
10:00 ───────── 11:00
New:
       10:30 ───────── 11:30
Result:
CONFLICT
```
Adjacent bookings are allowed:
```text
10:00 ─── 11:00
            11:00 ─── 12:00
```
Cancelled bookings do not block the resource.
---
## Concurrency Protection
A simple overlap query is not sufficient because two requests can execute concurrently.
Without locking:
```text
Transaction A                Transaction B
check overlap → free
                             check overlap → free
create booking
                             create booking
commit
                             commit
```
This could create two overlapping bookings.
The project solves this using PostgreSQL transactions and row-level locking:
```python
transaction.atomic()
```
together with:
```python
Resource.objects.select_for_update()
```
The resource row is locked before performing the final overlap check and inserting the booking.
The effective flow is:
```text
BEGIN
  ↓
SELECT Resource FOR UPDATE
  ↓
validate booking
  ↓
check overlap
  ↓
create booking
  ↓
COMMIT
```
If two requests attempt to reserve the same resource simultaneously, only one booking succeeds.
A dedicated concurrent integration test verifies:
```text
successful_bookings == 1
```
---
## Booking Lifecycle
Booking state changes are handled through dedicated service functions:
```python
create_booking()
update_booking()
cancel_booking()
complete_booking()
```
Current booking statuses:
```text
PENDING
CONFIRMED
CANCELLED
COMPLETED
```
`CANCELLED` and `COMPLETED` are treated as terminal states.
---
## Resource Availability
The API can calculate resource availability for a particular date.
Example:
```text
Resource working hours:
08:00 ─────────────────────────── 20:00
Existing bookings:
       10:00 ─ 11:00
                       14:00 ─ 16:00
Available intervals:
08:00 ─ 10:00
11:00 ─ 14:00
16:00 ─ 20:00
```
Available intervals shorter than the resource's minimum booking duration are not returned.
The availability endpoint is informational.
The authoritative availability check is still performed when the booking is created inside a database transaction.
---
## Authorization and IDOR Protection
Regular users may access only their own bookings.
For example:
```text
User A owns Booking #10
```
User B cannot:
```text
GET   /api/v1/bookings/10/
PATCH /api/v1/bookings/10/
POST  /api/v1/bookings/10/cancel/
GET   /api/v1/bookings/10/history/
```
Foreign objects are hidden through the queryset and return:
```text
404 Not Found
```
Managers and administrators can access all bookings.
---
## Booking History and Audit Trail
Critical booking operations generate persistent audit entries.
Supported actions:
```text
CREATED
UPDATED
CANCELLED
COMPLETED
```
Each history record stores:
```text
booking
actor
action
old state
new state
timestamp
```
Example timeline:
```text
Booking #42
CREATED
by user@example.com
        ↓
UPDATED
by manager@example.com
        ↓
CANCELLED
by user@example.com
```
Audit creation occurs in the same transaction as the booking operation.
Therefore:
```text
Booking mutation
+
BookingHistory entry
```
are committed atomically.
Audit records are read-only from the API.
---
## Structured Logging
The application uses structured JSON logging.
Operational events include:
```text
booking_created
booking_updated
booking_cancelled
booking_completed
booking_conflict
booking_validation_failed
api_access_denied
unhandled_api_exception
```
Each HTTP request receives a unique request identifier:
```text
X-Request-ID
```
This allows related logs to be correlated across the request lifecycle.
Sensitive information such as passwords, JWT tokens and secret keys is never intentionally written to application logs.
Unexpected exceptions are logged server-side with their traceback, while API clients receive only a safe generic response.
Example:
```json
{
    "detail": "Internal server error.",
    "code": "internal_error"
}
```
---
## Architecture
The project separates responsibilities across layers:
```text
HTTP Request
     │
     ▼
DRF View
     │
     ▼
Serializer
     │
     ├───────────────┐
     ▼               ▼
 Service          Selector
     │               │
     ▼               ▼
Business Logic     Read Queries
     │               │
     └───────┬───────┘
             ▼
         PostgreSQL
```
Main responsibilities:
```text
models.py
→ database schema and relations
serializers.py
→ API input/output representation
views.py
→ HTTP orchestration
services.py
→ write-side business logic
selectors.py
→ read-side queries
permissions.py
→ authorization rules
audit/
→ persistent business audit trail
```
---
## Project Structure
```text
booking-management-api/
│
├── apps/
│   ├── accounts/
│   ├── resources/
│   ├── bookings/
│   └── audit/
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   │
│   ├── api_exceptions.py
│   ├── logging.py
│   ├── middleware.py
│   └── urls.py
│
├── docs/
│   └── erd.md
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pyproject.toml
├── pytest.ini
├── requirements.txt
└── README.md
```
---
## Database Model
The main entities are:
```text
User
ResourceCategory
Resource
Booking
BookingHistory
```
Relationships:
```text
User 1 ─────── N Booking
ResourceCategory 1 ─────── N Resource
Resource 1 ─────── N Booking
Booking 1 ─────── N BookingHistory
User 1 ─────── N BookingHistory
               changed_by
```
The complete ERD is available in:
```text
docs/erd.md
```
---
## API
Base URL:
```text
/api/v1/
```
### Authentication
```text
POST /api/v1/auth/register/
POST /api/v1/auth/login/
POST /api/v1/auth/token/refresh/
GET  /api/v1/auth/me/
```
### Categories
```text
GET    /api/v1/categories/
POST   /api/v1/categories/
GET    /api/v1/categories/{id}/
PATCH  /api/v1/categories/{id}/
DELETE /api/v1/categories/{id}/
```
### Resources
```text
GET    /api/v1/resources/
POST   /api/v1/resources/
GET    /api/v1/resources/{id}/
PATCH  /api/v1/resources/{id}/
DELETE /api/v1/resources/{id}/
```
Availability:
```text
GET /api/v1/resources/{id}/availability/?date=YYYY-MM-DD
```
### Bookings
```text
GET   /api/v1/bookings/
POST  /api/v1/bookings/
GET   /api/v1/bookings/{id}/
PATCH /api/v1/bookings/{id}/
POST  /api/v1/bookings/{id}/cancel/
GET   /api/v1/bookings/{id}/history/
```
Physical booking deletion through the REST API is intentionally not supported.
---
## Booking Filters
Booking list supports filters such as:
```text
?resource=
?user=
?status=
?date_from=
?date_to=
```
Ordering:
```text
?ordering=start_at
?ordering=-start_at
?ordering=-created_at
```
---
## API Documentation
OpenAPI schema:
```text
http://127.0.0.1:8000/api/schema/
```
Swagger UI:
```text
http://127.0.0.1:8000/api/docs/
```
Redoc:
```text
http://127.0.0.1:8000/api/redoc/
```
Swagger supports JWT authorization, allowing the API to be tested directly from the browser.
---
## Environment Variables
Create:
```text
.env
```
based on:
```text
.env.example
```
Example:
```dotenv
SECRET_KEY=change-me
DEBUG=True
POSTGRES_DB=booking_management
POSTGRES_USER=booking_user
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
LOG_LEVEL=INFO
```
Never commit the real `.env` file.
---
## Local Installation
Clone the repository:
```bash
git clone <repository-url>
cd booking-management-api
```
Create a virtual environment.
Windows:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Install dependencies:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```
Create environment configuration:
```powershell
Copy-Item .env.example .env
```
Start PostgreSQL:
```bash
docker compose up -d db
```
Apply migrations:
```bash
python manage.py migrate
```
Run the development server:
```bash
python manage.py runserver
```
---
## Docker
Build and start the application:
```bash
docker compose up -d --build
```
Check containers:
```bash
docker compose ps
```
View web logs:
```bash
docker compose logs -f web
```
Apply migrations inside the container if required:
```bash
docker compose exec web python manage.py migrate
```
---
## Admin
Create a superuser:
```bash
python manage.py createsuperuser
```
Admin panel:
```text
http://127.0.0.1:8000/admin/
```
---
## Testing
Start PostgreSQL first:
```bash
docker compose up -d db
```
Run the complete test suite:
```bash
python -m pytest -v
```
Run booking tests:
```bash
python -m pytest apps/bookings/tests/ -v
```
Run the concurrency test:
```bash
python -m pytest apps/bookings/tests/test_concurrency.py -v
```
Run audit tests:
```bash
python -m pytest apps/audit/tests/ -v
```
---
## Code Quality
Ruff:
```bash
ruff check .
```
Formatting validation:
```bash
ruff format --check .
```
Apply formatting:
```bash
ruff format .
```
---
## Django Checks
Run Django system checks:
```bash
python manage.py check
```
Verify that no migrations are missing:
```bash
python manage.py makemigrations --check --dry-run
```
---
## OpenAPI Validation
Validate generated OpenAPI documentation:
```bash
python manage.py spectacular --file schema.yml --validate --fail-on-warn
```
The generated `schema.yml` may be removed afterwards if it is not tracked in the repository.
---
## Implemented Scope
Implemented:
```text
JWT authentication
custom user model
role-based permissions
resource categories
resource management
resource soft delete
booking CRUD lifecycle
booking filters
resource availability
overlap protection
PostgreSQL transactions
row-level locking
concurrency protection
BookingHistory
audit API
structured logging
safe API error handling
Swagger / OpenAPI
pytest test suite
Docker
```
---