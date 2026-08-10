# MT-ISPMS Professional Upgrade — Final Deliverable

Per section 33's required format. This covers everything implemented in
this pass on top of the previous code-review fixes (see `CHANGELOG.md` for
that earlier round - multi-tenant ID collisions, CSRF, the user-creation
bug, etc.).

---

## 1. Exact Files Modified

- `config.py` — `UPLOAD_FOLDER` now always resolves to an absolute path
- `app/__init__.py` — registered `exams_bp`; added 413 handler
- `app/models/school.py` — added `logo_url` property, branding fields
- `app/models/payment_type.py` — added `allow_custom_amount`
- `app/models/student_application.py` — added health/declaration fields
- `app/models/attendance.py` — added `EXCUSED` status
- `app/utils/helpers.py` — removed dead `save_upload`/`allowed_file` (superseded)
- `app/services/export_service.py` — rewritten to use shared branding; added report/receipt `school` param
- `app/auth/forms.py` — added `ProfileForm`
- `app/auth/routes.py` — added `/profile`, `/profile/remove-photo`
- `app/admin/forms.py` — added `BrandingForm`, `PaymentTypeForm.allow_custom_amount`
- `app/admin/routes.py` — added branding routes; wired `allow_custom_amount`
- `app/students/routes.py` — fixed photo-upload error handling; **restricted create/edit/deactivate/upload to Super Admin & School Admin only** (Collectors could previously do all of these); rebuilt Students Owing with search/filters
- `app/classes/routes.py` — **restricted create/edit/assign-students to Super Admin & School Admin only** (Collectors could previously do all of these)
- `app/expenses/routes.py` — fixed receipt-upload error handling; **added missing role restriction on the expense list itself** (any logged-in user, including Collectors, could previously view `/expenses/`)
- `app/reports/routes.py` — **added role restrictions to all 7 report routes** (any logged-in user, including Collectors/Teachers, could previously view financial reports by URL)
- `app/payments/routes.py` — added quick-amount data + server-side amount-lock enforcement
- `app/dashboard/routes.py` — **split into three role-specific dashboards** (financial/collector/teacher) so financial totals are never computed or rendered for Collector/Teacher roles
- `app/templates/shared/sidebar.html` — added Exams, Branding nav links
- `app/templates/shared/topbar.html` — added My Profile link
- `app/templates/payments/form.html`, `app/templates/expenses/form.html`, `app/templates/students/owing.html`, `app/templates/attendance/take.html` — UI additions (quick amounts, balance banner, search/filters, bulk mark-present)
- `seed.py` — extended with a second full school, payment-type defaults matching spec, subjects/grading/sample exam data

## 2. New Files Created

**Architecture:**
- `app/services/storage_service.py` — pluggable upload storage (local today, S3/Cloudinary-ready)
- `app/services/document_branding.py` — shared PDF header/footer/signature-block engine
- `app/services/results_service.py` — exam ranking with correct tie handling
- `app/utils/db_safety.py` *(from prior pass, still in use)*

**Models:**
- `app/models/exam.py` — `Subject`, `GradingScaleBand`, `Exam`, `ExamSubject`, `Result`

**Blueprint (Exams & Results):**
- `app/exams/__init__.py`, `app/exams/forms.py`, `app/exams/routes.py`
- Templates: `app/templates/exams/{subjects,subject_form,grading,grading_form,list,exam_form,view,enter_marks}.html`

**Profile management:**
- `app/templates/auth/profile.html`

**Branding:**
- `app/templates/admin/branding.html`
- `app/static/fonts/README.md` (instructions for enabling bilingual PDFs)

**Dashboards:**
- `app/templates/dashboard/collector.html`, `app/templates/dashboard/teacher.html`

**Docs:**
- This file (`FINAL_DELIVERABLE.md`)

## 3. Database Models Changed

