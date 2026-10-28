"""
Rename auth_user.username and every column that stores that username.

Keeps the same auth_user.id so integer FKs (leaves, events, notes, etc.) stay valid.
Django Admin cannot do this: username-keyed FKs have no ON UPDATE CASCADE.

Examples
--------
    python manage.py rename_username --map 2091=200036 --map 2090=200035 --dry-run
    python manage.py rename_username --map 2091=200036 --map 2090=200035 --apply
"""
from __future__ import annotations

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


FK_SQL = """
SELECT
    nsp.nspname AS table_schema,
    rel.relname AS table_name,
    con.conname AS constraint_name,
    pg_get_constraintdef(con.oid) AS definition,
    att.attname AS column_name,
    fnsp.nspname AS ref_schema,
    frel.relname AS ref_table,
    fatt.attname AS ref_column
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
JOIN pg_class frel ON frel.oid = con.confrelid
JOIN pg_namespace fnsp ON fnsp.oid = frel.relnamespace
JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS ck(attnum, ord) ON true
JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS fk(attnum, ord) ON fk.ord = ck.ord
JOIN pg_attribute att
    ON att.attrelid = con.conrelid AND att.attnum = ck.attnum
JOIN pg_attribute fatt
    ON fatt.attrelid = con.confrelid AND fatt.attnum = fk.attnum
WHERE con.contype = 'f'
  AND nsp.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
"""


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def quote_table(schema: str, table: str) -> str:
    return f"{quote_ident(schema)}.{quote_ident(table)}"


def parse_django_table(db_table: str) -> tuple[str | None, str]:
    """Return (schema_or_None, table) from Django db_table, including schema\".\"table form."""
    raw = (db_table or "").strip()
    if '"."' in raw:
        schema, table = raw.split('"."', 1)
        return schema.strip('"'), table.strip('"')
    if "." in raw and not raw.startswith('"'):
        schema, table = raw.split(".", 1)
        return schema, table
    return None, raw.strip('"')


