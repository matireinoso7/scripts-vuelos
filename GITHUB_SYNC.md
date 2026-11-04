# Syncing full CSV exports to GitHub

The flight sheet exports (`sheet_live.csv`, `sheet_live_no_feb.csv`) are ~68 KB each. GitHub MCP uploads from Cloud Agents are limited to ~16 KB per `create_or_update_file` call, so the copies on `main` may be partial until you push from a machine with `gh` auth.

From a clone that matches this repo:

```bash
gh auth login
git remote add github https://github.com/matireinoso7/scripts-vuelos.git 2>/dev/null || true
git push github main
```

Verify sizes:

```bash
wc -c sheet_live.csv sheet_live_no_feb.csv
# expect 68263 and 68065
```
