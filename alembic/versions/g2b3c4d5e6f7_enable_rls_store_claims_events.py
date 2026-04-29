"""enable RLS on store_claims and store_events (deny PostgREST access)

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-28 00:00:00.000000

Security fix for Supabase advisor `rls_disabled_in_public` ERRORs on
`store_claims` and `store_events`. Both tables existed without RLS,
which means the project anon key (which goes through PostgREST and
DOES respect RLS) had unrestricted CRUD on user-submitted claim PII
and on premium event content.

Access pattern audit (2026-04-28):

  * `store_claims`: written from `web/lib/claim-actions.ts::submitClaim`
    server action and read by ad-hoc admin SQL. The server action uses
    `web/lib/db.ts`, which connects via DATABASE_URL (direct Postgres /
    Supavisor) using the database role. That path bypasses RLS entirely.
    No anon-key code path reads or writes this table.

  * `store_events`: read in `web/lib/queries.ts` (server component path,
    same DATABASE_URL connection) and rendered by
    `web/app/store/[slug]/page.tsx`. Writes are admin-only (no
    application write path exists today). Same direct-Postgres story:
    server reads bypass RLS.

Migration policy choice: enable RLS with NO policies, mirroring the
`INTERNAL_TABLES` pattern from revision e8a1b2c3d4f5. Anon and
authenticated PostgREST access is denied; direct-Postgres connections
(Alembic, app db role, service role) are unaffected.

If a future feature needs anon SELECT on `store_events` (e.g. a static
JSON dump exposed to the browser), add a narrow policy in a follow-up
migration — do not weaken this one.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "g2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = (
    "store_claims",
    "store_events",
)


def upgrade() -> None:
    """Enable RLS on store_claims and store_events. No policies = deny PostgREST."""
    for table in RLS_TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    """Disable RLS, restoring the prior (insecure) state."""
    for table in RLS_TABLES:
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;')
