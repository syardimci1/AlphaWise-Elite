"""Initial schema — users, portfolios, reports, agent_decisions, audit_log

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-15

CONSTITUTION.md uyumu:
  - Madde 12.3: audit_log WORM — UPDATE/DELETE trigger ile engellenir
  - Madde 16.3: TimescaleDB extension + hypertable-ready
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # Extensions
    # -----------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')  # gen_random_uuid()

    # -----------------------------------------------------------------
    # users
    # -----------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "risk_profile",
            sa.String(length=32),
            nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # -----------------------------------------------------------------
    # portfolios  (ABD/BIST ayrımı için market alanı)
    # -----------------------------------------------------------------
    op.create_table(
        "portfolios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("cost_basis", sa.Numeric(20, 8), nullable=False),
        sa.Column("market", sa.String(length=8), nullable=False),  # 'US' | 'BIST'
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("market IN ('US','BIST')", name="ck_portfolios_market"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])
    op.create_index(
        "ix_portfolios_user_ticker_market",
        "portfolios",
        ["user_id", "ticker", "market"],
    )

    # -----------------------------------------------------------------
    # reports
    # -----------------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("confluence_score", sa.SmallInteger(), nullable=False),
        sa.Column("decision_code", sa.String(length=32), nullable=False),
        sa.Column("report_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "confluence_score BETWEEN 0 AND 100",
            name="ck_reports_confluence_range",
        ),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_ticker", "reports", ["ticker"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])

    # -----------------------------------------------------------------
    # agent_decisions
    # -----------------------------------------------------------------
    op.create_table(
        "agent_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_role", sa.String(length=16), nullable=False),  # TAA|FAA|RAA|SAA|MAA
        sa.Column("tier_used", sa.SmallInteger(), nullable=False),      # 1..4 (Madde 3.4 cascade_tier)
        sa.Column("signal", sa.String(length=16), nullable=False),      # EKLE|TUT|BEKLE|DİKKAT ET
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),      # 0.000..1.000
        sa.Column("model_used", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_agent_decisions_confidence_range",
        ),
        sa.CheckConstraint(
            "tier_used BETWEEN 1 AND 4",
            name="ck_agent_decisions_tier_range",
        ),
    )
    op.create_index("ix_agent_decisions_report_id", "agent_decisions", ["report_id"])
    op.create_index("ix_agent_decisions_agent_role", "agent_decisions", ["agent_role"])

    # -----------------------------------------------------------------
    # audit_log  (WORM — CONSTITUTION Madde 12.3)
    # -----------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # WORM trigger — UPDATE ve DELETE'i her koşulda engelle
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_worm_guard()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_log is WORM (CONSTITUTION 12.3): % not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_update
        BEFORE UPDATE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_worm_guard();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_delete
        BEFORE DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_worm_guard();
        """
    )

    # Hypertable — audit_log yüksek hacimli, zaman-serisi ✓
    op.execute(
        """
        SELECT create_hypertable(
            'audit_log', 'created_at',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );
        """
    )


def downgrade() -> None:
    # Trigger'ları bırakmak için önce audit_log'u drop et
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log;")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS audit_log_worm_guard();")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_event_type", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_agent_decisions_agent_role", table_name="agent_decisions")
    op.drop_index("ix_agent_decisions_report_id", table_name="agent_decisions")
    op.drop_table("agent_decisions")

    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_ticker", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")

    op.drop_index("ix_portfolios_user_ticker_market", table_name="portfolios")
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
