from app.db.base import Base
from app.db.session import engine
from app.models import application  # noqa: F401
from app.models import canonical_job  # noqa: F401
from app.models import collection_run  # noqa: F401
from app.models import cover_letter  # noqa: F401
from app.models import job_skill  # noqa: F401
from app.models import job_source_map  # noqa: F401
from app.models import raw_job  # noqa: F401
from app.models import resume_version  # noqa: F401
from app.models import user  # noqa: F401
from app.models import user_profile  # noqa: F401
from app.services.collectors.company_registry import TARGET_COMPANIES


SQLITE_RAW_JOB_COLUMNS = {
    "owner_user_id": "INTEGER REFERENCES users(id) ON DELETE CASCADE",
    "is_user_added": "BOOLEAN DEFAULT 0 NOT NULL",
    "source_board_token": "VARCHAR(255)",
    "first_seen_at": "DATETIME",
    "last_seen_at": "DATETIME",
    "is_active": "BOOLEAN DEFAULT 1 NOT NULL",
    "missed_collection_count": "INTEGER DEFAULT 0 NOT NULL",
    "closed_at": "DATETIME",
    "normalized_company": "VARCHAR(255)",
    "normalized_title": "VARCHAR(500)",
    "normalized_location": "VARCHAR(500)",
    "country": "VARCHAR(100)",
    "state": "VARCHAR(100)",
    "is_us_based": "BOOLEAN DEFAULT 0 NOT NULL",
    "work_mode": "VARCHAR(50)",
    "seniority": "VARCHAR(50)",
    "entry_fit_level": "VARCHAR(50)",
    "entry_fit_score": "INTEGER DEFAULT 0 NOT NULL",
    "entry_fit_reasons": "TEXT",
    "required_experience_years": "INTEGER",
    "career_eligible": "BOOLEAN DEFAULT 1 NOT NULL",
    "career_eligibility_reason": "TEXT",
    "role_category": "VARCHAR(100)",
    "target_relevance_score": "INTEGER DEFAULT 0 NOT NULL",
}

SQLITE_APPLICATION_COLUMNS = {
    "user_id": "INTEGER DEFAULT 1 NOT NULL",
    "resume_version": "VARCHAR(255)",
    "cover_letter_version": "VARCHAR(255)",
    "resume_version_id": "INTEGER REFERENCES resume_versions(id) ON DELETE SET NULL",
    "cover_letter_id": "INTEGER REFERENCES cover_letters(id) ON DELETE SET NULL",
}

SQLITE_USER_PROFILE_COLUMNS = {
    "user_id": "INTEGER DEFAULT 1 NOT NULL",
    "source_resume_version_id": "INTEGER",
    "manual_skills_json": "TEXT",
    "work_experience_json": "TEXT",
    "education_json": "TEXT",
    "domain_experience_json": "TEXT",
}

SQLITE_JOB_SKILL_COLUMNS = {
    "requirement_level": "VARCHAR(50) DEFAULT 'mentioned' NOT NULL",
    "evidence_snippet": "TEXT",
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.url.get_backend_name() == "sqlite":
        ensure_default_user()
        ensure_sqlite_raw_job_columns()
        backfill_sqlite_job_lifecycle()
        backfill_sqlite_source_board_tokens()
        ensure_sqlite_lifecycle_indexes()
        ensure_sqlite_job_skill_columns()
        ensure_sqlite_application_columns()
        migrate_sqlite_application_document_ids()
        ensure_sqlite_user_profile_columns()


def ensure_sqlite_raw_job_columns() -> None:
    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(raw_jobs)")
        }

        for column_name, column_type in SQLITE_RAW_JOB_COLUMNS.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE raw_jobs ADD COLUMN {column_name} {column_type}"
                )


def backfill_sqlite_job_lifecycle() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            UPDATE raw_jobs
            SET first_seen_at = COALESCE(first_seen_at, date_collected),
                last_seen_at = COALESCE(last_seen_at, date_collected),
                is_active = COALESCE(is_active, 1),
                missed_collection_count = COALESCE(missed_collection_count, 0)
            """
        )


def backfill_sqlite_source_board_tokens() -> None:
    with engine.begin() as connection:
        for company in TARGET_COMPANIES:
            connection.exec_driver_sql(
                """
                UPDATE raw_jobs
                SET source_board_token = ?
                WHERE source_board_token IS NULL
                  AND source = ?
                  AND (
                    LOWER(TRIM(COALESCE(normalized_company, ''))) = LOWER(?)
                    OR LOWER(TRIM(COALESCE(company, ''))) LIKE LOWER(?) || '%'
                  )
                """,
                (
                    company["board_token"],
                    company["source"],
                    company["name"],
                    company["name"],
                ),
            )


def ensure_sqlite_lifecycle_indexes() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_raw_jobs_source_board_token "
            "ON raw_jobs (source_board_token)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_raw_jobs_is_active ON raw_jobs (is_active)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_raw_jobs_last_seen_at ON raw_jobs (last_seen_at)"
        )


def ensure_default_user() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO users (id, email, display_name, created_at, updated_at)
            SELECT 1, 'default@local', 'Default User', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 1)
            """
        )


def ensure_sqlite_job_skill_columns() -> None:
    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(job_skills)")
        }

        for column_name, column_type in SQLITE_JOB_SKILL_COLUMNS.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE job_skills ADD COLUMN {column_name} {column_type}"
                )


def ensure_sqlite_application_columns() -> None:
    with engine.begin() as connection:
        existing_tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        if "applications" not in existing_tables:
            return

        existing_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(applications)")
        }

        for column_name, column_type in SQLITE_APPLICATION_COLUMNS.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE applications ADD COLUMN {column_name} {column_type}"
                )


def migrate_sqlite_application_document_ids() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            UPDATE applications
            SET resume_version_id = (
                SELECT resume_versions.id
                FROM resume_versions
                WHERE resume_versions.user_id = applications.user_id
                  AND resume_versions.name = applications.resume_version
                LIMIT 1
            )
            WHERE resume_version_id IS NULL
              AND resume_version IS NOT NULL
            """
        )
        connection.exec_driver_sql(
            """
            UPDATE applications
            SET cover_letter_id = (
                SELECT cover_letters.id
                FROM cover_letters
                WHERE cover_letters.user_id = applications.user_id
                  AND cover_letters.name = applications.cover_letter_version
                  AND cover_letters.raw_job_id = applications.raw_job_id
                LIMIT 1
            )
            WHERE cover_letter_id IS NULL
              AND cover_letter_version IS NOT NULL
            """
        )


def ensure_sqlite_user_profile_columns() -> None:
    with engine.begin() as connection:
        existing_tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        if "user_profiles" not in existing_tables:
            return

        existing_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(user_profiles)")
        }

        for column_name, column_type in SQLITE_USER_PROFILE_COLUMNS.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE user_profiles ADD COLUMN {column_name} {column_type}"
                )
