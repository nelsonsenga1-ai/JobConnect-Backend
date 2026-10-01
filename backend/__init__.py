from flask import Blueprint, jsonify, request
from datetime import datetime
from uuid import uuid4

from backend.auth import hash_password, verify_password
from backend.database import get_connection

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    first_name = (data.get("firstName") or "").strip()
    last_name = (data.get("lastName") or "").strip()
    role = (data.get("role") or "jobseeker").strip()

    if not email or not password or not first_name or not last_name:
        return jsonify({"error": "Missing required user fields."}), 400

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return jsonify({"error": "A user with this email already exists."}), 409

        user_id = str(uuid4())
        profile = {
            "organizationName": data.get("organizationName") or "",
            "title": data.get("title") or "",
            "location": data.get("location") or "",
            "summary": data.get("summary") or "",
            "skills": data.get("skills") or "",
            "education": data.get("education") or "",
            "experience": data.get("experience") or "",
        }

        conn.execute(
            """
            INSERT INTO users (id, first_name, last_name, email, role, password_hash, phone, profile, organization_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                first_name,
                last_name,
                email,
                role,
                hash_password(password),
                (data.get("phone") or "").strip(),
                str(profile),
                bool(data.get("organizationVerified", False)),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    return jsonify({"message": "Account created successfully.", "role": role}), 201


@api_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if not user or not verify_password(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials."}), 401

        user_data = {
            "id": user["id"],
            "firstName": user["first_name"],
            "lastName": user["last_name"],
            "email": user["email"],
            "role": user["role"],
            "phone": user["phone"],
            "organizationVerified": bool(user["organization_verified"]),
            "profile": user["profile"],
        }

    return jsonify({"user": user_data, "message": "Login successful."})


@api_bp.get("/users")
def get_users():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, first_name, last_name, email, role, phone, organization_verified, profile FROM users ORDER BY created_at DESC"
        ).fetchall()
    return jsonify({"users": [dict(row) for row in rows]})


@api_bp.get("/jobs")
def get_jobs():
    with get_connection() as conn:
        jobs = conn.execute(
            "SELECT * FROM jobs WHERE status = 'published' ORDER BY created_at DESC"
        ).fetchall()

    return jsonify({"jobs": [dict(job) for job in jobs]})


@api_bp.post("/jobs")
def create_job():
    data = request.get_json(silent=True) or {}
    user_email = (data.get("organizationEmail") or "").strip().lower()
    role = data.get("role") or "organization"

    if role != "organization":
        return jsonify({"error": "Only organizations can create jobs."}), 403

    if not user_email:
        return jsonify({"error": "Organization email is required."}), 400

    with get_connection() as conn:
        org = conn.execute("SELECT * FROM users WHERE email = ? AND role = 'organization'", (user_email,)).fetchone()
        if not org:
            return jsonify({"error": "Organization account not found."}), 404

        job_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO jobs (
                id, organization_id, organization_email, title, company, location,
                salary, job_type, description, requirements, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                org["id"],
                user_email,
                (data.get("title") or "").strip(),
                (data.get("company") or org["first_name"] + " " + org["last_name"]).strip(),
                (data.get("location") or "Remote").strip(),
                (data.get("salary") or "Competitive").strip(),
                (data.get("jobType") or "Full-time").strip(),
                (data.get("description") or "").strip(),
                (data.get("requirements") or "").strip(),
                "published",
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    return jsonify({"message": "Job posted successfully.", "jobId": job_id}), 201


@api_bp.post("/applications")
def create_application():
    data = request.get_json(silent=True) or {}
    job_id = (data.get("jobId") or "").strip()
    applicant_email = (data.get("applicantEmail") or "").strip().lower()

    if not job_id or not applicant_email:
        return jsonify({"error": "Job ID and applicant email are required."}), 400

    with get_connection() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return jsonify({"error": "Job not found."}), 404

        exists = conn.execute(
            "SELECT id FROM applications WHERE job_id = ? AND applicant_email = ?",
            (job_id, applicant_email),
        ).fetchone()
        if exists:
            return jsonify({"error": "You have already applied for this job."}), 409

        app_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO applications (id, job_id, applicant_email, applicant_name, status, current_stage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app_id,
                job_id,
                applicant_email,
                (data.get("applicantName") or applicant_email).strip(),
                "submitted",
                "Submitted",
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    return jsonify({"message": "Application submitted successfully.", "applicationId": app_id}), 201


@api_bp.get("/applications")
def get_applications():
    email = (request.args.get("email") or "").strip().lower()
    with get_connection() as conn:
        if email:
            rows = conn.execute(
                "SELECT * FROM applications WHERE applicant_email = ? ORDER BY created_at DESC",
                (email,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()

    return jsonify({"applications": [dict(row) for row in rows]})


@api_bp.post("/applications/<application_id>/assessment")
def submit_assessment(application_id):
    data = request.get_json(silent=True) or {}
    score = int(data.get("score", 0))
    answers = data.get("answers") or []

    with get_connection() as conn:
        app = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if not app:
            return jsonify({"error": "Application not found."}), 404

        conn.execute(
            """
            INSERT INTO assessments (id, application_id, score, answers, submitted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                application_id,
                score,
                str(answers),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.execute(
            "UPDATE applications SET psychometric_score = ?, status = 'testing', current_stage = 'Testing' WHERE id = ?",
            (score, application_id),
        )
        conn.commit()

    return jsonify({"message": "Assessment submitted successfully.", "score": score})


@api_bp.get("/notifications")
def get_notifications():
    email = (request.args.get("email") or "").strip().lower()
    with get_connection() as conn:
        if email:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE email = ? ORDER BY created_at DESC",
                (email,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC").fetchall()

    return jsonify({"notifications": [dict(row) for row in rows]})


@api_bp.post("/notifications")
def create_notification():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    message = (data.get("message") or "").strip()
    if not email or not message:
        return jsonify({"error": "Email and message are required."}), 400

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (id, email, message, type, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), email, message, data.get("type", "info"), datetime.utcnow().isoformat()),
        )
        conn.commit()

    return jsonify({"message": "Notification created."}), 201
