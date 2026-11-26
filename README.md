# CSCI 341 Assignment 3 — Research Conference and Paper Review Management System

PostgreSQL database + Python/SQLAlchemy query program (Part 2) + Flask web application (Part 3).

| Item | Location |
|---|---|
| Schema (DDL) | `sql/schema.sql` |
| Seed data | `sql/seed.sql` |
| View (task 8) | `sql/view.sql` |
| pg_dump export (schema + seed data + view) | `database_dump.sql` |
| Part 2 program | `part2_queries.py` (writes its output to `part2_output.txt`) |
| Web application | `app.py`, `templates/` |
| Shared DB helpers / (re)initialisation | `db.py`, `init_db.py` |
| Dependencies / deployment | `requirements.txt`, `render.yaml`, `Procfile` |
| Links (video, application) | `links.txt` |
| Executive summary | `EXECUTIVE_SUMMARY.md` |

---

## 1. Software versions

| Software | Version |
|---|---|
| PostgreSQL | 16 (any version ≥ 13 works; the dump was produced with pg_dump 16.15) |
| Python | 3.10 or newer (3.12 is used on the hosting platform) |
| SQLAlchemy | 2.0.x (`SQLAlchemy>=2.0.30,<2.1`) — the exact version is printed at the top of `part2_output.txt` |
| psycopg2-binary | 2.9.x (PostgreSQL driver used by SQLAlchemy) |
| Flask | 3.x |
| gunicorn | 22/23 (production web server) |

## 2. Setup and database restoration

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

createdb conference_db               # or: psql -c "CREATE DATABASE conference_db"
export DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/conference_db
# Windows PowerShell:  $env:DATABASE_URL="postgresql+psycopg2://postgres:<password>@localhost:5432/conference_db"
```

`DATABASE_URL` is used by every script. URLs that start with `postgres://` or `postgresql://`
(as given by hosting providers) are accepted and converted automatically.

Any of the following creates the schema and restores the **initial dataset** (each one drops existing data first, except the dump, which needs an empty database):

| Method | Command |
|---|---|
| Python (recommended) | `python init_db.py` |
| Part 2 program (tasks 1 and 2) | `python part2_queries.py` |
| SQL scripts | `psql -d conference_db -1 -f sql/schema.sql -f sql/seed.sql -f sql/view.sql` |
| pg_dump export (empty database) | `psql -d conference_db -f database_dump.sql` |
| Web application | **Restore seed data** button on the home page |

The dump can be regenerated with `pg_dump --no-owner --no-privileges -d conference_db -f database_dump.sql`.

## 3. Running Part 2 (SQL operations through Python and SQLAlchemy)

```bash
python part2_queries.py              # prints everything and saves it to part2_output.txt
python part2_queries.py --echo       # additionally logs the SQL that SQLAlchemy sends to the driver
```

* **Task 1** executes `sql/schema.sql` through SQLAlchemy (`Connection.exec_driver_sql`) and then lists the
  created tables, all constraints (`pg_constraint`) and indexes. **Warning:** it drops and re-creates the tables.
* **Task 2** executes `sql/seed.sql` and prints the row count of every table.
* **Tasks 3–8** are numbered in the code (`task_3_1`, …) and in the output (`TASK 3.1`, …). Every statement is
  written with `sqlalchemy.text()` and **bound parameters**; the program prints the SQL, the parameter values and
  the result.
* **Updates and deletions (3.1, 3.2, 4.1, 4.2)** run inside a transaction: BEFORE query → statement (with
  `RETURNING` and the row count) → AFTER query → **ROLLBACK** → the program re-reads the data and confirms it is
  identical to the BEFORE state. Every task therefore runs against the original seed data.
* **Task 8** creates the view from `sql/view.sql` (committed — it is a schema object, not data) and queries it.
* All filtering, joining and aggregation happens in PostgreSQL; Python only prints results.

### Query parameter values

