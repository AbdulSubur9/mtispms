# MT-ISPMS — Madrassa Integrated Student Payment Management System

A production-ready, multi-tenant web application for managing student payments,
expenses, and accountability reporting across one or many Madrassas.

Built with **Python 3.13, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login,
Flask-WTF, Flask-Mail**, Bootstrap 5, Jinja2, and Chart.js. Deployable on **Render**
with PostgreSQL in production and SQLite for local development.

---

## 1. Features

- **Multi-school (multi-tenant) architecture** — a Super Admin manages every
  Madrassa; School Admins are scoped to their own school only.
- **Role-based access control** — Super Admin, School Admin, Accountant,
  Collector, Teacher (read-only).
- **Authentication** — secure login/logout, password hashing, forgot/reset
  password via email, change password, session management.
- **Dashboard** — total students, today's/monthly collections, total expenses,
  current balance, outstanding fees, students paid vs owing, payment & expense
  trend charts (Chart.js), expense category pie chart.
- **Student management** — create/edit/delete/deactivate, auto-generated
  Student IDs (`STU-0001`), bulk import via Excel, export to Excel, photo
  upload.
- **Class management** — create classes, assign students & teachers.
- **Payment management** — weekly, monthly, building fund, PTA levy, special
  donations; auto-generated unique receipt numbers; printable PDF receipts;
  admin-only void with audit trail.
- **Expense management** (compulsory module) — categorized expenses (salary,
  stationery, electricity, water, maintenance, transportation, building
  project, food, others), receipt uploads, automatic balance recalculation
  (`Current Balance = Total Income − Total Expenses`).
- **Reports** — daily/weekly/monthly/yearly/custom income & expense reports,
  profit/loss, collector performance, student payment history, outstanding
  payments; export to **PDF, Excel, CSV**.
- **Notifications** — payment success, expense alerts, outstanding fees.
- **Global search** — across students, guardians, receipts, expenses,
  collectors, classes.
- **Audit log** — every login, logout, payment, expense, and user action is
  recorded.
- **Security** — CSRF protection, hashed passwords, role-based authorization,
  secure sessions, server-side input validation, parameterized ORM queries
  (SQL-injection safe), Jinja2 autoescaping (XSS safe).
- **REST API** — JSON endpoints for students, payments, expenses, dashboard
  summary, and authentication.

---

## 2. Project Structure

```
mtispms/
├── app/
│   ├── auth/              # login, logout, password reset, change password
│   ├── admin/             # schools, users, audit log (Super Admin / School Admin)
│   ├── students/          # student CRUD, Excel import/export
│   ├── classes/           # class CRUD, student assignment
│   ├── payments/          # payment CRUD, receipts, void
│   ├── expenses/          # expense CRUD
│   ├── reports/           # accountability & financial reports, exports
│   ├── dashboard/         # KPI dashboard
│   ├── search/            # global search
│   ├── api/               # REST API (JSON)
│   ├── models/            # SQLAlchemy models (one file per entity)
│   ├── services/          # stats_service.py, export_service.py (PDF/Excel/CSV)
│   ├── utils/             # decorators (RBAC), helpers (uploads, scoping)
│   ├── templates/         # Jinja2 templates, one folder per blueprint
│   ├── static/            # css/js/uploads
│   └── extensions.py      # db, migrate, login_manager, csrf, mail
├── tests/                 # pytest unit + integration tests
├── migrations/            # Flask-Migrate migration scripts (generated)
├── config.py              # Dev/Prod/Testing configuration
├── wsgi.py                # application entrypoint (gunicorn target)
├── seed.py                # demo data seed script
├── requirements.txt
├── Procfile                # Render/Heroku-style process file
├── render.yaml             # one-click Render Blueprint deployment
└── .env.example
```

---

## 3. Local Installation

### Prerequisites
- Python 3.11+ (3.13 recommended)
- pip / venv

### Steps

```bash
git clone <your-repo-url> mtispms
cd mtispms

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # then edit .env with your own SECRET_KEY, mail creds, etc.

# Initialize the database (SQLite by default in development)
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Seed demo data (creates a Super Admin, School Admin, Accountant,
# 2 Collectors, a Teacher, sample students, payments and expenses)
flask seed
# or: python seed.py

flask run
```

Visit **http://127.0.0.1:5000**.

### Default Login (Super Admin)

| Field    | Value    |
|----------|----------|
| Username | `admin`  |
| Password | `admin123` |

