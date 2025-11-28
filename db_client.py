#!/usr/bin/env python3
"""Command-line and Tkinter database client for SQLite and PostgreSQL."""
from __future__ import annotations

import argparse
import contextlib
import logging
import sqlite3
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
from typing import Iterable, List, Protocol, Sequence, runtime_checkable


logger = logging.getLogger(__name__)


@runtime_checkable
class DBAPICursor(Protocol):
    """Subset of Python DB-API 2.0 cursor methods used by this client."""

    description: Sequence[Sequence[object]] | None
    rowcount: int

    def execute(self, sql: str) -> object:
        ...

    def fetchall(self) -> List[Sequence[object]]:
        ...


@runtime_checkable
class DBAPIConnection(Protocol):
    """Minimal DB-API 2.0 connection interface used by the client."""

    def cursor(self) -> DBAPICursor:
        ...

    def commit(self) -> None:
        ...

    def close(self) -> None:
        ...


def connect_database(db_path: str) -> DBAPIConnection:
    """Create and return a database connection.

    Parameters
    ----------
    db_path:
        Path to the SQLite database or a full connection string to a remote
        database (currently supports PostgreSQL URIs beginning with
        ``postgres://`` or ``postgresql://``). Use ``:memory:`` for an in-memory
        SQLite database.
    """

    if db_path.startswith(("postgres://", "postgresql://")):
        try:
            import psycopg2  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - psycopg2 optional
            raise SystemExit(
                "psycopg2 is required for PostgreSQL connections. Install with 'pip install psycopg2-binary'."
            ) from exc

        return psycopg2.connect(db_path)

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


def execute_statement(cursor: DBAPICursor, sql: str) -> str:
    """Execute a single SQL statement and return the formatted result."""
    try:
        cursor.execute(sql)
    except Exception as exc:
        error = f"Error: {exc}"
        logger.error(error)
        return error

    if cursor.description:
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        output = format_rows(columns, rows)
        logger.info("Query returned %s row(s)", len(rows))
        return output

    affected = cursor.rowcount
    message = f"OK ({affected} rows affected)"
    logger.info(message)
    return message


