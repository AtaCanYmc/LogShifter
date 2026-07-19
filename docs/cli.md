# Command Line Interface (CLI) Manual

logshift features a click-based command line interface that allows running pipelines directly from the terminal or GitHub Actions cron runners.

## Commands

### `logshift archive`
Fetches log records from a database source and delivers them to target destinations.

#### Parameter Flags

| Option Flag | Required | Default | Description |
| --- | --- | --- | --- |
| `--source` / `-s` | No | `supabase` | Log source database. |
| `--dest` / `-d` | No | `github` | Comma-separated target destinations (e.g. `github,sheets,slack`). |
| `--supabase-url` | Yes | - | Supabase project API endpoint URL. |
| `--supabase-key` | Yes | - | Supabase Service Role key. |
| `--supabase-table` | No | `logs` | Target table containing logs. |
| `--github-token` | No | - | GitHub Personal Access Token. |
| `--github-repo` | No | - | GitHub target repository (`username/repo`). |
| `--discord-webhook` | No | - | Discord Webhook integration URL. |
| `--slack-webhook` | No | - | Slack Webhook integration URL. |

---

## Examples

### Running Dry-Run Simulation
To test database connections and see parsed OpenTelemetry log records without performing real API writes:
```bash
logshift --dry-run archive \
  --supabase-url "https://your-proj.supabase.co" \
  --supabase-key "service-key" \
  --dest discord,slack
```

### Full Execution
```bash
logshift archive \
  --supabase-url "https://your-proj.supabase.co" \
  --supabase-key "service-key" \
  --dest github,discord \
  --github-token "ghp_token..." \
  --github-repo "myorg/logs-repo" \
  --discord-webhook "https://discord.com/api/webhooks/..."
```