Other seeded accounts (see `seed.py` output for full list):
`schooladmin / Admin@123`, `accountant / Account@123`,
`collector1` & `collector2 / Collect@123`, `teacher1 / Teach@123`.

**Change these passwords immediately in any real deployment.**

---

## 4. Running Tests

```bash
pytest
```

Tests cover authentication flows, model logic (ID/receipt generation, balance
calculation, void-payment exclusion), and role-based access integration tests.
Testing uses an in-memory SQLite database and disables CSRF for form posts.

---

## 5. Deployment Guide (Render)

### Option A — Blueprint (recommended)
1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and point it at your repo. Render
   will read `render.yaml` and provision a **web service** + **PostgreSQL
   database** automatically.
3. Fill in `MAIL_USERNAME` / `MAIL_PASSWORD` / `MAIL_DEFAULT_SENDER` in the
   Render dashboard (marked `sync: false` so they aren't stored in the repo).
4. Render runs `pip install -r requirements.txt`, then `flask db upgrade`
   (via `preDeployCommand`), then starts Gunicorn.
5. Once live, SSH/Shell into the service (or use a one-off job) and run:
   ```bash
   flask seed
   ```
   to load demo data, or create your first Super Admin manually via the
   Flask shell.

### Option B — Manual Web Service
1. Create a **PostgreSQL** instance on Render; copy its connection string.
2. Create a **Web Service** from your repo:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
3. Add environment variables from `.env.example` (`SECRET_KEY`,
   `DATABASE_URL`, `FLASK_ENV=production`, mail settings).
4. After first deploy, open a shell and run `flask db upgrade` then
   `flask seed` (optional).

---

## 6. Database Diagram (entity overview)

```
School 1───* User
School 1───* ClassRoom 1───* Student
School 1───* Student 1───* Payment *───1 User (collector)
School 1───* Expense *───1 User (recorded_by)
Payment 1───1 Receipt
School 1───* AuditLog *───1 User
School 1───* Notification *───1 User (optional; null = school-wide broadcast)
```

Key constraints:
- `Student.student_id`, `Payment.receipt_number`, `Expense.reference_number`
  are unique and auto-generated per school (`STU-0001`, `RCT-26-00001`,
  `EXP-26-00001`).
- `Payment.is_void` soft-deletes a payment for audit purposes while excluding
  it from all income/balance calculations.

---

## 7. API Documentation (summary)

All endpoints are under `/api/v1` and require an authenticated session
(`POST /api/v1/auth/login` with `{"username": "...", "password": "..."}`
returns a session cookie).

| Method | Endpoint                       | Description                        |
|--------|---------------------------------|-------------------------------------|
| POST   | `/api/v1/auth/login`            | Log in, returns user summary        |
| POST   | `/api/v1/auth/logout`           | Log out                             |
| GET    | `/api/v1/students`               | Paginated list of students (scoped) |
| GET    | `/api/v1/students/<id>`          | Single student                      |
| GET    | `/api/v1/payments`               | Paginated list of payments          |
| GET    | `/api/v1/payments/<id>`          | Single payment                      |
| GET    | `/api/v1/expenses`                | Paginated list of expenses          |
| GET    | `/api/v1/dashboard/summary`       | KPI summary (students, income, balance) |
| GET    | `/api/v1/reports/income`          | Income total for a date range       |

All list endpoints accept `?page=` and `?per_page=` query parameters.

---

## 8. Roles & Permissions Summary

| Role          | Students | Classes | Payments | Expenses | Reports | Users/Schools |
|---------------|----------|---------|----------|----------|---------|---------------|
| Super Admin   | Full (all schools) | Full | Full + void | Full | Full | Full |
| School Admin  | Full (own school)  | Full | Full + void | Full | Full | Users only |
| Accountant    | View     | View    | View     | Full     | Full    | —             |
| Collector     | View     | View    | Create + view own | — | View | —             |
| Teacher       | View     | View    | View     | —        | View    | —             |

---

## 9. Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2).
- All forms are protected by Flask-WTF CSRF tokens.
- All database access goes through SQLAlchemy's ORM (parameterized queries).
- File uploads are restricted by extension and renamed with UUIDs to prevent
  path traversal / overwrite attacks.
- Session cookies are `HttpOnly` and `SameSite=Lax`; `Secure` is enabled in
  production config.
- Change `SECRET_KEY` and every seeded password before going live.

---

## 10. License

This project was generated for internal / educational use. Adapt the license
of your choice before distributing.