class Command(BaseCommand):
    help = (
        "Rename employee login (auth_user.username) and cascade to username-keyed "
        "FKs, keeping the same user id. Use --dry-run first, then --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--map",
            action="append",
            dest="maps",
            metavar="OLD=NEW",
            help="Username mapping, e.g. 2091=200036. Repeat for each user.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Perform the rename. Required for any write.",
        )

    def handle(self, *args, **options):
        maps = options.get("maps") or []
        dry_run = bool(options.get("dry_run"))
        apply = bool(options.get("apply"))
        if apply and dry_run:
            raise CommandError("Use either --dry-run or --apply, not both.")
        if not apply:
            dry_run = True
        if not maps:
            raise CommandError("Pass at least one --map OLD=NEW")

        renames = self._parse_maps(maps)
        self._preflight(renames)

        auth_user = self._auth_user_key()
        fk_rows = self._fk_rows()
        update_keys = self._columns_to_update(fk_rows, auth_user)
        update_keys |= self._django_username_columns(auth_user)
        fks_to_touch = self._fks_for_columns(fk_rows, update_keys)

        self.stdout.write("Users:")
        for old, new in renames:
            user = User.objects.get(username=old)
            self.stdout.write(f"  id={user.pk}  {old} -> {new}  email={user.email!r}")

        self.stdout.write("\nColumns that store username:")
        planned = []
        for schema, table, column in sorted(update_keys):
            for old, new in renames:
                count = self._count_col(schema, table, column, old)
                if count:
                    planned.append((schema, table, column, old, new, count))
                    self.stdout.write(
                        f"  {quote_table(schema, table)}.{quote_ident(column)}: "
                        f"{count} row(s) {old} -> {new}"
                    )
        if not planned:
            self.stdout.write("  (no matching rows besides the auth_user username itself)")

        self.stdout.write(f"\nForeign keys to defer during rename: {len(fks_to_touch)}")
        for fk in fks_to_touch:
            self.stdout.write(
                f"  {quote_table(fk['table_schema'], fk['table_name'])} "
                f"{fk['constraint_name']}"
            )

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                "\n[dry-run] No changes written. Re-run with --apply to rename."
            ))
            return

        with transaction.atomic():
            with connection.cursor() as cur:
                for old, _new in renames:
                    cur.execute(
                        "SELECT id FROM auth_user WHERE username = %s FOR UPDATE",
                        [old],
                    )
                    if not cur.fetchone():
                        raise CommandError(f"Lost lock on {old}; aborting.")

                # Postgres cannot ADD CONSTRAINT after UPDATE on the same table
                # in one transaction (pending trigger events). Defer FKs instead.
                for fk in fks_to_touch:
                    cur.execute(
                        f"ALTER TABLE {quote_table(fk['table_schema'], fk['table_name'])} "
                        f"ALTER CONSTRAINT {quote_ident(fk['constraint_name'])} "
                        f"DEFERRABLE"
                    )
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                self.stdout.write(f"Deferred {len(fks_to_touch)} foreign key(s)")

                for old, new in renames:
                    cur.execute(
                        "UPDATE auth_user SET username = %s WHERE username = %s",
                        [new, old],
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"auth_user: {old} -> {new} ({cur.rowcount} row)")
                    )

                for schema, table, column, old, new, _count in planned:
                    if (schema, table, column) == auth_user:
                        continue
                    cur.execute(
                        f"UPDATE {quote_table(schema, table)} "
                        f"SET {quote_ident(column)} = %s "
                        f"WHERE {quote_ident(column)} = %s",
                        [new, old],
                    )
                    if cur.rowcount:
                        self.stdout.write(
                            f"Updated {quote_table(schema, table)}.{quote_ident(column)} "
                            f"({cur.rowcount})"
                        )

                leftover = []
                for schema, table, column in sorted(update_keys):
                    for old, _new in renames:
                        if (schema, table, column) == auth_user:
                            continue
                        remaining = self._count_col(schema, table, column, old, cursor=cur)
                        if remaining:
                            leftover.append(
                                f"{quote_table(schema, table)}.{quote_ident(column)} "
                                f"still has {remaining} x {old}"
                            )
                if leftover:
                    raise CommandError(
                        "Aborting; leftover references would fail FK checks:\n  "
                        + "\n  ".join(leftover)
                    )

        usernames = [new for _old, new in renames] + [old for old, _new in renames]
        final = list(
            User.objects.filter(username__in=usernames).values("id", "username", "email")
        )
        self.stdout.write(self.style.SUCCESS(f"\nDone. Users now: {final}"))

    def _parse_maps(self, maps: list[str]) -> list[tuple[str, str]]:
        renames = []
        seen_old = set()
        seen_new = set()
        for item in maps:
            if "=" not in item:
                raise CommandError(f"Invalid --map {item!r}; expected OLD=NEW")
            old, new = item.split("=", 1)
            old, new = old.strip(), new.strip()
            if not old or not new:
                raise CommandError(f"Invalid --map {item!r}")
            if old == new:
                raise CommandError(f"{old} already equals the new username")
            if old in seen_old or new in seen_new or old in seen_new or new in seen_old:
                raise CommandError(f"Overlapping rename involving {old} / {new}")
            seen_old.add(old)
            seen_new.add(new)
            renames.append((old, new))
        return renames

    def _preflight(self, renames: list[tuple[str, str]]) -> None:
        for old, new in renames:
            if not User.objects.filter(username=old).exists():
                raise CommandError(f"Old username {old} does not exist")
            if User.objects.filter(username=new).exists():
                raise CommandError(f"Target username {new} already exists; refusing to rename")

    def _auth_user_key(self) -> tuple[str, str, str]:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT n.nspname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = 'auth_user' AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                ORDER BY CASE WHEN n.nspname = 'login_details' THEN 0 ELSE 1 END
                LIMIT 1
                """
            )
            row = cur.fetchone()
        schema = row[0] if row else "login_details"
        return (schema, "auth_user", "username")

    def _columns_to_update(self, fk_rows: list[dict], auth_user: tuple[str, str, str]):
        """auth_user.username plus every column that FKs to a username-keyed unique col."""
        cols = {auth_user}
        changed = True
        while changed:
            changed = False
            for row in fk_rows:
                dst = (row["ref_schema"], row["ref_table"], row["ref_column"])
                src = (row["table_schema"], row["table_name"], row["column_name"])
                if dst in cols and src not in cols:
                    cols.add(src)
                    changed = True
        return cols

    def _django_username_columns(self, auth_user: tuple[str, str, str]):
        """Extra username columns from models, resolved to a real schema.table if present."""
        keys = set()
        for model in apps.get_models():
            if model._meta.proxy:
                continue
            schema, table = parse_django_table(model._meta.db_table)
            if not schema:
                schema = self._visible_schema(table) or auth_user[0]
            if not self._relation_exists(schema, table):
                continue
            for field in model._meta.concrete_fields:
                rel = getattr(field, "remote_field", None)
                if rel is None or not getattr(field, "column", None):
                    continue
                target = rel.model
                to_field = getattr(rel, "field_name", None)
                if target is User and to_field == "username":
                    keys.add((schema, table, field.column))
                elif (
                    getattr(target, "__name__", "") == "Profile"
                    and to_field == "Employee_id"
                ):
                    keys.add((schema, table, field.column))
        return keys

    def _visible_schema(self, table: str) -> str | None:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT n.nspname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = %s
                  AND n.nspname NOT IN ('pg_catalog', 'pg_toast', 'information_schema')
                  AND pg_table_is_visible(c.oid)
                LIMIT 1
                """,
                [table],
            )
            row = cur.fetchone()
        return row[0] if row else None

    def _relation_exists(self, schema: str, table: str) -> bool:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND c.relname = %s
                LIMIT 1
                """,
                [schema, table],
            )
            return cur.fetchone() is not None

    def _fk_rows(self) -> list[dict]:
        with connection.cursor() as cur:
            cur.execute(FK_SQL)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _fks_for_columns(self, fk_rows: list[dict], update_keys: set[tuple[str, str, str]]) -> list[dict]:
        """Unique FKs whose source or referenced column is being updated."""
        by_name: dict[tuple[str, str, str], dict] = {}
        for row in fk_rows:
            src = (row["table_schema"], row["table_name"], row["column_name"])
            dst = (row["ref_schema"], row["ref_table"], row["ref_column"])
            if src in update_keys or dst in update_keys:
                key = (row["table_schema"], row["table_name"], row["constraint_name"])
                by_name[key] = row
        return list(by_name.values())

    def _count_col(self, schema, table, column, value, cursor=None) -> int:
        sql = (
            f"SELECT COUNT(*) FROM {quote_table(schema, table)} "
            f"WHERE {quote_ident(column)} = %s"
        )
        if cursor is not None:
            cursor.execute(sql, [value])
            return int(cursor.fetchone()[0])
        with connection.cursor() as cur:
            cur.execute(sql, [value])
            return int(cur.fetchone()[0])
