# Obsidian Sync (Headless)

Claude Code writes the wiki on laptop. You read on phone before a meeting. No desktop
Obsidian running on the server-side.

## Why obsidian-headless

- Desktop Obsidian needs a GUI
- Syncthing/Git/iCloud don't give Obsidian's link integrity
- Obsidian Sync is first-party and handles `[[wikilinks]]` properly
- `obsidian-headless` runs the sync engine without a window

## Prerequisites

- Obsidian account with Sync subscription ($5/mo tier is fine for PM wiki)
- Node.js 22+ on the host running Claude Code
- The wiki directory already scaffolded

## Initial Setup

```bash
npm install -g obsidian-headless

ob login --email <your-email> --password '<pw>'

# Create a remote vault
ob sync-create-remote --name "PM Wiki"

# Connect the wiki dir to it
cd "$WIKI_PATH"    # or wherever you scaffolded
ob sync-setup --vault "<vault-id-from-previous-step>"

# First sync
ob sync
```

On your phone/laptop Obsidian:
1. Open vault list
2. "Sync with existing remote vault"
3. Pick "PM Wiki"
4. Confirm the `[[wikilinks]]` render and Graph View works

## Continuous Background Sync (Systemd)

`~/.config/systemd/user/obsidian-pm-sync.service`:

```ini
[Unit]
Description=Obsidian PM Wiki Sync
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/ob sync --continuous
WorkingDirectory=%h/pm-wiki
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

Adjust `ExecStart` to match `which ob` on your machine.

```bash
systemctl --user daemon-reload
systemctl --user enable --now obsidian-pm-sync

# Survive logout
sudo loginctl enable-linger $USER

# Check
systemctl --user status obsidian-pm-sync
journalctl --user -u obsidian-pm-sync -f
```

## Conflict Resolution

Obsidian Sync handles most conflicts transparently. For rare real conflicts:

- Both sides modified same file → Obsidian creates `.sync-conflict` variant
- Resolve manually in Obsidian (mobile or desktop), pick a version
- Delete the conflict file

Prevention: don't edit on mobile while Claude Code is running an ingest. Stagger edits.

## What to sync

- Everything in `$WIKI_PATH/`, the scaffolded wiki dir
- Raw sources included, you might want to re-read them on mobile

What NOT to sync (separate path):
- Claude Code workspace directories
- Hindsight's `~/.hindsight/`
- Anything outside the wiki dir

## Obsidian Config for PM Wiki

Recommended plugins/settings once synced:

- **Dataview**: query frontmatter. Useful:
  ```dataview
  TABLE updated, tags
  FROM "entities"
  WHERE contains(tags, "company") AND contains(tags, "competitive")
  SORT updated DESC
  ```
- **Graph View**: visualize link density. Helps spot orphans visually.
- **Templater**: for quick new-page scaffolding from mobile (if you jot from phone).
- **Attachment folder**: set to `raw/assets/` so screenshots land there.

## Troubleshooting

- **Sync stuck**: `ob sync` manually to see error
- **Auth expired**: `ob login` again
- **Mobile not pulling**: check Obsidian Sync status in app settings
- **Ingests not appearing on mobile**: confirm systemd service is running
  and WorkingDirectory points to the actual wiki path
