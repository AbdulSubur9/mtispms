# MT-ISPMS — Code Review & Enhancement Summary

This document covers everything changed in this pass: bug root causes,
new features, migrations, environment variables, a testing checklist,
deployment steps, and recommendations for scaling to hundreds of schools.

---

## 1. Summary of Changes

### 1.1 Root-cause fixes

| Bug | Root Cause | Fix |
|---|---|---|
| "Internal Server Error" creating students/payments/expenses for a **second** school | `student_id` / `receipt_number` / `reference_number` were declared **globally unique** columns, but generated with **per-school counters** — the second school's first `STU-0001` collided with the first school's | Changed to **composite unique constraints** on `(school_id, code)`; generators now scan existing rows for that school rather than trusting "last inserted row" |
| Generic 500 page on any database conflict (e.g. duplicate username) | No commit ever had error handling — any `IntegrityError`/`SQLAlchemyError` bubbled straight to Flask's default handler | Added `safe_commit()` helper: rolls back, logs the real exception server-side, flashes a friendly, specific message. Wired into every create/update/delete route |
| New School Admins sometimes ended up "broken" (couldn't do anything) | A Super Admin could create a School Admin while the school dropdown was still on its default "0 / none" option, silently producing `school_id = NULL` | `UserForm.validate_school_id()` now rejects a non-super-admin role with no school selected; School Admins can no longer even see other schools in the dropdown when creating their own staff (locked to a single, non-tamperable option) |
| Delete buttons failing with "CSRF token missing" | 4 templates (`students/view.html`, `classes/view.html`, `expenses/list.html`, `admin/users_list.html`) had raw `<form method="POST">` with **no CSRF token at all** | Added `{{ csrf_field() }}` (new macro) to every affected form; added `delete_button()`/`action_button()` macros so this can't regress |
| Bulk Excel student import could silently drop rows after the first bad row | On PostgreSQL, one failed `INSERT` aborts the whole transaction until rolled back — every subsequent `flush()` in the same loop would then also fail | Each row now runs inside its own `db.session.begin_nested()` savepoint |
| A user from School A could view School B's student payment history by editing the URL | `reports.student_payment_history` had **no tenant-ownership check at all** | Added the same `school_id` ownership guard every other detail view already uses |
| Super Admin's "combined view" leaked into single-school pages | Every list view resolved `school_id` independently via `request.args`, with no persistence — navigating to a page without `?school_id=` silently fell back to "all schools" | `current_school_id()` now uses a **sticky session value**: once a Super Admin picks a school (via the new topbar switcher or any `?school_id=` link), it stays selected across the whole app until changed back to "All Schools" |
| No visibility into production errors | 500 handler didn't log anything | Added rotating file logging (`instance/logs/mtispms.log`) plus `exc_info` on every unhandled exception |

### 1.2 New features

- **Students Owing + WhatsApp reminders** (`/students/owing`) — lists active students below an expected contribution, with one-click `wa.me` deep links pre-filled with a reminder message. Message-building is isolated in the route so swapping in a real SMS provider (Twilio/Hubtel/Africa's Talking) later only touches one function.
- **AJAX payment collection search** (`/payments/collect`, `/students/api/search`) — live search by student ID, name, guardian name, guardian phone, or class; selecting a result jumps straight into the payment form with balance/history visible.
- **Custom Payment Types** (`SchoolPaymentType` model, `/admin/payment-types`) — each school defines its own structures (name, frequency, default amount); available as an optional field on the payment form alongside the built-in categories (kept for backward compatibility).
- **Teacher Portal + Attendance** — teachers now only ever see classes assigned to them (server-side enforced, not just hidden in the UI); new `Attendance` model and `/attendance` blueprint for taking daily attendance and viewing daily/weekly/monthly reports.
- **Student Application Form** (`StudentApplication` model, `/applications`) — online admission form, printable/downloadable branded PDF (ReportLab), and one-click "Approve & Admit" that creates the actual `Student` record.
- **Super Admin school switching** — a topbar dropdown (Super Admin only) that persists the selected school across every page (students, payments, expenses, reports, users, audit log) until switched back to "All Schools."
- **Expense balance control** — before saving, `amount` is checked against `Total payments collected − Previous expenses`; over-budget submissions are rejected with the exact "Insufficient funds. Available balance is GH₵X." message, both on create and edit (edit excludes the expense's own current amount from the baseline so raising/lowering it is judged fairly).
- **Notification Center** (`/notifications`) — read/unread state, mark-one-read, mark-all-read; badge counter in the sidebar and topbar.
- **User delete** — was missing entirely before (only toggle-active existed); added with self-deletion and cross-tenant guards, and a friendly message if the user can't be deleted due to linked records.

### 1.3 Security / code-quality hardening

- Field-level uniqueness validation on username/email (was previously only caught, ungracefully, at the database layer).
- School Admin's `school_id` is now **never** client-editable via any form — always forced server-side from `current_user.school_id`.
- Collectors' payment list is now correctly scoped to *their own* collected payments, not their whole school's.
- All new/updated delete and toggle actions require POST + CSRF + role check + tenant-ownership check, in that consistent order.
- Rotating file logging added for production diagnosability.

---

## 2. Database Migrations Required

See **`MIGRATION_GUIDE.md`** for full detail. Short version:

```bash
flask db migrate -m "Multi-tenant fixes, payment types, attendance, applications"
flask db upgrade
```

New tables: `school_payment_types`, `attendance`, `student_applications`.
Changed constraints: `students.student_id`, `payments.receipt_number`,
`expenses.reference_number` go from globally-unique to
composite-unique-per-school. **If you have existing production data**,
read the "already have production data" section of `MIGRATION_GUIDE.md`
before applying — Alembic needs to drop the old constraint by name first.

---

## 3. New Environment Variables

None are strictly required beyond what already existed in `.env.example`.
Two are newly *relevant*:

| Variable | Why it now matters |
|---|---|
| `SECRET_KEY` | Now also signs the session-stored "active school" selection for Super Admins — make sure it's a real secret in production, not the dev default. |
| (none added) | The WhatsApp reminder feature uses `wa.me` links client-side and needs **no API key or environment variable**. If you later add real SMS (Twilio/Hubtel/etc.), that provider's credentials would go here. |

---

## 4. Testing Checklist

Automated (`pytest`, see `tests/test_security_fixes.py` and updated
`tests/test_models.py`):

- [x] Two different schools can each independently create student `#0001`, receipt `#0001`, and expense reference `#0001` without an `IntegrityError` (the core regression test for the main bug).
- [x] Duplicate username/email shows a friendly validation message, not a 500.
- [x] A School Admin creating a staff user always gets scoped to their own school, even without explicit input.
- [x] Expense creation is blocked when it exceeds available balance, and allowed when within it.
- [x] Cross-tenant access to another school's student payment history returns 403.
- [x] Existing auth/model/integration tests still pass unmodified.

Manual checklist before shipping:

- [ ] Log in as `admin` (Super Admin) → switch between schools via the topbar dropdown → confirm Students/Payments/Expenses/Reports/Users all filter to just that school, and "All Schools" shows the combined view again.
- [ ] Log in as a School Admin → try to delete a class/expense/user/student → confirm the confirmation dialog appears and the delete actually succeeds (previously failed with "CSRF token missing").
- [ ] Create a **second** school as Super Admin, create its own School Admin, log in as that admin, add a student and record a payment — confirm no 500 error (this is the exact bug scenario).
- [ ] As a Collector, open "Search & Collect", type a partial name, confirm live results appear, select one, and confirm the payment form pre-fills that student.
- [ ] As a School Admin, go to Settings → Payment Types, add a custom type (e.g. "Saturday Payment"), then confirm it appears as an option when recording a payment.
- [ ] Log in as a Teacher — confirm the sidebar shows only "My Classes" and "Attendance," with no Payments/Expenses/Reports/Admin links, and that navigating directly to a payments URL returns 403.
- [ ] Take attendance for a class as that class's teacher; confirm a different teacher cannot take attendance for it (403).
- [ ] Submit a Student Application, download its PDF, click "Approve & Admit," confirm a new Student record appears with an auto-generated ID.
- [ ] Try to record an expense larger than the available balance — confirm it's blocked with the exact insufficient-funds message; try one within balance — confirm it saves.
- [ ] Trigger a notification (e.g. record a payment) and confirm it shows up in the Notification Center as unread, then mark it read.
- [ ] Check `instance/logs/mtispms.log` after intentionally triggering an error (e.g. a duplicate) — confirm the real exception and traceback are recorded there.

---

## 5. Deployment Instructions

Same as before (see `README.md` §5), with one addition: run the migration
before `flask seed` on any environment upgrading from the prior schema.

```bash
git pull
pip install -r requirements.txt
flask db migrate -m "Multi-tenant fixes, payment types, attendance, applications"
flask db upgrade
# optional, dev/staging only - reseeds demo data (safe to skip in prod):
# flask seed
flask run   # or gunicorn wsgi:app in production
```

On Render specifically, the `preDeployCommand: "flask db upgrade"` already
configured in `render.yaml` will pick up the new migration automatically on
the next deploy — no extra Render configuration needed.

---

## 6. Remaining Recommendations for Scaling to Hundreds of Schools

These are things I'd flag for a future pass rather than fix in this one,
roughly in priority order:

1. **Per-user read tracking for broadcast notifications.** Right now a
   school-wide notification (`user_id = NULL`) is a single row; marking it
   "read" marks it read for the whole school, not just the user who clicked
   it. At real scale this needs a join table (`notification_reads`:
   `notification_id`, `user_id`, `read_at`).
2. **Background jobs for exports and bulk imports.** Excel/PDF generation
   and large bulk-uploads currently run synchronously in the request. Fine
   at today's scale; at hundreds of schools, move these to a task queue
   (Celery + Redis, or RQ) so a large export doesn't tie up a web worker.
3. **Rate limiting on the AJAX search and API endpoints** — `/students/api/search`
   and `/api/v1/*` have no rate limiting yet; add Flask-Limiter before
   opening the API to third parties.
4. **Database indexing pass once real data volumes exist.** The composite
   unique constraints added here also serve as indexes for the common
   `WHERE school_id = ? AND student_id = ?` pattern, but a full index review
   (e.g. `payments.payment_date`, `expenses.expense_date` for report date-range
   queries) is worth doing once you have production-scale row counts.
5. **Move file uploads off local disk.** `UPLOAD_FOLDER` writes to the app
   server's local filesystem, which doesn't survive Render's ephemeral
   filesystem across deploys/restarts and doesn't scale past one instance.
   Move to S3-compatible object storage (e.g. Cloudflare R2, AWS S3) before
   running more than one web dyno/instance.
6. **SMS fallback for reminders.** The WhatsApp `wa.me` approach requires
   the guardian to have WhatsApp and requires a human to click "Send" —
   fine for a v1, but at scale you'll want an automated SMS/WhatsApp
   Business API integration that can send in bulk without per-message
   manual clicks. The reminder-message-building code is already isolated
   in `students.students_owing` specifically so this swap is contained.
7. **Formal API authentication.** `/api/v1/*` currently relies on the same
   session cookie as the web app. If external systems (e.g. a future mobile
   app) need to integrate, add token-based auth (e.g. Flask-JWT-Extended)
   rather than session cookies.
8. **Audit log retention/archival policy.** `audit_logs` grows forever;
   at hundreds of schools over years this table will get large. Consider a
   periodic archive-to-cold-storage job once row counts justify it.
9. **Automated Super-Admin-created-School-Admin welcome email** with a
   password-reset link instead of a plaintext password typed by the Super
   Admin — reduces credential-sharing risk during onboarding.