class DatabaseClient:
    """Manage database connections and statement execution."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.connection: DBAPIConnection | None = None
        self.cursor: DBAPICursor | None = None

    def connect(self) -> None:
        self.close()
        self.connection = connect_database(self.target)
        self.cursor = self.connection.cursor()
        logger.info("Connected to %s", self.target)

    def ensure_cursor(self) -> DBAPICursor:
        if not self.cursor:
            self.connect()
        assert self.cursor  # for type checkers
        return self.cursor

    def run_statement(self, sql: str) -> str:
        cursor = self.ensure_cursor()
        result = execute_statement(cursor, sql)
        self.commit()
        return result

    def run_script(self, path: Path) -> str:
        cursor = self.ensure_cursor()
        result = execute_script(cursor, path)
        self.commit()
        return result

    def commit(self) -> None:
        if self.connection:
            self.connection.commit()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            if self.connection:
                self.connection.close()
        self.connection = None
        self.cursor = None

    def __enter__(self) -> "DatabaseClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()


def execute_script(cursor: DBAPICursor, path: Path) -> str:
    """Run all statements from a file and return a status message."""
    sql = path.read_text(encoding="utf-8")
    try:
        if hasattr(cursor, "executescript"):
            cursor.executescript(sql)  # type: ignore[call-arg]
        else:
            for statement in _split_statements(sql):
                cursor.execute(statement)
    except Exception as exc:  # sqlite3.DatabaseError or driver-specific
        error = f"Error executing script {path}: {exc}"
        logger.error(error)
        return error

    message = f"Executed script: {path}"
    logger.info(message)
    return message


def _split_statements(sql: str) -> List[str]:
    """Very small helper to split script text into executable statements."""

    statements: List[str] = []
    buffer: List[str] = []
    for line in sql.splitlines():
        buffer.append(line)
        if line.rstrip().endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";")
            if statement:
                statements.append(statement)
            buffer.clear()

    if buffer:
        statement = "\n".join(buffer).strip().rstrip(";")
        if statement:
            statements.append(statement)

    return statements


def interactive_shell(client: DatabaseClient) -> None:
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
            output = client.run_statement(statement)
            print(output)
            buffer.clear()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute SQL statements against SQLite or PostgreSQL databases."
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        help=(
            "Path to SQLite database or PostgreSQL connection string. "
            "Use :memory: for an in-memory SQLite database."
        ),
    )
    parser.add_argument("--execute", help="Execute a single SQL statement and exit")
    parser.add_argument("--script", type=Path, help="Execute all statements in a SQL script file")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface")
    return parser.parse_args(argv)


class LogDisplayHandler(logging.Handler):
    """Logging handler that writes log messages to a Tkinter text widget."""

    def __init__(self, widget: scrolledtext.ScrolledText) -> None:
        super().__init__()
        self.widget = widget
        self.widget.configure(state="disabled")
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, message + "\n")
        self.widget.yview(tk.END)
        self.widget.configure(state="disabled")


class DatabaseGUI:
    """Tkinter-based interface for executing SQL statements with live logs."""

    def __init__(self, root: tk.Tk, initial_db: str) -> None:
        self.root = root
        self.client = DatabaseClient(initial_db)
        self.logger = logging.getLogger("db_client.gui")

        self.root.title("DBTest SQLite Client")
        self.db_path_var = tk.StringVar(value=initial_db)

        self._build_layout()
        self._configure_logging()
        self._connect_to_database()

    def _build_layout(self) -> None:
        db_frame = tk.Frame(self.root)
        db_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(db_frame, text="Database path:").pack(side=tk.LEFT)
        tk.Entry(db_frame, textvariable=self.db_path_var, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(db_frame, text="Browse", command=self._choose_db_file).pack(side=tk.LEFT)
        tk.Button(db_frame, text="Connect", command=self._connect_to_database).pack(side=tk.LEFT, padx=5)

        sql_frame = tk.Frame(self.root)
        sql_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(sql_frame, text="SQL statement:").pack(anchor=tk.W)
        self.sql_input = scrolledtext.ScrolledText(sql_frame, height=8)
        self.sql_input.pack(fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(sql_frame)
        button_frame.pack(fill=tk.X, pady=5)
        tk.Button(button_frame, text="Execute", command=self._execute_statement).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Run Script", command=self._run_script).pack(side=tk.LEFT, padx=5)

        tk.Label(sql_frame, text="Results:").pack(anchor=tk.W)
        self.results_output = scrolledtext.ScrolledText(sql_frame, height=10, state="disabled")
        self.results_output.pack(fill=tk.BOTH, expand=True)

        tk.Label(sql_frame, text="Live Logs:").pack(anchor=tk.W, pady=(10, 0))
        self.log_output = scrolledtext.ScrolledText(sql_frame, height=10, state="disabled")
        self.log_output.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_logging(self) -> None:
        handler = LogDisplayHandler(self.log_output)
        handler.setLevel(logging.INFO)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def _choose_db_file(self) -> None:
        selection = filedialog.askopenfilename(
            title="Select SQLite database",
            filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")],
        )
        if selection:
            self.db_path_var.set(selection)

    def _connect_to_database(self) -> None:
        path = self.db_path_var.get().strip() or ":memory:"
        try:
            self.client.target = path
            self.client.connect()
            self.logger.info("Connected to %s", path)
        except Exception as exc:
            messagebox.showerror("Connection error", str(exc))
            self.logger.error("Failed to connect to %s: %s", path, exc)

    def _execute_statement(self) -> None:
        sql = self.sql_input.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showinfo("No SQL", "Enter an SQL statement to execute.")
            return

        try:
            result = self.client.run_statement(sql)
        except Exception as exc:
            result = f"Error: {exc}"
            self.logger.error(result)
        self._display_result(result)
        self.logger.info("Executed statement")

    def _run_script(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select SQL script",
            filetypes=[("SQL Files", "*.sql"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            result = self.client.run_script(Path(filename))
        except Exception as exc:
            result = f"Error: {exc}"
            self.logger.error(result)
        self._display_result(result)

    def _display_result(self, message: str) -> None:
        self.results_output.configure(state="normal")
        self.results_output.delete("1.0", tk.END)
        self.results_output.insert(tk.END, message)
        self.results_output.configure(state="disabled")

    def _on_close(self) -> None:
        self.client.close()
        self.root.destroy()


def launch_gui(initial_db: str) -> None:
    root = tk.Tk()
    DatabaseGUI(root, initial_db)
    root.mainloop()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.gui:
        launch_gui(args.db)
        return 0

    with DatabaseClient(args.db) as client:
        if args.script:
            output = client.run_script(args.script)
            print(output)
        if args.execute:
            output = client.run_statement(args.execute)
            print(output)
        if not args.execute and not args.script:
            interactive_shell(client)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
