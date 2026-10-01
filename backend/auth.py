from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "jobconnect.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT UNIQUE,
                role TEXT,
                password_hash TEXT,
                phone TEXT,
                profile TEXT,
                organization_verified INTEGER DEFAULT 0,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                organization_email TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                job_type TEXT,
                description TEXT,
                requirements TEXT,
                status TEXT DEFAULT 'published',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                applicant_email TEXT,
                applicant_name TEXT,
                status TEXT,
                current_stage TEXT,
                psychometric_score INTEGER,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                application_id TEXT,
                score INTEGER,
                answers TEXT,
                submitted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                email TEXT,
                message TEXT,
                type TEXT,
                created_at TEXT
            );
            """
        )
        conn.commit()


def seed_demo_data():
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (id, first_name, last_name, email, role, password_hash, phone, profile, organization_verified, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "org-demo-id",
                    "Nexa",
                    "Labs",
                    "org@jobconnect.com",
                    "organization",
                    "$2b$12$Lq2P6RrR5jd1rHML6oE1rO0K0J24x8PF6S1t0QeNAX3BKMz3J9I8m",
                    "+1234567890",
                    str({"organizationName": "Nexa Labs", "location": "Remote"}),
                    1,
                    "2026-10-01T00:00:00",
                ),
            )

        if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO jobs (id, organization_id, organization_email, title, company, location, salary, job_type, description, requirements, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "job-demo-id",
                    "org-demo-id",
                    "org@jobconnect.com",
                    "Senior Product Designer",
                    "Nexa Labs",
                    "Lagos, Nigeria",
                    "$120,000",
                    "Full-time",
                    "Design user-facing experiences for a hiring platform and work closely with product and engineering teams.",
                    "Figma, UX research, product thinking, prototyping",
                    "published",
                    "2026-10-01T00:00:00",
                )
            )

        conn.commit()