| Task | Parameters | Expected result on the seed data |
|---|---|---|
| 3.1 | `email = 'arman.armanov@example.com'`, `phone = '+77773414141'` | 1 row updated (user 1). User 15 is a namesake "Arman Armanov" with another e-mail and is **not** changed — this is why the e-mail is used. |
| 3.2 | `city = 'Astana'` (+7 days), otherwise +3 days | 3 rows: CADS 2026 (Astana) 2026-04-01 → 04-08, ISMLS 2026 (Almaty) 07-01 → 07-04, GDM 2027 (Astana) 2027-02-20 → 02-27 |
| 4.1 | `email = 'amina.aminova@example.com'`, `status = 'withdrawn'` | Papers 7 and 8 deleted with 4 authorship, 5 keyword, 3 version and 2 review rows. Paper 12 (withdrawn, Amina is a co-author but not corresponding) and paper 11 (Amina corresponding, but rejected) are kept. |
| 4.2 | `city = 'Astana'` | Sessions 3 (CADS 2026) and 6 (GDM 2027) deleted. Non-empty Astana sessions 1, 2 and the empty Almaty session 5 are kept. |
| 5.1 | `status = 'accepted'` | Papers 1, 2, 3, 4, 10 |
| 5.2 | `pattern = '%machine learning%'` with `ILIKE` | Papers 2 ("Machine Learning"), 3, 8 ("MACHINE LEARNING"), 10. Paper 4 ("machine-learned") does not match. |
| 5.3 | `paper_id = 2` | Versions 4, 2, 1 (version 3 never existed — gaps are allowed) |
| 5.4 | `conference_id = 1` (CADS 2026), `expertise = 'Databases'`, `min_years = 3` | Reviewers 1, 3, 8. Excluded: 4 (2 years), 7 (no Databases expertise), 6 and 11 (not in the CADS 2026 pool). |
| 6.1 | — | Tracks 3 and 6 report 0 / 0; track 1 counts Timur and Aigerim once although each wrote two papers in it (5 papers, 8 authors). |
| 6.2 | — | Reviewer 6 (Daniyar Omarov): 0 reviews, NULL average |
| 6.3 | — | CADS 2026: 9 papers, 4 accepted, 3.57; ISMLS 2026: 3, 1, 3.33; GDM 2027: 0, 0, NULL |
| 6.4 | — | Average = 20 reviews / 9 reviewers = 2.22 → reviewers 3 (5 reviews), 1, 4, 8 (3 reviews each) |
| 7 | — | CADS 2026: 4 / 1 → 80.00; ISMLS 2026: 1 / 1 → 50.00; GDM 2027: 0 / 0 → NULL |
| 8 | — | Papers 1, 2 (session 1), 3 (session 2), 10 (session 4). Accepted paper 4 has no session and is not in the view. |

Averages in 6.2–6.4 are rounded to two decimals for display; 6.4 compares against the unrounded average.

## 4. Running the web application (Part 3)

```bash
python init_db.py --if-empty         # creates + seeds the tables only if they do not exist yet
flask --app app run                  # http://127.0.0.1:5000
```

Production command (used on the hosting platform): `gunicorn app:app`.

**Deployment (free):** web service on Render, database on Neon (free PostgreSQL that does not expire).
1. Create a Neon project and copy its connection string (`postgresql://…?sslmode=require`).
2. Push this folder to a GitHub repository. On Render choose **New → Blueprint** (uses `render.yaml`) or
   **New → Web Service** with build command `pip install -r requirements.txt` and start command
   `python init_db.py --if-empty && gunicorn app:app --bind 0.0.0.0:$PORT`.
3. Set the environment variable `DATABASE_URL` to the Neon connection string (`SECRET_KEY` is generated).
4. The first start creates and seeds the database automatically. A free Render service sleeps after 15 minutes
   without traffic; the first request afterwards takes up to about a minute.

No login is needed (authentication is not required by the assignment).

### What the application does

| Area | Operations |
|---|---|
| **Users** | Create, view, edit, delete. The same form manages the **author profile** (ORCID, research-area labels) and the **reviewer profile** (years of experience, expertise labels, reviewer-pool memberships). Labels are entered one per line or comma-separated and stored as separate rows. |
| **Papers** | Create, view, edit, delete. The paper form manages **authorship** (author, position, exactly one corresponding author), **keywords**, status, track and session; creating a paper also stores its first **version**. Versions are added, edited and deleted on the paper page (the current version is the highest number). |
| **Reviews** | Create, view, edit, delete completed reviews. |
| **Sessions** | Create, view, edit, delete. The session page lists its papers and can **assign** or **unassign** papers. |
| Read-only | Conferences with host institutions, tracks, reviewer pools and sessions; the schedule page shows the view `accepted_paper_schedule`. |

Every change runs in **one transaction** (`engine.begin()`); if any check or SQL statement fails, the whole change is
rolled back and the page shows a red message explaining why (application messages, or a translated database
constraint message naming the violated constraint).

**Demonstrating the required checks with the seed data** (also listed on the home page):
* Self-review: add a review of paper 2 by Arman Armanov (author of paper 2) → rejected. Edit paper 1 and add Arman
  Armanov as an author (he reviewed paper 1) → rejected.
