# DBTest

Command-line and Tkinter utility for executing SQL statements against an SQLite database or a remote PostgreSQL instance. A lightweight GUI is available when you prefer clickable controls and live logs.

## Features
- Connect to any SQLite database file (or use an in-memory database) or a PostgreSQL connection string such as `postgresql://user:pass@host:5432/dbname`.
- Execute a single statement from the command line, run a SQL script file, or use an interactive shell.
- Results are displayed in a basic table format; non-query statements report affected rows.

## Usage
```
python3 db_client.py --db example.db --execute "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, body TEXT);"
python3 db_client.py --db example.db --execute "INSERT INTO notes (body) VALUES ('hello');"
python3 db_client.py --db example.db --execute "SELECT * FROM notes;"
python3 db_client.py --db example.db --script schema.sql
python3 db_client.py --db example.db
```

Use a PostgreSQL URI to connect to a remote database (requires `psycopg2-binary`):

```
python3 db_client.py --db postgresql://user:pass@db.example.com:5432/mydb --execute "SELECT NOW();"
```

Use `:memory:` for an in-memory database that disappears when the program exits:
```
python3 db_client.py --db :memory: --execute "SELECT 'temp' AS value;"
```

### Graphical interface

Launch the Tkinter-based GUI to run statements and view live logs without using the terminal:

```
python3 db_client.py --gui
```

Specify an initial database path (defaults to an in-memory database) or connect to a file/remote URI using the Browse button inside the GUI.

While in the interactive shell, type `exit` or `quit` to close the program. End statements with a semicolon (`;`).
