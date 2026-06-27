"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("qualification_level", sa.String(), nullable=True),
        sa.Column("qualification_fields", JSON(), nullable=True),
        sa.Column("qualification_percentage", sa.Float(), nullable=True),
        sa.Column("exams_cleared", JSON(), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("experience_domain", sa.String(), nullable=True),
        sa.Column("is_pwd", sa.Boolean(), default=False),
        sa.Column("is_ex_serviceman", sa.Boolean(), default=False),
        sa.Column("physical", JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_job_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("organization", sa.String(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("apply_url", sa.String(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(), default="pending_extraction"),
        sa.Column("criteria", JSON(), nullable=True),
        sa.Column("r2_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_content_hash", "jobs", ["content_hash"])
    op.create_unique_constraint("uq_jobs_source_dedup", "jobs", ["source_name", "source_job_id"])
    op.create_index(
        "ix_jobs_status_published",
        "jobs",
        ["status", "published_at"],
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "scraper_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("ran_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("jobs_found", sa.Integer(), default=0),
        sa.Column("jobs_new", sa.Integer(), default=0),
        sa.Column("jobs_extracted", sa.Integer(), default=0),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("scraper_runs")
    op.drop_table("jobs")
    op.drop_table("users")
