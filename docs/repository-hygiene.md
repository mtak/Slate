# Public repository hygiene

Slate is intended to be readable by anyone. Keep committed documentation,
examples, logs, screenshots, and configuration files safe for public access.

## Before publishing changes

From the repository root, inspect the exact staged changes:

```sh
git status --short
git diff --cached --check
git diff --cached
```

For every added or changed file, confirm that:

- Credentials, device tokens, private keys, certificates, and secret calendar
  feed URLs are placeholders. Put real values in ignored local files or
  deployment secret storage.
- Calendar entries, screenshots, logs, and other examples contain fictional
  data only. Remove names, addresses, schedules, and other household details.
- Network addresses and hostnames are loopback values or documentation
  placeholders, not values from a private network or deployment.
- Paths, usernames, ports, and other machine-specific settings are generic or
  explained as local examples.
- Any new local configuration file is covered by `.gitignore` before it is
  used. Confirm with `git check-ignore -v <path>` and verify it does not appear
  in `git status --short` as an untracked or staged file.

If a real secret has already been committed, remove it from the files and
rotate or revoke it. A later deletion does not remove it from Git history.
