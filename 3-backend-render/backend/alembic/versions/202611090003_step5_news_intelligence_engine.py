"""Step 5 News Intelligence Engine schema extensions.

Revision ID: 202611090003
Revises: 202611090002
Create Date: 2026-11-09 22:57:00.000000
"""

from pathlib import Path
from alembic import op

revision = "202611090003"
down_revision = "202611090002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    step5_sql_path = (
        repo_root
        / "supabase"
        / "migrations"
        / "20261109000003_nexus_media_ai_news_intelligence_engine.sql"
    )
    if step5_sql_path.exists():
        op.execute(step5_sql_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.source_fetch_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS public.collection_runs CASCADE;")
    op.execute("DROP TABLE IF EXISTS public.news_classifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS public.trend_scores CASCADE;")
    op.execute("DROP TABLE IF EXISTS public.story_clusters CASCADE;")
