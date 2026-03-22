# db-backup-oss

Open-source project to backup MySQL or PostgreSQL, compress the dump, keep only recent backups, and upload to S3-compatible storage (Linode Object Storage, AWS S3, MinIO, etc).

## Features

- Supports `mysql` and `postgres`
- Backup file name includes database name (example: `app_db_20260322T173011Z.sql.gz`)
- Gzip compression (`.sql.gz`)
- Local retention: keep only the latest 2 backups
- Remote retention: keep only the latest 3 backups in object storage
- Interactive setup wizard for quick onboarding
- Notifications for automatic backups via Discord and/or Telegram
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

### Setup Wizard

Generate a full config interactively:

```bash
db-backup --wizard --config config/config.yaml
```

The wizard asks for database, retention, storage, and notifications, then writes a ready-to-use YAML file.

Use env vars for secrets:

```bash
export DB_PASSWORD='your-db-password'
export LINODE_ACCESS_KEY='your-linode-access-key'
export LINODE_SECRET_KEY='your-linode-secret-key'
export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'
export TELEGRAM_BOT_TOKEN='123456:ABCDEF'
export TELEGRAM_CHAT_ID='-1001234567890'
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

When notifications are enabled, success/failure messages are sent to Discord and/or Telegram.

## Linode Object Storage (S3 compatible)

Set in YAML:

- `storage.provider: s3`
- `storage.endpoint_url: https://<region>.linodeobjects.com`
- `storage.addressing_style: virtual` (recommended for Linode)
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

## Notifications

In YAML:

```yaml
notifications:
  enabled: true
  discord_webhook_url: ${DISCORD_WEBHOOK_URL}
  telegram_bot_token: ${TELEGRAM_BOT_TOKEN}
  telegram_chat_id: ${TELEGRAM_CHAT_ID}
```

Notes:

- If only Discord is configured, only Discord messages are sent.
- If only Telegram is configured, only Telegram messages are sent.
- If both are configured, both receive notifications.

## Troubleshooting

- `Discord notification failed: unknown url type: '${DISCORD_WEBHOOK_URL}'`
  - Cause: env var not exported.
  - Fix: export `DISCORD_WEBHOOK_URL` before running, or disable notifications.

- `Telegram notification failed: HTTP Error 404: Not Found`
  - Cause: invalid bot token or unresolved env var in `telegram_bot_token`.
  - Fix: verify token/chat id and export env vars.

- `Access denied for user 'root'@'localhost'` (MySQL/MariaDB error 1698)
  - Cause: root often uses socket auth in MariaDB.
  - Fix: create a dedicated backup user with password and proper grants, then update YAML.

- `ConnectionClosedError` during S3 upload
  - Usually transient network/TLS issue with endpoint.
  - For Linode, prefer `storage.addressing_style: virtual`.
  - The uploader now retries automatically; if it persists, validate `endpoint_url`, bucket policy, and firewall/DNS connectivity.

## Cron example

Daily at 02:00:

```bash
0 2 * * * /path/to/.venv/bin/db-backup --config /path/to/db-backup-oss/config/mysql.yaml >> /var/log/db-backup.log 2>&1
```

## License

MIT
