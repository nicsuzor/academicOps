# Brain Sync Systemd Timer

Periodic sync for `~/brain` repository.

## Installation

```bash
# Copy units to user systemd directory
mkdir -p ~/.config/systemd/user
cp brain-sync.service brain-sync.timer ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable and start timer
systemctl --user enable brain-sync.timer
systemctl --user start brain-sync.timer
```

## Verify

```bash
# Check timer status
systemctl --user status brain-sync.timer

# List all timers
systemctl --user list-timers

# Check last run
journalctl --user -u brain-sync.service -n 20
```

## Manual trigger

```bash
systemctl --user start brain-sync.service
```

## Logs

Sync failures are logged to `~/brain/.sync-failures.log`.
