# Command Line Interface (CLI) Manual

logshift features a click-based command line interface that allows running pipelines directly from the terminal or GitHub Actions cron runners.

The CLI documentation below is dynamically generated from the codebase to avoid documentation drift:

::: mkdocs-click
    :module: logshift.cli
    :command: cli
    :depth: 2

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
