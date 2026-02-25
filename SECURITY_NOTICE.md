# Security Notice

This repository had its Git history rewritten on 2026-02-25 to remove sensitive information.

## What was removed
- Personal email addresses
- VPS IP addresses
- Active endpoint IDs
- Local file paths
- Configuration files with credentials

## Changes made
- All sensitive values replaced with placeholders or environment variables
- Use `.env` file for configuration (see `.env.example`)
- `CONTEXT.md` removed from history and added to `.gitignore`
- Hardcoded API keys replaced with `os.getenv()` calls

## For users
Copy `.env.example` to `.env` and fill in your own values:

```bash
RUNPOD_API_KEY=your_key_here
ENDPOINT_ID=your_endpoint_id
```

## Files affected
- `download_job_output.py` - Now uses environment variables
- `README.md` - Email replaced with placeholder
- `hub.json` - Email replaced with placeholder
- `BREAKTHROUGH.md` - Endpoint IDs replaced with placeholders

## Git history
The repository history was cleaned using `git filter-branch` to remove all traces of sensitive data from commits dating back to the initial commit.

If you had previously cloned this repository, you should re-clone it or force-pull the changes:

```bash
git fetch origin
git reset --hard origin/main
```
