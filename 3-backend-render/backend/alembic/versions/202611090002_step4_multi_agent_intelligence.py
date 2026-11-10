"""Step 4 Multi-Agent Intelligence System schema extensions.

Revision ID: 202611090002
Revises: 
Create Date: 2026-11-09 22:18:00.000000
"""

from pathlib import Path
from alembic import op

revision = "202611090002"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    step4_sql_path = (
        repo_root
        / "supabase"
        / "migrations"
        / "20261109000002_nexus_media_ai_multi_agent_system.sql"
    )
    if step4_sql_path.exists():
        op.execute(step4_sql_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.agent_execution_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS public.workflow_runs CASCADE;")
