# db-backup-oss

Open-source project to backup MySQL or PostgreSQL, compress the dump, keep only recent backups, and upload to S3-compatible storage (Linode Object Storage, AWS S3, MinIO, etc).

## Features

- Supports `mysql` and `postgres`
- Backup file name includes database name (example: `app_db_20260322T173011Z.sql.gz`)
- Gzip compression (`.sql.gz`)
- Local retention: keep only the latest 2 backups
- Remote retention: keep only the latest 3 backups in object storage
- Upload provider abstraction:
  - built-in `s3`
  - built-in `noop` (no upload)
  - custom provider via dotted path (for other repositories)

## Project Structure

- `src/db_backup/` application source
- `src/db_backup/providers/` upload providers
- `config/mysql.yaml` MySQL example
- `config/postgres.yaml` PostgreSQL example
- `backups/mysql/` local MySQL backups
- `backups/postgres/` local PostgreSQL backups

## Requirements

- Python 3.10+
- System client tools:
  - `mysqldump` for MySQL backups
  - `pg_dump` for PostgreSQL backups

### Install database client tools

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y mysql-client postgresql-client
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Configuration

Use one of the ready templates:

- `config/mysql.yaml`
- `config/postgres.yaml`

You can also copy `config/config.example.yaml` to `config/config.yaml`.

Use env vars for secrets:

```bash
export DB_PASSWORD='your-db-password'
export LINODE_ACCESS_KEY='your-linode-access-key'
export LINODE_SECRET_KEY='your-linode-secret-key'
```

## Run

MySQL:

```bash
db-backup --config config/mysql.yaml
```

PostgreSQL:

```bash
db-backup --config config/postgres.yaml
```

The command will:

1. Create compressed dump (`.sql.gz`) in `backups/mysql/` or `backups/postgres/`
2. Keep only last 2 local backups for the same database
3. Upload to S3-compatible bucket
4. Keep only last 3 remote backups for the same database

## Linode Object Storage (S3 compatible)

Set in YAML:

- `storage.provider: s3`
- `storage.endpoint_url: https://<region>.linodeobjects.com`
- `storage.bucket`
- `storage.access_key_id`
- `storage.secret_access_key`

## Configure upload to other repositories

Create a provider class with methods:

- `upload_file(self, local_path, remote_key)`
- `list_objects(self, prefix)` returning `list[RemoteObject]`
- `delete_object(self, key)`

Then set:

```yaml
storage:
  provider: my_package.my_module.MyProvider
```

The custom class receives `StorageConfig` in the constructor.

## Cron example

Daily at 02:00:

```bash
0 2 * * * /path/to/.venv/bin/db-backup --config /path/to/db-backup-oss/config/mysql.yaml >> /var/log/db-backup.log 2>&1
```

## License

MIT