| Model | Change |
|---|---|
| `School` | + `motto`, `website`, `document_header_text`, `document_footer_text`; + `logo_url` property |
| `SchoolPaymentType` | + `allow_custom_amount` (bool, default True) |
| `StudentApplication` | + `has_medical_condition`, `medical_condition_details`, `declaration_accepted` |
| `Attendance` | `AttendanceStatus` + `EXCUSED` |
| **New:** `Subject` | school-scoped, unique per school |
| **New:** `GradingScaleBand` | school-scoped configurable grading (A/B/C/D/F by default, fully editable) |
| **New:** `Exam` | belongs to a class; `is_published` flag |
| **New:** `ExamSubject` | join of Exam↔Subject with per-exam `max_marks` |
| **New:** `Result` | one student's marks for one exam subject; unique per (exam_subject, student) |

## 4. Migration Commands Required

```bash
flask db migrate -m "Branding, custom payment types, application health fields, exams and results"
flask db upgrade
```

All changes in this pass are additive (new tables, new nullable columns) —
no destructive migration, no data loss. See `MIGRATION_GUIDE.md` for the
one constraint-drop step still needed if you haven't yet applied the
*previous* pass's student/payment/expense uniqueness fix to an existing
production database.

## 5. Environment Variables Required

None are newly *required*. One is newly *relevant*:

| Variable | Purpose |
|---|---|
| `STORAGE_BACKEND` | Optional, defaults to `local`. Set this when a real object-storage backend (S3/Cloudinary) is implemented later — see `app/services/storage_service.py`'s `StorageBackend` interface. |

## 6. New Dependencies Added

None. Everything in this pass uses packages already in `requirements.txt`
(Pillow for image validation, ReportLab for PDFs). **Optional, not
required:** `arabic-reshaper` and `python-bidi` if/when full RTL Arabic
text shaping is added to the admission form (see
`app/static/fonts/README.md`).

## 7. Routes Added/Changed

**Added:**
- `/auth/profile`, `/auth/profile/remove-photo`
- `/admin/branding`, `/admin/branding/remove-logo`
- `/exams/*` (12 routes: subjects, grading scale, exam CRUD, marks entry, publish, student report PDF, class result sheet PDF)
- `/payments/collect` *(from prior pass, now enhanced with quick amounts)*

**Changed (access control tightened — see section 9):**
- `/students/create`, `/students/<id>/edit`, `/students/<id>/deactivate`, `/students/upload`
- `/classes/create`, `/classes/<id>/edit`, `/classes/<id>/assign-students`
- `/expenses/` (list)
- `/reports/*` (all 7 routes)

## 8. Permission Changes

This is the most important section — several real authorization gaps were
found and closed, matching the "never rely on hiding buttons" instruction:

