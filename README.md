# DBTest

Simple command-line utility for executing SQL statements against an SQLite database. A lightweight Tkinter interface is also available when you want clickable controls and live logs.

## Features
- Connect to any SQLite database file (or use an in-memory database).
- Execute a single statement from the command line, run a SQL script file, or use an interactive shell.
- Results are displayed in a basic table format; non-query statements report affected rows.

## Usage
```
python db_client.py --db example.db --execute "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, body TEXT);"
python db_client.py --db example.db --execute "INSERT INTO notes (body) VALUES ('hello');"
python db_client.py --db example.db --execute "SELECT * FROM notes;"
python db_client.py --db example.db --script schema.sql
python db_client.py --db example.db
```

Use `:memory:` for an in-memory database that disappears when the program exits:
```
python db_client.py --db :memory: --execute "SELECT 'temp' AS value;"
```

### Graphical interface

Launch the Tkinter-based GUI to run statements and view live logs without using the terminal:

```
python db_client.py --gui
```

Specify an initial database path (defaults to an in-memory database) or connect to a file using the Browse button inside the GUI.

While in the interactive shell, type `exit` or `quit` to close the program. End statements with a semicolon (`;`).
