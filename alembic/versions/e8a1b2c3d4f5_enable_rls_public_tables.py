"""enable RLS on public tables with anon read-only policies

Revision ID: e8a1b2c3d4f5
Revises: d7a3b1c9e4f2
Create Date: 2026-04-07 12:00:00.000000

Security fix for Supabase advisor `rls_disabled_in_public`.

The web app connects via direct Postgres (DATABASE_URL / Supavisor) using
the database role, which bypasses RLS. The risk is the project's anon API
key, which goes through PostgREST and DOES respect RLS. With RLS disabled,
the anon key grants full CRUD on every public table.

This migration:
  1. Enables RLS on every public table.
  2. Grants anon SELECT-only on tables that legitimately back the public
     directory site (`stores`, `store_categories`, `store_external_refs`,
     `online_presences`, `city_descriptions`).
  3. Leaves internal tables (`alembic_version`, `validation_logs`) with
     RLS enabled and NO policies, which denies all PostgREST access.
     Direct Postgres connections (Alembic, app) are unaffected.

No INSERT/UPDATE/DELETE policies are created. Admin writes happen via
direct Postgres connection or service role key, both of which bypass RLS.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e8a1b2c3d4f5"
down_revision: Union[str, Sequence[str], None] = "c5e1a9f4b2d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PUBLIC_READ_TABLES = (
    "stores",
    "store_categories",
    "store_external_refs",
    "online_presences",
    "city_descriptions",
)

INTERNAL_TABLES = (
    "alembic_version",
    "validation_logs",
)


def upgrade() -> None:
    """Enable RLS and create anon SELECT policies for public-read tables."""
    for table in PUBLIC_READ_TABLES + INTERNAL_TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;')

    for table in PUBLIC_READ_TABLES:
        policy = f"anon_select_{table}"
        op.execute(
            f'DROP POLICY IF EXISTS "{policy}" ON public."{table}";'
        )
        op.execute(
            f'CREATE POLICY "{policy}" ON public."{table}" '
            f"FOR SELECT TO anon USING (true);"
        )
        # Mirror for authenticated users so future auth flows still read.
        auth_policy = f"authenticated_select_{table}"
        op.execute(
            f'DROP POLICY IF EXISTS "{auth_policy}" ON public."{table}";'
        )
        op.execute(
            f'CREATE POLICY "{auth_policy}" ON public."{table}" '
            f"FOR SELECT TO authenticated USING (true);"
        )


def downgrade() -> None:
    """Drop policies and disable RLS, restoring prior (insecure) state."""
    for table in PUBLIC_READ_TABLES:
        op.execute(
            f'DROP POLICY IF EXISTS "anon_select_{table}" ON public."{table}";'
        )
        op.execute(
            f'DROP POLICY IF EXISTS "authenticated_select_{table}" '
            f'ON public."{table}";'
        )

    for table in PUBLIC_READ_TABLES + INTERNAL_TABLES:
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;')
