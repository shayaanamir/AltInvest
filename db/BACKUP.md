# Backing up and restoring the app database (ml/docs/DECISIONS.md D93)

All app data lives in the Atlas database `altinvest_db`. Take a backup before any cleanup (`db/cleanup_seed_data.py`), backfill or migration.

- Backups go to a folder **outside the repository**. The script refuses a folder inside it. They are never committed: they contain user accounts, password hashes and sessions.
- The tools come from the `mongo:7` Docker image (mongodump / mongorestore 100.x), so Docker must be running.
- The connection string comes from `BACKEND_MONGO_URI` (else `MONGO_URI`), from the environment or the repo's `.env`. It is passed to the container as an environment variable, never printed and never on a command line.

## Backup

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest
powershell -ExecutionPolicy Bypass -File db\backup_atlas.ps1 -OutDir D:\altinvest-backups
```

This writes `D:\altinvest-backups\altinvest_db-<UTC time>\altinvest_db\*.bson.gz` and `*.metadata.json.gz`, one pair per collection (indexes included). At the end it prints the matching restore command.

## Restore

`--drop` replaces each collection that is in the dump with its backed-up content. Collections created after the backup are left alone. Without `--drop`, documents are inserted, and documents whose `_id` already exists are skipped (no update).

```powershell
$env:ALTINVEST_DUMP_URI = "<the same connection string>"   # or: $env:ALTINVEST_DUMP_URI = $env:BACKEND_MONGO_URI
docker run --rm -e ALTINVEST_DUMP_URI -v "D:\altinvest-backups:/backup" mongo:7 sh -c 'mongorestore --uri="$ALTINVEST_DUMP_URI" --gzip --drop --nsInclude="altinvest_db.*" /backup/altinvest_db-<UTC time>'
Remove-Item Env:\ALTINVEST_DUMP_URI
```

To restore only one collection (for example `prices`), use `--nsInclude="altinvest_db.prices"`.

## Check a backup

```powershell
docker run --rm -v "D:\altinvest-backups:/backup" mongo:7 sh -c 'ls -la /backup/altinvest_db-<UTC time>/altinvest_db | head'
```