* Invalid session assignment: on session 1 (CADS 2026) assign paper 9 (submitted) → rejected; assign paper 10
  (accepted, ISMLS 2026) → rejected; assign paper 4 (accepted, CADS 2026) → accepted. Editing paper 1 (scheduled)
  to status *rejected*, or to a track of ISMLS 2026, is rejected; changing the conference of session 1 is rejected
  while it contains CADS papers.

## 5. Schema, keys and references

Primary keys are **bold**. `→` marks a foreign key and its `ON DELETE` action (default `NO ACTION` = reject).
All surrogate keys are `INTEGER GENERATED BY DEFAULT AS IDENTITY`.

| Table | Columns | Keys, references and constraints |
|---|---|---|
| `app_user` | **user_id**, given_name, surname, email, affiliation, country, phone_number | UNIQUE(email); CHECK e-mail contains `@`; CHECK phone format; names not blank; all NOT NULL |
| `author` | **author_id**, orcid (optional) | author_id → app_user(user_id) CASCADE; UNIQUE(orcid); CHECK ORCID format |
| `author_research_area` | **author_id, area_label** | author_id → author CASCADE |
| `reviewer` | **reviewer_id**, years_experience | reviewer_id → app_user(user_id) CASCADE; CHECK years_experience ≥ 0 |
| `reviewer_expertise` | **reviewer_id, area_label** | reviewer_id → reviewer CASCADE |
| `conference` | **conference_id**, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline | CHECK end_date ≥ start_date; CHECK review_deadline ≥ submission_deadline |
| `conference_host` | **conference_id, host_name** | conference_id → conference CASCADE |
| `conference_reviewer` (pool) | **conference_id, reviewer_id** | conference_id → conference CASCADE; reviewer_id → reviewer CASCADE |
| `track` | **track_id**, conference_id, name, description, research_area, coordinator_id | conference_id → conference CASCADE; coordinator_id → reviewer RESTRICT; (conference_id, coordinator_id) → conference_reviewer (coordinator must be in the pool); UNIQUE(conference_id, name) |
| `conference_session` | **session_id**, conference_id, title, session_date, start_time, end_time, room_label, chair_id | conference_id → conference CASCADE; chair_id → reviewer RESTRICT; (conference_id, chair_id) → conference_reviewer (chair must be in the pool); CHECK end_time > start_time |
| `paper` | **paper_id**, track_id, title, abstract, submission_date, status, session_id (optional) | track_id → track RESTRICT; session_id → conference_session SET NULL; CHECK status ∈ {submitted, under review, accepted, rejected, withdrawn}; CHECK session_id IS NULL OR status = 'accepted' |
| `paper_keyword` | **paper_id, keyword** | paper_id → paper CASCADE |
| `paper_author` | **paper_id, author_id**, author_position, is_corresponding | paper_id → paper CASCADE; author_id → author RESTRICT; UNIQUE(paper_id, author_position); CHECK author_position > 0; partial UNIQUE index on (paper_id) WHERE is_corresponding (at most one corresponding author) |
| `paper_version` (weak entity) | **paper_id, version_no**, file_location, uploaded_at, change_note (optional) | paper_id → paper **CASCADE**; CHECK version_no > 0 |
| `review` | **review_id**, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments (optional), review_submission_date | paper_id → paper CASCADE; reviewer_id → reviewer RESTRICT; UNIQUE(paper_id, reviewer_id); CHECK overall_score BETWEEN 1 AND 5 (INTEGER); CHECK recommendation ∈ {accept, reject} |
| `accepted_paper_schedule` | view | one row per accepted paper assigned to a session |

Secondary B-tree indexes exist on the foreign-key columns used by joins (`track.conference_id`,
`paper.track_id`, `paper.session_id`, `paper_author.author_id`, `review.reviewer_id`, …) and on `paper.status`.

**Deletion behaviour.** Deleting a paper cascades to its versions, keywords, authorship rows and reviews.
Deleting a user cascades to their author/reviewer profile, labels and pool memberships, but is **rejected** while the
user is still an author of a paper, has reviews, coordinates a track or chairs a session (the web app explains which).
Deleting a session sets `paper.session_id` to NULL. Deleting a conference removes its hosts, pool memberships,
tracks and sessions but never users or reviewers, and is rejected while any of its tracks has papers. Foreign keys
are never disabled.

## 6. Required checks