| Gap Found | Who Was Affected | Fix |
|---|---|---|
| Collectors could create/edit/deactivate/bulk-upload students | Collector | Restricted to Super Admin/School Admin |
| Collectors could create/edit classes, assign students to classes | Collector | Restricted to Super Admin/School Admin |
| Any logged-in user (incl. Collector) could view `/expenses/` directly | Collector, Teacher | Restricted to Super Admin/School Admin/Accountant |
| Any logged-in user (incl. Collector/Teacher) could view every financial report by URL, even though the sidebar hid the link | Collector, Teacher | All 7 report routes now require Super Admin/School Admin/Accountant (student-history additionally allows Collector, since they legitimately need to check one student's payment history while collecting) |
| Dashboard computed AND rendered total revenue, current balance, and expenses for every role | Collector, Teacher | Dashboard now branches by role at the route level - Collector/Teacher dashboards never compute these figures at all, not just hide them in the template |
| Payment type amount locks (`allow_custom_amount=False`) were only enforceable client-side | Collector | Server-side enforcement added in `create_payment` |

Every fix above was verified by re-reading the actual route decorators
after the change (not just the sidebar/template visibility), consistent
with the instruction that authorization must be enforced server-side.

## 9. Security Improvements

- Fixed the student-photo-upload 500 (root cause: unresolved relative
  `UPLOAD_FOLDER` path + zero error handling around file I/O)
- New pluggable storage service validates uploads are genuine images
  (Pillow content verification, not just extension-matching) before ever
  writing them to disk
- Old files are now cleaned up on replace/delete (student photos, school
  logos, profile photos, expense receipts) instead of accumulating forever
- 413 (payload-too-large) now shows a friendly flash message instead of a
  raw Werkzeug error page
- Six real IDOR/authorization gaps closed (section 8 above)
- Profile email edits are validated for uniqueness before hitting the DB

## 10. Testing Performed

**Static verification (this sandbox has no internet access to install the
full Flask stack, so nothing was run live — see the note in section 11):**
- Full Python compile sweep (`python -m py_compile`) on all 71 `.py` files after every change — zero errors
- Full Jinja2 parse sweep on all 62 templates — zero errors
- Automated cross-check that every `url_for()` call in every template resolves to an actually-registered route — zero missing endpoints
- Manual line-by-line audit of every route's decorators against the section 5/6/10-12 role matrix (this is how the six permission gaps in section 8 were found and fixed)

**Not performed (couldn't be, in this environment) — you should run before
deploying:**
- `pytest` (the existing suite from the prior pass plus any new tests you add for the exam/results system)
- Live manual walkthrough of the testing checklist in section 29 of your original prompt (login as each role, upload a photo, generate each PDF, etc.)

## 11. Known Limitations

- **Bilingual/Arabic PDF labels degrade gracefully rather than being fully implemented.** No Arabic-capable font file is available in this offline sandbox, so Arabic text is omitted from the admission form rather than risk rendering as broken glyphs. Drop a Unicode Arabic TTF into `app/static/fonts/` (see the README there) to enable it — no code changes needed. Full right-to-left shaping additionally needs `arabic-reshaper` + `python-bidi`, not yet wired in.
- **Local file storage is not Render-persistent.** The `StorageBackend` abstraction is ready for S3/Cloudinary, but no cloud backend is actually implemented yet — uploaded photos/logos/receipts will be lost on Render redeploys until one is added.
- **Broadcast notification read-state is coarse.** A school-wide notification (`user_id=NULL`) is one row; marking it read affects all viewers, not per-user (flagged previously, still true).
- **Exam system covers the specified scope but not every edge case.** E.g. no "exam attempt not yet started" state, no partial-credit rounding configuration beyond 2 decimal places, no subject-level pass/fail thresholds separate from the overall grade.
- **No automated test suite was added for the exam/results or branding features in this pass** — the prior pass's `pytest` suite still covers auth/multi-tenancy/expense-balance; extending it to the new modules is recommended before production use.
- **Nothing in this pass was executed against a live database** (sandbox has no network access to install Flask/SQLAlchemy/etc.) — verification was static (compilation, template parsing, route cross-referencing, manual decorator audit) rather than runtime. Please run the manual testing checklist yourself before deploying.

## 12. Deployment Instructions for Render

Same as the standard flow (see `README.md` §5 and `CHANGELOG.md` §5),
with the migration from section 4 above:

```bash
git pull
pip install -r requirements.txt
flask db migrate -m "Branding, custom payment types, application health fields, exams and results"
flask db upgrade
flask run   # or gunicorn wsgi:app in production
```

`render.yaml`'s existing `preDeployCommand: "flask db upgrade"` picks up
the new migration automatically on the next Render deploy - no config
changes needed there.

## 13. Recommended Future Improvements

1. **Implement a real cloud storage backend** (S3 or Cloudinary) using the `StorageBackend` interface in `app/services/storage_service.py` before relying on uploaded files surviving Render redeploys in production.
2. **Add the Arabic font + reshaping libraries** for genuinely bilingual, RTL-correct admission forms (see limitation above).
3. **Per-user notification read-state** via a join table, once notification volume justifies it.
4. **Automated tests for the exam/results system** — ranking edge cases (all-tied class, single student, zero results) are exactly the kind of thing worth locking down with tests before this is trusted for real report cards.
5. **Exam edit/delete routes** — currently exams can be created and have marks entered/published, but there's no "edit exam name/date" or "delete exam" route yet; add these with the same teacher-ownership + tenant checks used elsewhere.
6. **Bulk marks import via Excel** for exam results, mirroring the existing student bulk-upload pattern — useful once a school has many subjects/classes.
7. **Mobile-first pass on the exam marks-entry and attendance grids specifically** — these are the most likely screens to be used from a phone in a classroom, and the current tables, while responsive, could use larger touch targets.
8. A full security review by someone able to run the application live (penetration-style testing of the fixed IDOR issues, CSRF on every new form, session fixation, etc.) since everything here was verified statically, not by exercising the running app.
