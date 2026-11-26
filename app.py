"""CSCI 341 Assignment 3 - Part 3: web application (Flask + SQLAlchemy Core).

Full CRUD for users (with author/reviewer profiles), papers (with authorship,
keywords and versions), reviews and sessions. Conferences, tracks, reviewer
pools and host institutions come from the seed script and are read-only
(reviewer-pool membership can also be edited in the user form).

Required application checks (Part 1):
  1. No self-reviews       -> validate_review()   and validate_paper() (authorship change)
  2. Valid session plans   -> session_assignment_errors(), used by the paper form,
                              the session "assign paper" form and the session form
Every change runs in one transaction (engine.begin()); failures are rolled back
and reported on the page.

Run locally:   flask --app app run      (DATABASE_URL must point to PostgreSQL)
Production:    gunicorn app:app
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, time

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from db import get_engine
from init_db import init_database

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "csci341-assignment3-dev-key")
engine = get_engine()

PAPER_STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
RECOMMENDATIONS = ["accept", "reject"]
ORCID_RE = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{5,30}$")
MAX_AUTHOR_ROWS = 30
ALLOW_RESET = os.environ.get("ALLOW_RESET", "1") != "0"


# =============================================================================
# Error handling
# =============================================================================
class ValidationError(Exception):
    """Raised by application-level checks; carries user-facing messages."""

    def __init__(self, messages):
        if isinstance(messages, str):
            messages = [messages]
        super().__init__("; ".join(messages))
        self.messages = list(messages)


# Friendly texts for constraint violations reported by PostgreSQL
CONSTRAINT_MESSAGES = {
    "uq_app_user_email": "Another user already has this e-mail address (e-mails must be unique).",
    "ck_app_user_email_format": "The e-mail address is not valid.",
    "ck_app_user_phone_format": "The phone number may contain only digits, spaces, parentheses, hyphens and a leading +.",
    "ck_app_user_names_not_blank": "Given name and surname are required.",
    "uq_author_orcid": "Another author already has this ORCID.",
    "ck_author_orcid_format": "ORCID must look like 0000-0002-1825-0097.",
    "ck_reviewer_experience_nonnegative": "Years of reviewing experience cannot be negative.",
    "pk_paper_author": "The same author is listed twice for this paper.",
    "uq_paper_author_position": "Two authors of the same paper cannot share an author position.",
    "uq_paper_one_corresponding": "A paper can have only one corresponding author.",
    "ck_pa_position_positive": "Author positions must be positive integers.",
    "ck_paper_status": "Paper status must be submitted, under review, accepted, rejected or withdrawn.",
    "ck_paper_session_requires_accepted": "Only accepted papers can be assigned to a session.",
    "pk_paper_version": "This paper already has a version with that number.",
    "ck_pv_version_positive": "Version numbers must be positive integers.",
    "uq_review_paper_reviewer": "This reviewer has already reviewed this paper (at most one review per reviewer and paper).",
    "ck_review_score": "The overall score must be an integer from 1 to 5.",
    "ck_review_recommendation": "The recommendation must be 'accept' or 'reject'.",
    "ck_review_comments_not_blank": "Comments for the authors are required.",
    "ck_session_times": "The session end time must be later than its start time.",
    "fk_session_chair_in_pool": "The session chair must belong to the reviewer pool of the session's conference.",
    "fk_track_coordinator_in_pool": "This reviewer coordinates a track of that conference and must stay in its pool.",
    "fk_pa_author": "The user is still listed as an author of at least one paper.",
    "fk_review_reviewer": "The reviewer still has submitted reviews.",
    "fk_track_coordinator": "The reviewer still coordinates a track.",
    "fk_session_chair": "The reviewer still chairs a session.",
}


def describe_db_error(exc: DBAPIError) -> str:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    if constraint in CONSTRAINT_MESSAGES:
        return f"Rejected by the database: {CONSTRAINT_MESSAGES[constraint]} (constraint {constraint})"
    primary = getattr(diag, "message_primary", None) or str(orig or exc).splitlines()[0]
    return f"Rejected by the database: {primary}"


def report_failure(exc: Exception) -> None:
    if isinstance(exc, ValidationError):
        for message in exc.messages:
            flash(message, "error")
    elif isinstance(exc, DBAPIError):
        flash(describe_db_error(exc), "error")
    else:
        flash(f"The operation failed and was rolled back: {exc}", "error")


# =============================================================================
# Small database helpers (all SQL uses bound parameters)
# =============================================================================
def fetch_all(sql: str, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def fetch_one(sql: str, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().first()


def c_all(conn, sql: str, **params):
    return conn.execute(text(sql), params).mappings().all()


def c_one(conn, sql: str, **params):
    return conn.execute(text(sql), params).mappings().first()


def c_scalar(conn, sql: str, **params):
    return conn.execute(text(sql), params).scalar()


def c_exec(conn, sql: str, **params):
    return conn.execute(text(sql), params)


# =============================================================================
# Form parsing helpers
# =============================================================================
def form_dict() -> dict:
    data = request.form.to_dict(flat=True)
    data["pools"] = request.form.getlist("pools")
    return data


def get_str(form, name, label, errors, required=True, max_len=None) -> str:
    value = (form.get(name) or "").strip()
    if required and not value:
        errors.append(f"{label} is required.")
    if max_len and len(value) > max_len:
        errors.append(f"{label} must be at most {max_len} characters.")
    return value


def get_int(form, name, label, errors, required=True, min_value=None, max_value=None):
    raw = (form.get(name) or "").strip()
    if not raw:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        value = int(raw)
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if min_value is not None and value < min_value:
        errors.append(f"{label} must be at least {min_value}.")
    if max_value is not None and value > max_value:
        errors.append(f"{label} must be at most {max_value}.")
    return value


def get_date(form, name, label, errors, required=True):
    raw = (form.get(name) or "").strip()
    if not raw:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors.append(f"{label} must be a date (YYYY-MM-DD).")
        return None


def get_time(form, name, label, errors):
    raw = (form.get(name) or "").strip()
    if not raw:
        errors.append(f"{label} is required.")
        return None
    try:
        return time.fromisoformat(raw)
    except ValueError:
        errors.append(f"{label} must be a time (HH:MM).")
        return None


def get_datetime(form, name, label, errors):
    raw = (form.get(name) or "").strip()
    if not raw:
        errors.append(f"{label} is required.")
        return None
    try:
        return datetime.fromisoformat(raw).replace(microsecond=0)
    except ValueError:
        errors.append(f"{label} must be a date and time.")
        return None


def split_labels(raw: str | None) -> list[str]:
    """One label per line (commas and semicolons also separate labels)."""
    labels, seen = [], set()
    for part in re.split(r"[\n,;]+", raw or ""):
        label = part.strip()
        if label and label.lower() not in seen:
            seen.add(label.lower())
            labels.append(label)
    return labels


def check_labels(labels, label, errors, max_len=100):
    for item in labels:
        if len(item) > max_len:
            errors.append(f"{label} '{item[:30]}...' is longer than {max_len} characters.")


# =============================================================================
# Template helpers
# =============================================================================
@app.template_filter("fmt")
def fmt(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)


def iso_time(value) -> str:
    return value.strftime("%H:%M") if value else ""


def iso_datetime(value) -> str:
    return value.strftime("%Y-%m-%dT%H:%M") if value else ""


@app.context_processor
def inject_globals():
    return {"PAPER_STATUSES": PAPER_STATUSES, "RECOMMENDATIONS": RECOMMENDATIONS, "ALLOW_RESET": ALLOW_RESET}


@app.errorhandler(SQLAlchemyError)
def handle_db_error(exc):
    app.logger.exception("Database error")
    return render_template("error.html", message=str(getattr(exc, "orig", exc) or exc)), 500


# =============================================================================
# Home, read-only pages, maintenance
# =============================================================================
@app.get("/")
def index():
    counts = fetch_one("""
        SELECT (SELECT COUNT(*) FROM app_user)           AS users,
               (SELECT COUNT(*) FROM paper)              AS papers,
               (SELECT COUNT(*) FROM paper_version)      AS versions,
               (SELECT COUNT(*) FROM review)             AS reviews,
               (SELECT COUNT(*) FROM conference_session) AS sessions,
               (SELECT COUNT(*) FROM conference)         AS conferences,
               (SELECT COUNT(*) FROM track)              AS tracks
    """)
    return render_template("index.html", counts=counts)


@app.get("/healthz")
def healthz():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return "ok"


@app.get("/conferences")
def conferences():
    confs = fetch_all("SELECT * FROM conference ORDER BY conference_id")
    hosts = fetch_all("SELECT conference_id, host_name FROM conference_host ORDER BY conference_id, host_name")
    tracks = fetch_all("""
        SELECT t.track_id, t.conference_id, t.name, t.research_area, t.description,
               u.given_name || ' ' || u.surname AS coordinator,
               (SELECT COUNT(*) FROM paper p WHERE p.track_id = t.track_id) AS paper_count
        FROM track t JOIN app_user u ON u.user_id = t.coordinator_id
        ORDER BY t.conference_id, t.track_id
    """)
    pools = fetch_all("""
        SELECT cr.conference_id, r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
               r.years_experience
        FROM conference_reviewer cr
        JOIN reviewer r ON r.reviewer_id = cr.reviewer_id
        JOIN app_user u ON u.user_id = r.reviewer_id
        ORDER BY cr.conference_id, u.surname, u.given_name
    """)
    sessions = fetch_all("""
        SELECT s.session_id, s.conference_id, s.title, s.session_date, s.start_time, s.end_time,
               (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS paper_count
        FROM conference_session s ORDER BY s.conference_id, s.session_date, s.start_time
    """)

    def by_conf(rows):
        grouped = {}
        for row in rows:
            grouped.setdefault(row["conference_id"], []).append(row)
        return grouped

    return render_template("conferences.html", confs=confs, hosts=by_conf(hosts), tracks=by_conf(tracks),
                           pools=by_conf(pools), sessions=by_conf(sessions))


@app.get("/schedule")
def schedule():
    rows = fetch_all("""
        SELECT * FROM accepted_paper_schedule
        ORDER BY conference_id, session_date, start_time, session_id, paper_id
    """)
    return render_template("schedule.html", rows=rows)


@app.post("/admin/reset")
def admin_reset():
    if not ALLOW_RESET:
        abort(403)
    try:
        init_database(engine)
        flash("The database was restored to the original seed data.", "success")
    except SQLAlchemyError as exc:
        report_failure(exc)
    return redirect(url_for("index"))


# =============================================================================
# USERS (with author and reviewer profiles)
# =============================================================================
def all_conferences():
    return fetch_all("SELECT conference_id, acronym, name FROM conference ORDER BY conference_id")


@app.get("/users")
def users_list():
    users = fetch_all("""
        SELECT u.user_id, u.given_name, u.surname, u.email, u.affiliation, u.country, u.phone_number,
               (a.author_id IS NOT NULL)   AS is_author,
               (r.reviewer_id IS NOT NULL) AS is_reviewer
        FROM app_user u
        LEFT JOIN author a   ON a.author_id = u.user_id
        LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
        ORDER BY u.user_id
    """)
    return render_template("users_list.html", users=users)


@app.get("/users/<int:user_id>")
def user_detail(user_id):
    user = fetch_one("SELECT * FROM app_user WHERE user_id = :uid", uid=user_id)
    if user is None:
        abort(404)
    author = fetch_one("SELECT orcid FROM author WHERE author_id = :uid", uid=user_id)
    reviewer = fetch_one("SELECT years_experience FROM reviewer WHERE reviewer_id = :uid", uid=user_id)
    areas = fetch_all("SELECT area_label FROM author_research_area WHERE author_id = :uid ORDER BY area_label", uid=user_id)
    expertise = fetch_all("SELECT area_label FROM reviewer_expertise WHERE reviewer_id = :uid ORDER BY area_label", uid=user_id)
    pools = fetch_all("""
        SELECT c.conference_id, c.acronym FROM conference_reviewer cr
        JOIN conference c ON c.conference_id = cr.conference_id
        WHERE cr.reviewer_id = :uid ORDER BY c.conference_id
    """, uid=user_id)
    papers = fetch_all("""
        SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
        FROM paper_author pa JOIN paper p ON p.paper_id = pa.paper_id
        WHERE pa.author_id = :uid ORDER BY p.paper_id
    """, uid=user_id)
    reviews = fetch_all("""
        SELECT rv.review_id, rv.paper_id, p.title, rv.overall_score, rv.recommendation
        FROM review rv JOIN paper p ON p.paper_id = rv.paper_id
        WHERE rv.reviewer_id = :uid ORDER BY rv.review_id
    """, uid=user_id)
    tracks = fetch_all("SELECT track_id, name FROM track WHERE coordinator_id = :uid ORDER BY track_id", uid=user_id)
    sessions = fetch_all("SELECT session_id, title FROM conference_session WHERE chair_id = :uid ORDER BY session_id", uid=user_id)
    return render_template("user_detail.html", user=user, author=author, reviewer=reviewer, areas=areas,
                           expertise=expertise, pools=pools, papers=papers, reviews=reviews,
                           tracks=tracks, sessions=sessions)


def parse_user_form(form) -> dict:
    errors: list[str] = []
    d = {
        "given_name": get_str(form, "given_name", "Given name", errors, max_len=100),
        "surname": get_str(form, "surname", "Surname", errors, max_len=100),
        "email": get_str(form, "email", "E-mail", errors, max_len=255).lower(),
        "affiliation": get_str(form, "affiliation", "Affiliation", errors, max_len=200),
        "country": get_str(form, "country", "Country", errors, max_len=100),
        "phone_number": get_str(form, "phone_number", "Phone number", errors, max_len=30),
        "is_author": bool(form.get("is_author")),
        "is_reviewer": bool(form.get("is_reviewer")),
    }
    if d["email"] and d["email"].find("@") < 1:
        errors.append("The e-mail address is not valid.")
    if d["phone_number"] and not PHONE_RE.match(d["phone_number"]):
        errors.append("The phone number may contain only digits, spaces, parentheses, hyphens and a leading +.")
    if not (d["is_author"] or d["is_reviewer"]):
        errors.append("Every user must be an author, a reviewer, or both - tick at least one role.")
    if d["is_author"]:
        d["orcid"] = (form.get("orcid") or "").strip().upper() or None
        if d["orcid"] and not ORCID_RE.match(d["orcid"]):
            errors.append("ORCID must look like 0000-0002-1825-0097.")
        d["research_areas"] = split_labels(form.get("research_areas"))
        if not d["research_areas"]:
            errors.append("An author needs at least one research-area label.")
        check_labels(d["research_areas"], "Research area", errors)
    if d["is_reviewer"]:
        d["years_experience"] = get_int(form, "years_experience", "Years of reviewing experience",
                                        errors, min_value=0, max_value=80)
        d["expertise_areas"] = split_labels(form.get("expertise_areas"))
        if not d["expertise_areas"]:
            errors.append("A reviewer needs at least one expertise-area label.")
        check_labels(d["expertise_areas"], "Expertise area", errors)
        d["pools"] = sorted({int(x) for x in form.get("pools", []) if str(x).isdigit()})
    if errors:
        raise ValidationError(errors)
    return d


def author_blockers(conn, user_id) -> list[str]:
    papers = c_all(conn, "SELECT paper_id FROM paper_author WHERE author_id = :uid ORDER BY paper_id", uid=user_id)
    if papers:
        return ["the user is an author of paper(s) " + ", ".join(f"#{p['paper_id']}" for p in papers)]
    return []


def reviewer_blockers(conn, user_id) -> list[str]:
    blockers = []
    reviews = c_all(conn, "SELECT review_id FROM review WHERE reviewer_id = :uid ORDER BY review_id", uid=user_id)
    if reviews:
        blockers.append("the user has submitted review(s) " + ", ".join(f"#{r['review_id']}" for r in reviews))
    tracks = c_all(conn, "SELECT track_id FROM track WHERE coordinator_id = :uid ORDER BY track_id", uid=user_id)
    if tracks:
        blockers.append("the user coordinates track(s) " + ", ".join(f"#{t['track_id']}" for t in tracks))
    sessions = c_all(conn, "SELECT session_id FROM conference_session WHERE chair_id = :uid ORDER BY session_id", uid=user_id)
    if sessions:
        blockers.append("the user chairs session(s) " + ", ".join(f"#{s['session_id']}" for s in sessions))
    return blockers


def save_user(conn, d: dict, user_id: int | None = None) -> int:
    duplicate = c_one(conn, """
        SELECT user_id FROM app_user
        WHERE LOWER(email) = LOWER(:email) AND user_id <> COALESCE(:uid, -1)
    """, email=d["email"], uid=user_id)
    if duplicate:
        raise ValidationError(f"The e-mail {d['email']} is already used by user #{duplicate['user_id']} (e-mails must be unique).")

    core = {k: d[k] for k in ("given_name", "surname", "email", "affiliation", "country", "phone_number")}
    if user_id is None:
        user_id = c_scalar(conn, """
            INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
            VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
            RETURNING user_id
        """, **core)
        was_author = was_reviewer = False
    else:
        result = c_exec(conn, """
            UPDATE app_user
            SET given_name = :given_name, surname = :surname, email = :email,
                affiliation = :affiliation, country = :country, phone_number = :phone_number
            WHERE user_id = :uid
        """, uid=user_id, **core)
        if result.rowcount == 0:
            raise ValidationError(f"User #{user_id} does not exist.")
        was_author = c_scalar(conn, "SELECT EXISTS (SELECT 1 FROM author WHERE author_id = :uid)", uid=user_id)
        was_reviewer = c_scalar(conn, "SELECT EXISTS (SELECT 1 FROM reviewer WHERE reviewer_id = :uid)", uid=user_id)

    # ---- author profile -------------------------------------------------------
    if d["is_author"]:
        if was_author:
            c_exec(conn, "UPDATE author SET orcid = :orcid WHERE author_id = :uid", orcid=d["orcid"], uid=user_id)
        else:
            c_exec(conn, "INSERT INTO author (author_id, orcid) VALUES (:uid, :orcid)", uid=user_id, orcid=d["orcid"])
        c_exec(conn, "DELETE FROM author_research_area WHERE author_id = :uid", uid=user_id)
        for label in d["research_areas"]:
            c_exec(conn, "INSERT INTO author_research_area (author_id, area_label) VALUES (:uid, :label)",
                   uid=user_id, label=label)
    elif was_author:
        blockers = author_blockers(conn, user_id)
        if blockers:
            raise ValidationError("Cannot remove the author role: " + "; ".join(blockers)
                                  + ". Remove the authorship in the paper form first.")
        c_exec(conn, "DELETE FROM author WHERE author_id = :uid", uid=user_id)   # cascades to research areas

    # ---- reviewer profile -----------------------------------------------------
    if d["is_reviewer"]:
        if was_reviewer:
            c_exec(conn, "UPDATE reviewer SET years_experience = :years WHERE reviewer_id = :uid",
                   years=d["years_experience"], uid=user_id)
        else:
            c_exec(conn, "INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:uid, :years)",
                   uid=user_id, years=d["years_experience"])
        c_exec(conn, "DELETE FROM reviewer_expertise WHERE reviewer_id = :uid", uid=user_id)
        for label in d["expertise_areas"]:
            c_exec(conn, "INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES (:uid, :label)",
                   uid=user_id, label=label)
        current = {r["conference_id"] for r in c_all(
            conn, "SELECT conference_id FROM conference_reviewer WHERE reviewer_id = :uid", uid=user_id)}
        wanted = set(d["pools"])
        for cid in sorted(current - wanted):
            roles = c_one(conn, """
                SELECT (SELECT COUNT(*) FROM track WHERE conference_id = :cid AND coordinator_id = :uid) AS tracks,
                       (SELECT COUNT(*) FROM conference_session WHERE conference_id = :cid AND chair_id = :uid) AS sessions,
                       (SELECT acronym FROM conference WHERE conference_id = :cid) AS acronym
            """, cid=cid, uid=user_id)
            if roles["tracks"] or roles["sessions"]:
                raise ValidationError(
                    f"Cannot remove the reviewer from the pool of {roles['acronym']}: they coordinate "
                    f"{roles['tracks']} track(s) and chair {roles['sessions']} session(s) of that conference.")
            c_exec(conn, "DELETE FROM conference_reviewer WHERE conference_id = :cid AND reviewer_id = :uid",
                   cid=cid, uid=user_id)
        for cid in sorted(wanted - current):
            c_exec(conn, "INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES (:cid, :uid)",
                   cid=cid, uid=user_id)
    elif was_reviewer:
        blockers = reviewer_blockers(conn, user_id)
        if blockers:
            raise ValidationError("Cannot remove the reviewer role: " + "; ".join(blockers) + ".")
        c_exec(conn, "DELETE FROM reviewer WHERE reviewer_id = :uid", uid=user_id)  # cascades expertise + pools
    return user_id


def user_form_from_db(user_id):
    user = fetch_one("SELECT * FROM app_user WHERE user_id = :uid", uid=user_id)
    if user is None:
        return None
    author = fetch_one("SELECT orcid FROM author WHERE author_id = :uid", uid=user_id)
    reviewer = fetch_one("SELECT years_experience FROM reviewer WHERE reviewer_id = :uid", uid=user_id)
    areas = fetch_all("SELECT area_label FROM author_research_area WHERE author_id = :uid ORDER BY area_label", uid=user_id)
    expertise = fetch_all("SELECT area_label FROM reviewer_expertise WHERE reviewer_id = :uid ORDER BY area_label", uid=user_id)
    pools = fetch_all("SELECT conference_id FROM conference_reviewer WHERE reviewer_id = :uid", uid=user_id)
    form = {k: user[k] for k in ("given_name", "surname", "email", "affiliation", "country", "phone_number")}
    form.update({
        "is_author": "on" if author else "",
        "orcid": (author["orcid"] or "") if author else "",
        "research_areas": "\n".join(a["area_label"] for a in areas),
        "is_reviewer": "on" if reviewer else "",
        "years_experience": str(reviewer["years_experience"]) if reviewer else "",
        "expertise_areas": "\n".join(e["area_label"] for e in expertise),
        "pools": [str(p["conference_id"]) for p in pools],
    })
    return form


@app.route("/users/new", methods=["GET", "POST"])
def user_create():
    form = {"pools": []}
    if request.method == "POST":
        form = form_dict()
        try:
            d = parse_user_form(form)
            with engine.begin() as conn:
                user_id = save_user(conn, d)
            flash(f"User #{user_id} created.", "success")
            return redirect(url_for("user_detail", user_id=user_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    return render_template("user_form.html", form=form, user_id=None, conferences=all_conferences())


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    if request.method == "POST":
        form = form_dict()
        try:
            d = parse_user_form(form)
            with engine.begin() as conn:
                save_user(conn, d, user_id)
            flash(f"User #{user_id} updated.", "success")
            return redirect(url_for("user_detail", user_id=user_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        form = user_form_from_db(user_id)
        if form is None:
            abort(404)
    return render_template("user_form.html", form=form, user_id=user_id, conferences=all_conferences())


@app.post("/users/<int:user_id>/delete")
def user_delete(user_id):
    try:
        with engine.begin() as conn:
            blockers = author_blockers(conn, user_id) + reviewer_blockers(conn, user_id)
            if blockers:
                raise ValidationError(f"User #{user_id} cannot be deleted because " + "; ".join(blockers) + ".")
            result = c_exec(conn, "DELETE FROM app_user WHERE user_id = :uid", uid=user_id)
            if result.rowcount == 0:
                raise ValidationError(f"User #{user_id} does not exist.")
        flash(f"User #{user_id} deleted together with their author/reviewer profile, labels and pool memberships.",
              "success")
        return redirect(url_for("users_list"))
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
        return redirect(url_for("user_detail", user_id=user_id))


# =============================================================================
# Required application check 2 (shared): valid session assignment
# =============================================================================
def session_assignment_errors(status, track_conference_id, track_label, session) -> list[str]:
    """A scheduled paper must be accepted, and its track and session must belong to the same conference."""
    errors = []
    if status != "accepted":
        errors.append(f"Invalid session assignment: only accepted papers can be scheduled, but the paper's status "
                      f"is '{status}'.")
    if track_conference_id != session["conference_id"]:
        errors.append(f"Invalid session assignment: session #{session['session_id']} '{session['title']}' belongs to "
                      f"{session['acronym']} (conference #{session['conference_id']}), but the paper's track "
                      f"{track_label} belongs to conference #{track_conference_id}.")
    return errors


def load_session(conn, session_id):
    return c_one(conn, """
        SELECT s.session_id, s.title, s.conference_id, c.acronym
        FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
        WHERE s.session_id = :sid
    """, sid=session_id)


# =============================================================================
# PAPERS (with authorship, keywords and versions)
# =============================================================================
def paper_choices():
    with engine.connect() as conn:
        tracks = c_all(conn, """
            SELECT t.track_id, t.name, t.conference_id, c.acronym
            FROM track t JOIN conference c ON c.conference_id = t.conference_id
            ORDER BY t.conference_id, t.track_id
        """)
        sessions = c_all(conn, """
            SELECT s.session_id, s.title, s.session_date, s.start_time, s.conference_id, c.acronym
            FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
            ORDER BY s.conference_id, s.session_date, s.start_time, s.session_id
        """)
        authors = c_all(conn, """
            SELECT a.author_id, u.given_name || ' ' || u.surname AS full_name, u.email
            FROM author a JOIN app_user u ON u.user_id = a.author_id
            ORDER BY u.surname, u.given_name, a.author_id
        """)
    return {"tracks": tracks, "sessions": sessions, "authors": authors}


@app.get("/papers")
def papers_list():
    status = request.args.get("status") or None
    papers = fetch_all("""
        SELECT p.paper_id, p.title, p.status, p.submission_date, t.name AS track_name, c.acronym,
               s.session_id, s.title AS session_title,
               ca.given_name || ' ' || ca.surname AS corresponding_author,
               (SELECT MAX(v.version_no) FROM paper_version v WHERE v.paper_id = p.paper_id) AS current_version,
               (SELECT COUNT(*) FROM review rv WHERE rv.paper_id = p.paper_id) AS review_count
        FROM paper p
        JOIN track t      ON t.track_id = p.track_id
        JOIN conference c ON c.conference_id = t.conference_id
        LEFT JOIN conference_session s ON s.session_id = p.session_id
        LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
        LEFT JOIN app_user ca     ON ca.user_id = pa.author_id
        WHERE (CAST(:status AS VARCHAR) IS NULL OR p.status = :status)
        ORDER BY p.paper_id
    """, status=status)
    return render_template("papers_list.html", papers=papers, status=status)


@app.get("/papers/<int:paper_id>")
def paper_detail(paper_id):
    paper = fetch_one("""
        SELECT p.paper_id, p.track_id, p.title, p.abstract, p.submission_date, p.status, p.session_id,
               t.name AS track_name, t.conference_id, c.acronym,
               s.title AS session_title, s.session_date, s.start_time, s.end_time, s.room_label
        FROM paper p
        JOIN track t      ON t.track_id = p.track_id
        JOIN conference c ON c.conference_id = t.conference_id
        LEFT JOIN conference_session s ON s.session_id = p.session_id
        WHERE p.paper_id = :pid
    """, pid=paper_id)
    if paper is None:
        abort(404)
    keywords = fetch_all("SELECT keyword FROM paper_keyword WHERE paper_id = :pid ORDER BY keyword", pid=paper_id)
    authors = fetch_all("""
        SELECT pa.author_id, pa.author_position, pa.is_corresponding,
               u.given_name || ' ' || u.surname AS full_name, u.email
        FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
        WHERE pa.paper_id = :pid ORDER BY pa.author_position
    """, pid=paper_id)
    versions = fetch_all("""
        SELECT version_no, file_location, uploaded_at, change_note
        FROM paper_version WHERE paper_id = :pid ORDER BY version_no DESC
    """, pid=paper_id)
    reviews = fetch_all("""
        SELECT rv.review_id, rv.reviewer_id, u.given_name || ' ' || u.surname AS reviewer_name,
               rv.overall_score, rv.recommendation, rv.review_submission_date
        FROM review rv JOIN app_user u ON u.user_id = rv.reviewer_id
        WHERE rv.paper_id = :pid ORDER BY rv.review_id
    """, pid=paper_id)
    next_version = (versions[0]["version_no"] + 1) if versions else 1
    return render_template("paper_detail.html", paper=paper, keywords=keywords, authors=authors,
                           versions=versions, reviews=reviews, next_version=next_version,
                           now=iso_datetime(datetime.now()))


def blank_author_rows(n=5):
    return [{"author_id": "", "position": str(i + 1), "corresponding": i == 0} for i in range(n)]


def author_rows_from_form(form):
    try:
        n = min(int(form.get("author_rows", 5)), MAX_AUTHOR_ROWS)
    except ValueError:
        n = 5
    corresponding = form.get("corresponding")
    return [{"author_id": form.get(f"author_id_{i}", ""), "position": form.get(f"position_{i}", ""),
             "corresponding": corresponding == str(i)} for i in range(n)]


def parse_paper_form(form, creating: bool) -> dict:
    errors: list[str] = []
    d = {
        "track_id": get_int(form, "track_id", "Track", errors),
        "title": get_str(form, "title", "Title", errors, max_len=300),
        "abstract": get_str(form, "abstract", "Abstract", errors),
        "submission_date": get_date(form, "submission_date", "Submission date", errors),
        "status": (form.get("status") or "").strip(),
        "session_id": get_int(form, "session_id", "Session", errors, required=False),
        "keywords": split_labels(form.get("keywords")),
    }
    if d["status"] not in PAPER_STATUSES:
        errors.append("Status must be one of: " + ", ".join(PAPER_STATUSES) + ".")
    if not d["keywords"]:
        errors.append("A paper needs at least one keyword.")
    check_labels(d["keywords"], "Keyword", errors)

    authors = []
    for i, row in enumerate(author_rows_from_form(form)):
        if not str(row["author_id"]).strip():
            continue
        row_errors: list[str] = []
        author_id = get_int({"v": row["author_id"]}, "v", f"Author in row {i + 1}", row_errors)
        position = get_int({"v": row["position"]}, "v", f"Position in row {i + 1}", row_errors, min_value=1)
        errors.extend(row_errors)
        authors.append({"author_id": author_id, "position": position, "is_corresponding": row["corresponding"]})
    if not authors:
        errors.append("A paper needs at least one author.")
    ids = [a["author_id"] for a in authors if a["author_id"] is not None]
    if len(ids) != len(set(ids)):
        errors.append("The same author is listed more than once.")
    positions = [a["position"] for a in authors if a["position"] is not None]
    if len(positions) != len(set(positions)):
        errors.append("Author positions must be unique within the paper.")
    if authors and sum(1 for a in authors if a["is_corresponding"]) != 1:
        errors.append("Select exactly one corresponding author (the radio button of a filled author row).")
    d["authors"] = authors

    if creating:
        d["version_no"] = get_int(form, "version_no", "Version number", errors, min_value=1)
        d["file_location"] = get_str(form, "file_location", "File location", errors, max_len=500)
        d["uploaded_at"] = get_datetime(form, "uploaded_at", "Upload date and time", errors)
        d["change_note"] = (form.get("change_note") or "").strip() or None
    if errors:
        raise ValidationError(errors)
    return d


def validate_paper(conn, d: dict, paper_id: int | None) -> None:
    errors: list[str] = []
    track = c_one(conn, """
        SELECT t.track_id, t.name, t.conference_id FROM track t WHERE t.track_id = :tid
    """, tid=d["track_id"])
    if track is None:
        errors.append(f"Track #{d['track_id']} does not exist.")

    # Required check 2: valid session assignment (status, track and session conference)
    if d["session_id"] is not None:
        session = load_session(conn, d["session_id"])
        if session is None:
            errors.append(f"Session #{d['session_id']} does not exist.")
        elif track is not None:
            errors.extend(session_assignment_errors(d["status"], track["conference_id"],
                                                    f"'{track['name']}'", session))

    for a in d["authors"]:
        exists = c_scalar(conn, "SELECT EXISTS (SELECT 1 FROM author WHERE author_id = :aid)", aid=a["author_id"])
        if not exists:
            errors.append(f"User #{a['author_id']} does not have an author profile.")

    # Required check 1: no self-reviews when the authors change
    if paper_id is not None:
        for a in d["authors"]:
            review = c_one(conn, """
                SELECT rv.review_id, u.given_name || ' ' || u.surname AS full_name
                FROM review rv JOIN app_user u ON u.user_id = rv.reviewer_id
                WHERE rv.paper_id = :pid AND rv.reviewer_id = :aid
            """, pid=paper_id, aid=a["author_id"])
            if review:
                errors.append(f"Self-review conflict: {review['full_name']} (user #{a['author_id']}) already "
                              f"reviewed this paper (review #{review['review_id']}) and therefore cannot be "
                              f"one of its authors.")
    if errors:
        raise ValidationError(errors)


def save_paper(conn, d: dict, paper_id: int | None = None) -> int:
    fields = {k: d[k] for k in ("track_id", "title", "abstract", "submission_date", "status", "session_id")}
    if paper_id is None:
        paper_id = c_scalar(conn, """
            INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
            VALUES (:track_id, :title, :abstract, :submission_date, :status, :session_id)
            RETURNING paper_id
        """, **fields)
        c_exec(conn, """
            INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
            VALUES (:pid, :vno, :loc, :uploaded_at, :note)
        """, pid=paper_id, vno=d["version_no"], loc=d["file_location"], uploaded_at=d["uploaded_at"],
               note=d["change_note"])
    else:
        result = c_exec(conn, """
            UPDATE paper
            SET track_id = :track_id, title = :title, abstract = :abstract,
                submission_date = :submission_date, status = :status, session_id = :session_id
            WHERE paper_id = :pid
        """, pid=paper_id, **fields)
        if result.rowcount == 0:
            raise ValidationError(f"Paper #{paper_id} does not exist.")
        c_exec(conn, "DELETE FROM paper_keyword WHERE paper_id = :pid", pid=paper_id)
        c_exec(conn, "DELETE FROM paper_author WHERE paper_id = :pid", pid=paper_id)
    for keyword in d["keywords"]:
        c_exec(conn, "INSERT INTO paper_keyword (paper_id, keyword) VALUES (:pid, :kw)", pid=paper_id, kw=keyword)
    for a in d["authors"]:
        c_exec(conn, """
            INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
            VALUES (:pid, :aid, :pos, :corr)
        """, pid=paper_id, aid=a["author_id"], pos=a["position"], corr=a["is_corresponding"])
    return paper_id


@app.route("/papers/new", methods=["GET", "POST"])
def paper_create():
    if request.method == "POST":
        form = form_dict()
        rows = author_rows_from_form(form)
        try:
            d = parse_paper_form(form, creating=True)
            with engine.begin() as conn:
                validate_paper(conn, d, None)
                paper_id = save_paper(conn, d)
            flash(f"Paper #{paper_id} created with its authors, keywords and version {d['version_no']}.", "success")
            return redirect(url_for("paper_detail", paper_id=paper_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        form = {"submission_date": date.today().isoformat(), "status": "submitted", "version_no": "1",
                "uploaded_at": iso_datetime(datetime.now())}
        rows = blank_author_rows()
    return render_template("paper_form.html", form=form, rows=rows, paper_id=None, **paper_choices())


@app.route("/papers/<int:paper_id>/edit", methods=["GET", "POST"])
def paper_edit(paper_id):
    if request.method == "POST":
        form = form_dict()
        rows = author_rows_from_form(form)
        try:
            d = parse_paper_form(form, creating=False)
            with engine.begin() as conn:
                c_one(conn, "SELECT paper_id FROM paper WHERE paper_id = :pid FOR UPDATE", pid=paper_id)
                validate_paper(conn, d, paper_id)
                save_paper(conn, d, paper_id)
            flash(f"Paper #{paper_id} updated (details, authors and keywords saved in one transaction).", "success")
            return redirect(url_for("paper_detail", paper_id=paper_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        paper = fetch_one("SELECT * FROM paper WHERE paper_id = :pid", pid=paper_id)
        if paper is None:
            abort(404)
        keywords = fetch_all("SELECT keyword FROM paper_keyword WHERE paper_id = :pid ORDER BY keyword", pid=paper_id)
        authors = fetch_all("""
            SELECT author_id, author_position, is_corresponding FROM paper_author
            WHERE paper_id = :pid ORDER BY author_position
        """, pid=paper_id)
        form = {
            "track_id": str(paper["track_id"]), "title": paper["title"], "abstract": paper["abstract"],
            "submission_date": paper["submission_date"].isoformat(), "status": paper["status"],
            "session_id": str(paper["session_id"]) if paper["session_id"] else "",
            "keywords": "\n".join(k["keyword"] for k in keywords),
        }
        rows = [{"author_id": str(a["author_id"]), "position": str(a["author_position"]),
                 "corresponding": a["is_corresponding"]} for a in authors]
        next_pos = max([a["author_position"] for a in authors], default=0)
        rows += [{"author_id": "", "position": str(next_pos + i + 1), "corresponding": False} for i in range(3)]
    return render_template("paper_form.html", form=form, rows=rows, paper_id=paper_id, **paper_choices())


@app.post("/papers/<int:paper_id>/delete")
def paper_delete(paper_id):
    try:
        with engine.begin() as conn:
            counts = c_one(conn, """
                SELECT (SELECT COUNT(*) FROM paper_version WHERE paper_id = :pid) AS versions,
                       (SELECT COUNT(*) FROM review WHERE paper_id = :pid) AS reviews
            """, pid=paper_id)
            result = c_exec(conn, "DELETE FROM paper WHERE paper_id = :pid", pid=paper_id)
            if result.rowcount == 0:
                raise ValidationError(f"Paper #{paper_id} does not exist.")
        flash(f"Paper #{paper_id} deleted; ON DELETE CASCADE also removed its authorship and keyword rows, "
              f"{counts['versions']} version(s) and {counts['reviews']} review(s).", "success")
        return redirect(url_for("papers_list"))
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
        return redirect(url_for("paper_detail", paper_id=paper_id))


# ---- versions ----------------------------------------------------------------
def parse_version_form(form, with_number: bool) -> dict:
    errors: list[str] = []
    d = {
        "file_location": get_str(form, "file_location", "File location", errors, max_len=500),
        "uploaded_at": get_datetime(form, "uploaded_at", "Upload date and time", errors),
        "change_note": (form.get("change_note") or "").strip() or None,
    }
    if with_number:
        d["version_no"] = get_int(form, "version_no", "Version number", errors, min_value=1)
    if errors:
        raise ValidationError(errors)
    return d


@app.post("/papers/<int:paper_id>/versions/new")
def version_create(paper_id):
    try:
        d = parse_version_form(request.form, with_number=True)
        with engine.begin() as conn:
            if c_one(conn, "SELECT paper_id FROM paper WHERE paper_id = :pid FOR UPDATE", pid=paper_id) is None:
                raise ValidationError(f"Paper #{paper_id} does not exist.")
            if c_one(conn, "SELECT 1 FROM paper_version WHERE paper_id = :pid AND version_no = :vno",
                     pid=paper_id, vno=d["version_no"]):
                raise ValidationError(f"Paper #{paper_id} already has a version {d['version_no']}.")
            c_exec(conn, """
                INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                VALUES (:pid, :vno, :loc, :uploaded_at, :note)
            """, pid=paper_id, vno=d["version_no"], loc=d["file_location"], uploaded_at=d["uploaded_at"],
                   note=d["change_note"])
        flash(f"Version {d['version_no']} added to paper #{paper_id}.", "success")
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
    return redirect(url_for("paper_detail", paper_id=paper_id))


@app.route("/papers/<int:paper_id>/versions/<int:version_no>/edit", methods=["GET", "POST"])
def version_edit(paper_id, version_no):
    version = fetch_one("""
        SELECT v.*, p.title FROM paper_version v JOIN paper p ON p.paper_id = v.paper_id
        WHERE v.paper_id = :pid AND v.version_no = :vno
    """, pid=paper_id, vno=version_no)
    if version is None:
        abort(404)
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            d = parse_version_form(form, with_number=False)
            with engine.begin() as conn:
                c_exec(conn, """
                    UPDATE paper_version
                    SET file_location = :loc, uploaded_at = :uploaded_at, change_note = :note
                    WHERE paper_id = :pid AND version_no = :vno
                """, loc=d["file_location"], uploaded_at=d["uploaded_at"], note=d["change_note"],
                       pid=paper_id, vno=version_no)
            flash(f"Version {version_no} of paper #{paper_id} updated.", "success")
            return redirect(url_for("paper_detail", paper_id=paper_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        form = {"file_location": version["file_location"], "uploaded_at": iso_datetime(version["uploaded_at"]),
                "change_note": version["change_note"] or ""}
    return render_template("version_form.html", version=version, form=form)


@app.post("/papers/<int:paper_id>/versions/<int:version_no>/delete")
def version_delete(paper_id, version_no):
    try:
        with engine.begin() as conn:
            c_one(conn, "SELECT paper_id FROM paper WHERE paper_id = :pid FOR UPDATE", pid=paper_id)
            count = c_scalar(conn, "SELECT COUNT(*) FROM paper_version WHERE paper_id = :pid", pid=paper_id)
            if count <= 1:
                raise ValidationError("Every paper must keep at least one version, so its only version cannot be "
                                      "deleted. Delete the whole paper instead.")
            result = c_exec(conn, "DELETE FROM paper_version WHERE paper_id = :pid AND version_no = :vno",
                            pid=paper_id, vno=version_no)
            if result.rowcount == 0:
                raise ValidationError(f"Version {version_no} of paper #{paper_id} does not exist.")
        flash(f"Version {version_no} of paper #{paper_id} deleted.", "success")
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
    return redirect(url_for("paper_detail", paper_id=paper_id))


# =============================================================================
# REVIEWS
# =============================================================================
def review_choices():
    with engine.connect() as conn:
        papers = c_all(conn, """
            SELECT p.paper_id, p.title, p.status, c.acronym
            FROM paper p JOIN track t ON t.track_id = p.track_id
            JOIN conference c ON c.conference_id = t.conference_id
            ORDER BY p.paper_id
        """)
        reviewers = c_all(conn, """
            SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name
            FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
            ORDER BY u.surname, u.given_name, r.reviewer_id
        """)
    return {"papers": papers, "reviewers": reviewers}


@app.get("/reviews")
def reviews_list():
    reviews = fetch_all("""
        SELECT rv.review_id, rv.paper_id, p.title, rv.reviewer_id,
               u.given_name || ' ' || u.surname AS reviewer_name,
               rv.overall_score, rv.recommendation, rv.review_submission_date
        FROM review rv
        JOIN paper p    ON p.paper_id = rv.paper_id
        JOIN app_user u ON u.user_id = rv.reviewer_id
        ORDER BY rv.review_id
    """)
    return render_template("reviews_list.html", reviews=reviews)


@app.get("/reviews/<int:review_id>")
def review_detail(review_id):
    review = fetch_one("""
        SELECT rv.*, p.title, p.status, u.given_name || ' ' || u.surname AS reviewer_name
        FROM review rv
        JOIN paper p    ON p.paper_id = rv.paper_id
        JOIN app_user u ON u.user_id = rv.reviewer_id
        WHERE rv.review_id = :rid
    """, rid=review_id)
    if review is None:
        abort(404)
    return render_template("review_detail.html", review=review)


def parse_review_form(form) -> dict:
    errors: list[str] = []
    d = {
        "paper_id": get_int(form, "paper_id", "Paper", errors),
        "reviewer_id": get_int(form, "reviewer_id", "Reviewer", errors),
        "overall_score": get_int(form, "overall_score", "Overall score", errors, min_value=1, max_value=5),
        "recommendation": (form.get("recommendation") or "").strip(),
        "comments_for_authors": get_str(form, "comments_for_authors", "Comments for the authors", errors),
        "confidential_comments": (form.get("confidential_comments") or "").strip() or None,
        "review_submission_date": get_date(form, "review_submission_date", "Review submission date", errors),
    }
    if d["recommendation"] not in RECOMMENDATIONS:
        errors.append("The recommendation must be 'accept' or 'reject'.")
    if errors:
        raise ValidationError(errors)
    return d


def validate_review(conn, d: dict, review_id: int | None) -> None:
    errors: list[str] = []
    paper = c_one(conn, "SELECT paper_id, title FROM paper WHERE paper_id = :pid", pid=d["paper_id"])
    if paper is None:
        errors.append(f"Paper #{d['paper_id']} does not exist.")
    reviewer = c_one(conn, """
        SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name
        FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
        WHERE r.reviewer_id = :rid
    """, rid=d["reviewer_id"])
    if reviewer is None:
        errors.append(f"User #{d['reviewer_id']} does not have a reviewer profile.")
    if paper and reviewer:
        # Required check 1: a reviewer may not review a paper they authored
        authorship = c_one(conn, """
            SELECT author_position FROM paper_author WHERE paper_id = :pid AND author_id = :rid
        """, pid=d["paper_id"], rid=d["reviewer_id"])
        if authorship:
            errors.append(f"Self-review rejected: {reviewer['full_name']} (user #{d['reviewer_id']}) is author "
                          f"#{authorship['author_position']} of paper #{d['paper_id']} and cannot review it.")
        # at most one review per reviewer and paper (also enforced by UNIQUE constraint)
        duplicate = c_one(conn, """
            SELECT review_id FROM review
            WHERE paper_id = :pid AND reviewer_id = :rid AND review_id <> COALESCE(:review_id, -1)
        """, pid=d["paper_id"], rid=d["reviewer_id"], review_id=review_id)
        if duplicate:
            errors.append(f"{reviewer['full_name']} already submitted review #{duplicate['review_id']} for paper "
                          f"#{d['paper_id']}; a reviewer may submit at most one review per paper.")
    if errors:
        raise ValidationError(errors)


REVIEW_FIELDS = ("paper_id", "reviewer_id", "overall_score", "recommendation", "comments_for_authors",
                 "confidential_comments", "review_submission_date")


@app.route("/reviews/new", methods=["GET", "POST"])
def review_create():
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            d = parse_review_form(form)
            with engine.begin() as conn:
                validate_review(conn, d, None)
                review_id = c_scalar(conn, """
                    INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                                        comments_for_authors, confidential_comments, review_submission_date)
                    VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation,
                            :comments_for_authors, :confidential_comments, :review_submission_date)
                    RETURNING review_id
                """, **{k: d[k] for k in REVIEW_FIELDS})
            flash(f"Review #{review_id} saved.", "success")
            return redirect(url_for("review_detail", review_id=review_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        form = {"paper_id": request.args.get("paper_id", ""), "review_submission_date": date.today().isoformat(),
                "recommendation": "accept", "overall_score": "3"}
    return render_template("review_form.html", form=form, review_id=None, **review_choices())


@app.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
def review_edit(review_id):
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            d = parse_review_form(form)
            with engine.begin() as conn:
                validate_review(conn, d, review_id)
                result = c_exec(conn, """
                    UPDATE review
                    SET paper_id = :paper_id, reviewer_id = :reviewer_id, overall_score = :overall_score,
                        recommendation = :recommendation, comments_for_authors = :comments_for_authors,
                        confidential_comments = :confidential_comments,
                        review_submission_date = :review_submission_date
                    WHERE review_id = :review_id
                """, review_id=review_id, **{k: d[k] for k in REVIEW_FIELDS})
                if result.rowcount == 0:
                    raise ValidationError(f"Review #{review_id} does not exist.")
            flash(f"Review #{review_id} updated.", "success")
            return redirect(url_for("review_detail", review_id=review_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        review = fetch_one("SELECT * FROM review WHERE review_id = :rid", rid=review_id)
        if review is None:
            abort(404)
        form = {k: ("" if review[k] is None else str(review[k])) for k in REVIEW_FIELDS}
    return render_template("review_form.html", form=form, review_id=review_id, **review_choices())


@app.post("/reviews/<int:review_id>/delete")
def review_delete(review_id):
    try:
        with engine.begin() as conn:
            result = c_exec(conn, "DELETE FROM review WHERE review_id = :rid", rid=review_id)
            if result.rowcount == 0:
                raise ValidationError(f"Review #{review_id} does not exist.")
        flash(f"Review #{review_id} deleted.", "success")
        return redirect(url_for("reviews_list"))
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
        return redirect(url_for("review_detail", review_id=review_id))


# =============================================================================
# SESSIONS
# =============================================================================
def session_choices():
    with engine.connect() as conn:
        conferences = c_all(conn, """
            SELECT conference_id, acronym, start_date, end_date FROM conference ORDER BY conference_id
        """)
        reviewers = c_all(conn, """
            SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
                   COALESCE((SELECT string_agg(c.acronym, ', ' ORDER BY c.conference_id)
                             FROM conference_reviewer cr JOIN conference c ON c.conference_id = cr.conference_id
                             WHERE cr.reviewer_id = r.reviewer_id), 'no pool') AS pools
            FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
            ORDER BY u.surname, u.given_name
        """)
    return {"conferences": conferences, "reviewers": reviewers}


@app.get("/sessions")
def sessions_list():
    sessions = fetch_all("""
        SELECT s.session_id, s.title, s.session_date, s.start_time, s.end_time, s.room_label,
               c.acronym, c.city, u.given_name || ' ' || u.surname AS chair_name,
               (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS paper_count
        FROM conference_session s
        JOIN conference c ON c.conference_id = s.conference_id
        JOIN app_user u   ON u.user_id = s.chair_id
        ORDER BY s.conference_id, s.session_date, s.start_time, s.session_id
    """)
    return render_template("sessions_list.html", sessions=sessions)


@app.get("/sessions/<int:session_id>")
def session_detail(session_id):
    session = fetch_one("""
        SELECT s.*, c.acronym, c.city, u.given_name || ' ' || u.surname AS chair_name
        FROM conference_session s
        JOIN conference c ON c.conference_id = s.conference_id
        JOIN app_user u   ON u.user_id = s.chair_id
        WHERE s.session_id = :sid
    """, sid=session_id)
    if session is None:
        abort(404)
    papers = fetch_all("""
        SELECT p.paper_id, p.title, p.status, t.name AS track_name
        FROM paper p JOIN track t ON t.track_id = p.track_id
        WHERE p.session_id = :sid ORDER BY p.paper_id
    """, sid=session_id)
    candidates = fetch_all("""
        SELECT p.paper_id, p.title, p.status, p.session_id, c.acronym, t.conference_id
        FROM paper p JOIN track t ON t.track_id = p.track_id
        JOIN conference c ON c.conference_id = t.conference_id
        WHERE p.session_id IS DISTINCT FROM :sid
        ORDER BY (p.status = 'accepted' AND t.conference_id = :cid) DESC, p.paper_id
    """, sid=session_id, cid=session["conference_id"])
    return render_template("session_detail.html", session=session, papers=papers, candidates=candidates)


def parse_session_form(form) -> dict:
    errors: list[str] = []
    d = {
        "conference_id": get_int(form, "conference_id", "Conference", errors),
        "title": get_str(form, "title", "Title", errors, max_len=200),
        "session_date": get_date(form, "session_date", "Session date", errors),
        "start_time": get_time(form, "start_time", "Start time", errors),
        "end_time": get_time(form, "end_time", "End time", errors),
        "room_label": get_str(form, "room_label", "Room", errors, max_len=100),
        "chair_id": get_int(form, "chair_id", "Chair", errors),
    }
    if d["start_time"] and d["end_time"] and d["end_time"] <= d["start_time"]:
        errors.append("The session end time must be later than its start time.")
    if errors:
        raise ValidationError(errors)
    return d


def validate_session(conn, d: dict, session_id: int | None) -> None:
    errors: list[str] = []
    conf = c_one(conn, """
        SELECT conference_id, acronym, start_date, end_date FROM conference WHERE conference_id = :cid
    """, cid=d["conference_id"])
    if conf is None:
        raise ValidationError(f"Conference #{d['conference_id']} does not exist.")
    if not (conf["start_date"] <= d["session_date"] <= conf["end_date"]):
        errors.append(f"The session date must fall within {conf['acronym']} "
                      f"({conf['start_date']} to {conf['end_date']}).")
    in_pool = c_one(conn, """
        SELECT 1 FROM conference_reviewer WHERE conference_id = :cid AND reviewer_id = :chair
    """, cid=d["conference_id"], chair=d["chair_id"])
    if not in_pool:
        errors.append(f"The chair (user #{d['chair_id']}) must belong to the reviewer pool of {conf['acronym']}.")
    if session_id is not None:
        # Required check 2 when the session's conference changes
        conflicts = c_all(conn, """
            SELECT p.paper_id FROM paper p JOIN track t ON t.track_id = p.track_id
            WHERE p.session_id = :sid AND t.conference_id <> :cid ORDER BY p.paper_id
        """, sid=session_id, cid=d["conference_id"])
        if conflicts:
            ids = ", ".join(f"#{p['paper_id']}" for p in conflicts)
            errors.append(f"Invalid session assignment: moving this session to {conf['acronym']} would leave "
                          f"paper(s) {ids} from another conference in it. Unassign them first.")
    if errors:
        raise ValidationError(errors)


SESSION_FIELDS = ("conference_id", "title", "session_date", "start_time", "end_time", "room_label", "chair_id")


@app.route("/sessions/new", methods=["GET", "POST"])
def session_create():
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            d = parse_session_form(form)
            with engine.begin() as conn:
                validate_session(conn, d, None)
                session_id = c_scalar(conn, """
                    INSERT INTO conference_session (conference_id, title, session_date, start_time, end_time,
                                                    room_label, chair_id)
                    VALUES (:conference_id, :title, :session_date, :start_time, :end_time, :room_label, :chair_id)
                    RETURNING session_id
                """, **{k: d[k] for k in SESSION_FIELDS})
            flash(f"Session #{session_id} created.", "success")
            return redirect(url_for("session_detail", session_id=session_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        form = {}
    return render_template("session_form.html", form=form, session_id=None, **session_choices())


@app.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
def session_edit(session_id):
    if request.method == "POST":
        form = request.form.to_dict()
        try:
            d = parse_session_form(form)
            with engine.begin() as conn:
                validate_session(conn, d, session_id)
                result = c_exec(conn, """
                    UPDATE conference_session
                    SET conference_id = :conference_id, title = :title, session_date = :session_date,
                        start_time = :start_time, end_time = :end_time, room_label = :room_label,
                        chair_id = :chair_id
                    WHERE session_id = :sid
                """, sid=session_id, **{k: d[k] for k in SESSION_FIELDS})
                if result.rowcount == 0:
                    raise ValidationError(f"Session #{session_id} does not exist.")
            flash(f"Session #{session_id} updated.", "success")
            return redirect(url_for("session_detail", session_id=session_id))
        except (ValidationError, SQLAlchemyError) as exc:
            report_failure(exc)
    else:
        s = fetch_one("SELECT * FROM conference_session WHERE session_id = :sid", sid=session_id)
        if s is None:
            abort(404)
        form = {"conference_id": str(s["conference_id"]), "title": s["title"],
                "session_date": s["session_date"].isoformat(), "start_time": iso_time(s["start_time"]),
                "end_time": iso_time(s["end_time"]), "room_label": s["room_label"], "chair_id": str(s["chair_id"])}
    return render_template("session_form.html", form=form, session_id=session_id, **session_choices())


@app.post("/sessions/<int:session_id>/delete")
def session_delete(session_id):
    try:
        with engine.begin() as conn:
            assigned = c_scalar(conn, "SELECT COUNT(*) FROM paper WHERE session_id = :sid", sid=session_id)
            result = c_exec(conn, "DELETE FROM conference_session WHERE session_id = :sid", sid=session_id)
            if result.rowcount == 0:
                raise ValidationError(f"Session #{session_id} does not exist.")
        flash(f"Session #{session_id} deleted; {assigned} assigned paper(s) were unscheduled "
              f"(paper.session_id set to NULL by ON DELETE SET NULL).", "success")
        return redirect(url_for("sessions_list"))
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
        return redirect(url_for("session_detail", session_id=session_id))


@app.post("/sessions/<int:session_id>/assign")
def session_assign(session_id):
    errors: list[str] = []
    paper_id = get_int(request.form, "paper_id", "Paper", errors)
    try:
        if errors:
            raise ValidationError(errors)
        with engine.begin() as conn:
            session = load_session(conn, session_id)
            if session is None:
                raise ValidationError(f"Session #{session_id} does not exist.")
            paper = c_one(conn, """
                SELECT p.paper_id, p.status, p.session_id, t.name AS track_name, t.conference_id
                FROM paper p JOIN track t ON t.track_id = p.track_id
                WHERE p.paper_id = :pid
                FOR UPDATE OF p
            """, pid=paper_id)
            if paper is None:
                raise ValidationError(f"Paper #{paper_id} does not exist.")
            # Required check 2
            problems = session_assignment_errors(paper["status"], paper["conference_id"],
                                                 f"'{paper['track_name']}'", session)
            if problems:
                raise ValidationError([f"Paper #{paper_id} was NOT assigned. " + p for p in problems])
            c_exec(conn, "UPDATE paper SET session_id = :sid WHERE paper_id = :pid", sid=session_id, pid=paper_id)
        moved = f" (moved from session #{paper['session_id']})" if paper["session_id"] else ""
        flash(f"Paper #{paper_id} assigned to session #{session_id}{moved}.", "success")
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
    return redirect(url_for("session_detail", session_id=session_id))


@app.post("/sessions/<int:session_id>/unassign/<int:paper_id>")
def session_unassign(session_id, paper_id):
    try:
        with engine.begin() as conn:
            result = c_exec(conn, """
                UPDATE paper SET session_id = NULL WHERE paper_id = :pid AND session_id = :sid
            """, pid=paper_id, sid=session_id)
            if result.rowcount == 0:
                raise ValidationError(f"Paper #{paper_id} is not assigned to session #{session_id}.")
        flash(f"Paper #{paper_id} removed from session #{session_id}.", "success")
    except (ValidationError, SQLAlchemyError) as exc:
        report_failure(exc)
    return redirect(url_for("session_detail", session_id=session_id))


if __name__ == "__main__":
    app.run(debug=True)
