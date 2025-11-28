# DBTest

This project now provides a single-purpose command-line tool for rebuilding a Postgres table from a SQL Server styled schema file and a CSV dataset. The previous code has been removed and replaced with a streamlined workflow centered on this task.

## What it does
1. Connects to a Postgres database via a connection string.
2. Reads a `.sql` file that contains a SQL Server style `CREATE TABLE` statement.
3. Translates common SQL Server syntax to Postgres and creates the table (dropping any existing table of the same name).
4. Reads rows from a CSV file and inserts them into the new table in column order from the schema.

## Requirements
- Python 3.10+
- A reachable Postgres instance
- `psycopg-binary` (installed automatically from `requirements.txt`)

### Installation
Install the dependencies into your virtual environment:

```
pip install -r requirements.txt
```

If you see `ImportError: no pq wrapper available` or similar errors when importing `psycopg`, reinstall the bundled binary wheel to ensure `libpq` is included:

```
pip install --force-reinstall "psycopg[binary]"
```
On Windows, also make sure the Visual C++ runtime is installed; you can download the [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) from Microsoft if it is not already present.

## Usage
```
python3 main.py --conn postgresql://user:pass@host:5432/dbname --sql path/to/schema.sql --csv path/to/data.csv
```

Optional flags:
- `--table` — override the table name found in the SQL file.
- `--schema` — target a specific schema (defaults to `public`).

## Notes on SQL conversion
The conversion handles common data types (`INT`, `NVARCHAR`, `DATETIME`, `BIT`, etc.), removes SQL Server specific options (`WITH (...)`, `ON [PRIMARY]`, `GO`), and turns `IDENTITY` into a Postgres identity column. It is not a full SQL parser; if your schema uses uncommon features, review the generated table before loading data.
