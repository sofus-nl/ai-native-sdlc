# Security policy

## Report a vulnerability

Report it privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**. Do not open a public issue for a vulnerability.

Include the plugin version, the host (Claude Code or Codex) and its version, and the steps that show the problem. Leave out secrets and private project data.

## Supported versions

Only the latest release gets security fixes. The plugin is pre-1.0; a fix ships as a new version and earlier versions are not patched.

## What the plugin runs on your machine

- The skills are Markdown instructions. They run nothing by themselves.
- On Claude Code the plugin registers one hook, `hooks/edit_guard.py`. Claude Code runs it with your full user rights, outside the Bash sandbox, on four events: before each file edit and shell command, after each skill call, when a typed slash command expands, and when a turn stops.
  - It reads the session transcript and the project's `.sdlc/` files. It hashes the project's files to see what changed: through `git` in a Git repository, and by reading the files directly in a folder without Git, where it stops after about 2,000 files.
  - It writes a record file and a short-lived claim file per session in the plugin's data folder, or in the system temp folder when the host names no data folder. It deletes session files older than 14 days from that folder.
  - It makes no network connection.
- On Codex the plugin registers no hook.
- The plugin bundles no third-party code and needs no API key.

A plugin update replaces these files. To keep the files you reviewed, pin your install to a reviewed release tag or commit; see the Security section of the [README](README.md#security).
