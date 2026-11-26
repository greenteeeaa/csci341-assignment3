# CSCI 341 Assignment 3 — Executive Summary
**Research Conference and Paper Review Management System** · Fall 2026

| Member | Student ID | Contributions |
|---|---|---|
| [Full name 1] | [ID] | [e.g. relational schema, constraints, seed data, pg_dump export] |
| [Full name 2] | [ID] | [e.g. Part 2 SQLAlchemy program and query verification] |
| [Full name 3] | [ID] | [e.g. Flask application, deployment, video] |

**Links:** video and application URLs are in `links.txt` (no login is required).

## Completed work
* **Part 1 — Relational database and sample data.** PostgreSQL schema with 15 tables and 61 named constraints
  (primary keys, foreign keys with documented ON DELETE actions, NOT NULL, UNIQUE, CHECK) plus a partial unique
  index (one corresponding author) and composite foreign keys (coordinators and chairs belong to the conference's
  reviewer pool). Multivalued labels are stored in separate relations. Seed data: 15 users, 12 papers in all five
  statuses, 17 versions, 20 completed reviews, 3 conferences (two in Astana, one in Almaty), covering every
  required case (empty tracks, a conference without papers, a reviewer without reviews, scheduled and unscheduled
  accepted papers, Amina Aminova's withdrawn papers, empty Astana sessions). All Assignment 1 business rules hold
  in the data. Repeatable creation through `init_db.py`, the SQL scripts or `database_dump.sql`.
* **Part 2 — SQL through Python and SQLAlchemy.** `part2_queries.py` creates the tables and inserts the data, then
  runs tasks 3.1–8 with `text()` and bound parameters, printing each SQL statement, its parameters and result.
  Updates and deletions show before/after results inside a transaction that is rolled back, and the program
  verifies that the seed data is restored. The view `accepted_paper_schedule` is created and queried. All results
  were cross-checked with independently written SQL.
* **Part 3 — Deployed web application.** Flask + SQLAlchemy Core with full CRUD for users (author and reviewer
  profiles), papers (authorship, keywords, versions), reviews and sessions (paper assignment); read-only pages for
  conferences, tracks and pools and for the schedule view. Every change runs in one transaction and failures are
  reported clearly. Both required application checks — no self-reviews and valid session assignments — are
  enforced wherever they apply (review save/edit, authorship change, assignment, status/track change, session
  conference change). Deployed with persistent PostgreSQL storage.

## Incomplete or non-working requirements
None. [Update this line if anything changes before submission.]
