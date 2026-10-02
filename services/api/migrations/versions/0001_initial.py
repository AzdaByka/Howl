"""Create initial Howl API schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "communities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_communities"),
    )
    op.create_index("ix_communities_owner_id", "communities", ["owner_id"], unique=False)

    op.create_table(
        "oauth_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_oauth_accounts"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_accounts_provider"),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=False)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)

    op.create_table(
        "community_members",
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_id", "user_id", name="pk_community_members"),
    )

    op.create_table(
        "voice_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_voice_channels"),
    )
    op.create_index(
        "ix_voice_channels_community_id",
        "voice_channels",
        ["community_id"],
        unique=False,
    )

    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_invites"),
        sa.UniqueConstraint("token_hash", name="uq_invites_token_hash"),
    )
    op.create_index("ix_invites_community_id", "invites", ["community_id"], unique=False)
    op.create_index("ix_invites_created_by", "invites", ["created_by"], unique=False)
    op.create_index("ix_invites_token_hash", "invites", ["token_hash"], unique=False)
    op.create_index("ix_invites_expires_at", "invites", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_table("invites")
    op.drop_table("voice_channels")
    op.drop_table("community_members")
    op.drop_table("sessions")
    op.drop_table("oauth_accounts")
    op.drop_table("communities")
    op.drop_table("users")
