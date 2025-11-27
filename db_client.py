#!/usr/bin/env python3
"""Simple command-line database client using SQLite.

This script provides a minimal interactive shell for executing SQL
statements against an SQLite database. It supports executing a single
statement, running a script file, or entering an interactive prompt.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


def connect_database(db_path: str) -> sqlite3.Connection:
    """Create and return an SQLite connection.

    Parameters
    ----------
    db_path:
        Path to the SQLite database. Use ``:memory:`` for an in-memory
        database.
    """
    return sqlite3.connect(db_path)


def format_rows(columns: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """Format query results into a padded table string."""
    data: List[List[str]] = [list(map(_format_cell, row)) for row in rows]
    col_widths = [len(col) for col in columns]
    for row in data:
        for idx, value in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(value))

    header = " | ".join(col.ljust(col_widths[idx]) for idx, col in enumerate(columns))
    separator = "-+-".join("-" * width for width in col_widths)
    body = "\n".join(
        " | ".join(value.ljust(col_widths[idx]) for idx, value in enumerate(row))
        for row in data
    )

    return "\n".join(filter(None, [header, separator, body]))


def _format_cell(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def execute_statement(cursor: sqlite3.Cursor, sql: str) -> None:
    """Execute a single SQL statement and print the result."""
    try:
        cursor.execute(sql)
    except sqlite3.DatabaseError as exc:
        print(f"Error: {exc}")
        return

    if cursor.description:
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        output = format_rows(columns, rows)
        print(output)
    else:
        affected = cursor.rowcount
        print(f"OK ({affected} rows affected)")


def execute_script(cursor: sqlite3.Cursor, path: Path) -> None:
    """Run all statements from a file."""
    sql = path.read_text(encoding="utf-8")
    try:
        cursor.executescript(sql)
    except sqlite3.DatabaseError as exc:
        print(f"Error executing script {path}: {exc}")
        return
    print(f"Executed script: {path}")


def interactive_shell(cursor: sqlite3.Cursor) -> None:
    """Launch an interactive prompt for entering SQL statements."""
    print("Enter SQL statements terminated by a semicolon. Type 'exit' or 'quit' to leave.")
    buffer: List[str] = []
    while True:
        prompt = "db> " if not buffer else "... "
        try:
            line = input(prompt)
        except EOFError:
            print()
            break

        stripped = line.strip()
        if not buffer and stripped.lower() in {"exit", "quit"}:
            break

        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer)
            execute_statement(cursor, statement)
            buffer.clear()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute SQL statements against an SQLite database.")
    parser.add_argument("--db", required=True, help="Path to SQLite database (use :memory: for in-memory)")
    parser.add_argument("--execute", help="Execute a single SQL statement and exit")
    parser.add_argument("--script", type=Path, help="Execute all statements in a SQL script file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    connection = connect_database(args.db)
    cursor = connection.cursor()

    if args.script:
        execute_script(cursor, args.script)
    if args.execute:
        execute_statement(cursor, args.execute)
    if not args.execute and not args.script:
        interactive_shell(cursor)

    connection.commit()
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