**Database constraints (Part 1):** all primary keys, foreign keys and NOT NULL constraints above; unique e-mails;
unique author positions per paper; at most one review per reviewer and paper; only completed reviews (all review
fields except confidential comments are NOT NULL); CHECK constraints for paper status, integer scores 1–5,
recommendation, positive author positions and version numbers, non-negative experience, conference dates and
session times; versions identified by (paper_id, version_no) with ON DELETE CASCADE; at most one session per paper
(`paper.session_id`).

**Application check 1 — no self-reviews** (`validate_review()` and `validate_paper()` in `app.py`): a review is
rejected if its reviewer is an author of the paper (checked when creating and when editing a review), and a change
of a paper's authors is rejected if a new author already reviewed that paper.

**Application check 2 — valid session assignments** (`session_assignment_errors()`, used by `validate_paper()`,
`session_assign()` and `validate_session()`): a scheduled paper must be *accepted*, and its track's conference must
equal the session's conference. Checked when a paper is assigned (paper form or session page), when a scheduled
paper's status or track changes, and when a session's conference changes. Invalid changes are **rejected**.
As a safety net, the CHECK constraint `ck_paper_session_requires_accepted` also enforces the status part in the
database.

## 7. Other business rules from Assignment 1

All of these hold in the seed data. "DB" = enforced by PostgreSQL, "App" = enforced by the web application,
"Seed" = satisfied by the seed data only (no web CRUD for those tables).

| Business rule | Enforcement |
|---|---|
| Every user is an author, a reviewer, or both | App (user form requires at least one role) |
| An author has one or more research-area labels | App |
| A reviewer has one or more expertise labels | App |
| A conference has one or more host institutions, tracks and pool reviewers | Seed |
| A track coordinator belongs to the pool of the track's conference | DB (composite FK) + App message |
| A session chair belongs to the pool of the session's conference | DB (composite FK) + App pre-check |
| Every paper has at least one keyword | App |
| Every paper has at least one author | App |
| Exactly one corresponding author per paper | DB (at most one, partial unique index) + App (exactly one) |
| Every paper has at least one version | App (paper is created with its first version; the last version cannot be deleted) |
| A session date lies within the conference dates | App (design assumption) |
| An author with papers / a reviewer with reviews, tracks or sessions cannot lose that role | DB (RESTRICT FKs) + App message |
| Removing a conference does not remove reviewers | DB (only pool rows cascade) |

## 8. Design assumptions and changes relative to Assignment 1

* The implementation follows the reference relational schema (Appendix A), which maps the Assignment 1 EER/UML
  design: APP_USER superclass with overlapping, total AUTHOR/REVIEWER subclasses (shared primary key); multivalued
  labels (research areas, expertise, keywords, host institutions) in separate relations; PAPER_VERSION as a weak
  entity identified by (paper_id, version_no); PAPER_AUTHOR and CONFERENCE_REVIEWER as M:N relations, PAPER_AUTHOR
  carrying position and corresponding flag; the optional paper–session relationship as the nullable
  `paper.session_id`.
* Additions: composite foreign keys for the coordinator/chair pool rules, a partial unique index for the
  corresponding author, CHECK `session_id IS NULL OR status = 'accepted'`, CHECK review_deadline ≥
  submission_deadline, format checks for e-mail, phone and ORCID, unique track names within a conference, and
  indexes on foreign keys.
* E-mails are stored in lower case by the application; deadlines and the review submission date are DATE values;
  `uploaded_at` is a TIMESTAMP; session times are TIME values.
* Acronyms include the year (e.g. "CADS 2026") because each conference row is one edition.
* Paper files are not uploaded; only their file location (path) is stored, as required.
* "City is Astana" is an exact comparison with the bound value `'Astana'`.
* Reviews of withdrawn or rejected papers are kept (reviews are historical records).
* Invalid session-related changes are rejected (not silently repaired); a session can be deleted, which unschedules
  its papers.

## 9. Testing performed

* Every required constraint was tested with a violating statement (duplicate e-mail, duplicate author position,
  second review, invalid status/score/recommendation, non-positive position/version, negative experience,
  invalid conference dates and session times, second corresponding author, scheduling a non-accepted paper,
  chair/coordinator outside the pool, RESTRICT deletions) — each was rejected by PostgreSQL.
* All business rules were verified on the seed data with SQL checks; Part 2 results were cross-checked with
  independently written SQL.
* The web application was tested end-to-end (create/read/update/delete for users, papers, versions, reviews and
  sessions; both required checks in every place they apply; rollback of rejected changes; seed restore).
* `database_dump.sql` was restored into an empty database and verified (61 constraints, view rows).
