# Publishing the source

What goes in the public repository, and what must never go there.

## Published

| Folder | Contents |
|---|---|
| `launcher/` | Launcher (C#, .NET Framework 4.8) |
| `relay-agent/` | Host relay agent `RevivalRelay.exe` (C#, .NET 8) |
| `server/` | API, UDP relay, anti-cheat, admin panel, deployment (Node.js, PostgreSQL) |
| `release/release.py` | Builds, signs and uploads updates (needs the private key, not included) |
| `release/signing-public-key.txt` | Public key the launcher checks updates with |
| `tools/` (scripts only) | Pak building and Blueprint analysis scripts (`kismet/*.py`, `online/*.py`) |
| Lua mods | `Propnight/Binaries/Win64/Mods/PropnightLocalMap`, `PropnightLoginBypasser` |
| `LICENSE`, this file | Documentation |

`server/src/legacy` and the login bypass come from the Propnight Revived project
(MIT): keep their copyright notice.

## Never published

| What | Why |
|---|---|
| `release/.signing-key.pem` | Whoever has it can push files to every player |
| `release/.r2.json` | Write access to the Cloudflare R2 bucket |
| `server/.env`, `server/deploy/.vps-password`, `server/deploy/.admin-password` | Server, database and admin passwords |
| `server/config/anticheat.json` (VPS) | Anti-cheat limits: public limits are easy to stay under |
| Discord webhook URL | Anyone could post in the alert channel |
| `HANDOFF.md`, `analysis/` | Working notes: server setup and anti-cheat details |
| `distribution/` | Old manual scripts from before the launcher |
| Game files: `*.pak`, `*.uasset`, `*.uexp`, `*.umap`, `Propnight.exe`, `extracted/`, `modpak/`, `v2/`, `v4/`, `cmp*/`, `online/*.pak` | Property of the game's owners; players get them from Steam, the revival paks only through the launcher |
| `tools/UAssetGUI-*`, `tools/repak-*`, `tools/UE4SS_*` | Third-party tools: link to their own releases instead |
| `backups/`, `logs/`, `certs/`, `hosts.before-revival` | Local machine data |
| `server/test/fixtures/*.sav` as they are now | Copies of a real player's saves (Steam ID, progress): replace them with saves from a fresh test account before the first commit |

A `.gitignore` at the repository root should list all of the above before the
first commit.
