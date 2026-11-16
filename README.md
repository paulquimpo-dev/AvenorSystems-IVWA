# Avenor Systems — Intentionally Vulnerable Web Application

A local web security testing lab built for the university seminar **Think Like a Hacker: Cybersecurity & Offensive Security**. It provides controlled demonstrations of weak authentication, route discovery, role-based access control, and defensive controls.

All company names, users, credentials, and dashboard records are fictional. The vulnerable configuration is for an isolated, private lab only. Do not expose it to the public Internet or use it against systems you do not own or have explicit permission to test. No cloud services, external assets, or APIs are used.

## Project overview

- **Application:** Flask web application with a PostgreSQL database.
- **Vulnerable mode:** Demonstrates a guessable training password and login attempts without throttling.
- **Secure mode:** Demonstrates stronger training credentials, per-IP request limits, and temporary account lockout.
- **Optional authorization exercise:** With `PRIVILEGE_ESCALATION_DEMO=true`, a named fictional staff or support account can change its own application role. The default is disabled; protected mode requires an administrator.
- **Testing workflow:** Documented HTTP request analysis, route enumeration, and bounded authentication testing using Burp Suite, Gobuster, and Hydra. These tools are not application dependencies.

This project does **not** intentionally implement SQL injection or cross-site scripting. Its database access uses SQLAlchemy, and user-provided text is rendered through Flask templates. The training scenarios focus on authentication and authorization behavior.

## Quick start

This lab requires Python and PostgreSQL. Follow the [Windows setup](#windows-setup-powershell) below to create a dedicated local database, configure `.env`, initialize the demo accounts, and start the server. The application listens on `0.0.0.0:5000` so a private VM can connect; restrict access to a host-only lab network before starting vulnerable mode.

For guided exercises, see [PRESENTER_GUIDE.md](PRESENTER_GUIDE.md), [PRIVILEGE_ESCALATION_GUIDE.md](PRIVILEGE_ESCALATION_GUIDE.md), and [SCENARIO_MATERIALS.md](SCENARIO_MATERIALS.md).

## Verification status

The integration suite in `tests/test_lab.py` covers the public pages, login behavior, secure-mode throttling and lockout, session invalidation, account permissions, the optional role escalation scenario, and logs that omit submitted passwords. The recorded run is summarized in [TEST_RESULTS.md](TEST_RESULTS.md). Testing requires a dedicated disposable PostgreSQL database; never point the test suite at a database containing useful data.

## Windows setup (PowerShell)

PostgreSQL must be running. Add its `bin` directory to PATH or invoke it explicitly:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -d postgres
```

In psql, create a dedicated role and database. `\password` prompts for a new, local database password without putting it in shell history:

```sql
CREATE ROLE cyberlab LOGIN;
\password cyberlab
CREATE DATABASE cybersecurity_demo OWNER cyberlab;
\q
```

Use this dedicated database only for this lab. Never point the app at a real application database.

```powershell
cd path\to\AvenorSystems-IVWA
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
notepad .env
```

If activation is restricted, skip activation and replace `python` with `.\.venv\Scripts\python.exe`. If `python` or `py` points to a missing installation, repair Python or use an installed Python executable by its full path.

Set `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg2://cyberlab:YOUR_URL_ENCODED_DB_PASSWORD@localhost:5432/cybersecurity_demo
SECRET_KEY=PASTE_THE_GENERATED_64_CHARACTER_VALUE
VULNERABLE_MODE=true
```

Percent-encode special characters in the database password, such as `@` → `%40`, `#` → `%23`, `%` → `%25`, `:` → `%3A`, `/` → `%2F`. `.env` is ignored by Git. The database password is separate from the fictional web account.

```powershell
python reset_demo.py
python app.py
```

Open **http://127.0.0.1:5000**. Flask listens on `0.0.0.0:5000`, with debugging disabled. Keep the terminal open; Ctrl+C stops it. There is no robots file, sitemap or public link revealing the administrator route.

## Predictable reset and mode switching

Stop Flask before resetting. With `VULNERABLE_MODE=true`, reset creates/restores `admin` / `Avenor2026!`. This deliberately guessable credential exists only for the seminar. Passwords are stored with Werkzeug's salted scrypt hash.

To show defenses, stop Flask, change `.env` to `VULNERABLE_MODE=false`, run `python reset_demo.py`, then restart. Secure demo login: `admin` / `Orbit-Lab-Only!2026#Anchor`. Secure reset enforces a longer fixture credential and records its mode; changing the flag alone cannot authenticate with the old weak fixture. Both passwords are documented training fixtures, not production secrets. Return to vulnerable mode using the same stop/edit/reset/start sequence.

Secure mode permits five POST attempts per source IP per rolling 60 seconds. Five failed attempts against the account lock it for 60 seconds across IPs. Later correct attempts are blocked while locked. Rejected attempts return HTTP 429 with the same failure text. IP limits are in process memory and reset on server restart; account counters persist in PostgreSQL. Run one Flask process. This is a demonstration, not a production authentication system. MFA and CAPTCHA are not implemented.

`reset_demo.py` creates missing application tables and restores only the `admin`, `alex.scott` and `support.account` records, clears its counters, and increments the session version to invalidate previous logins. It never drops a database, deletes other users or changes external files. Restart also clears in-memory IP limits. Logs are retained deliberately; they contain no submitted passwords. Dashboard activity is illustrative, not a live log viewer.

Authentication events are JSON lines in `logs/auth.log`, timestamped in UTC, with attempted username, direct source IP and outcome. Logs rotate at 1 MB with two backups. View them with:

```powershell
Get-Content .\logs\auth.log -Tail 20 -Wait
```

## Private VMware connectivity

Prefer **Host-only (VMnet1)** for Kali's adapter. Keep the Windows VMnet1 virtual adapter enabled. Disconnect Kali's other adapters during the demonstration. This works without Internet after dependencies/tools are installed. NAT can also allow host/guest communication, but host-only gives the clearest isolated setup. Avoid bridged mode, router forwarding, tunnels or public hosting.

On Windows run `ipconfig`. Find **VMware Network Adapter VMnet1**, and use its IPv4 address, not Wi-Fi, Ethernet, a gateway, VMnet8 (unless using NAT), or Kali's address. Example only: Windows `192.168.56.1`, Kali `192.168.56.128` on the same host-only subnet. Open `http://192.168.56.1:5000` from Kali. Never type `0.0.0.0` as the destination.

Flask's required `0.0.0.0` bind listens on every host interface. Before starting the vulnerable demo, disconnect physical network adapters or ensure firewall rules restrict inbound access to the VMware interface and Kali IP. Do not disable Windows Firewall. A narrowly scoped rule (Administrator PowerShell, replace BOTH addresses with your actual host-only addresses) is:

```powershell
New-NetFirewallRule -DisplayName 'Avenor private VMware lab' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000 -LocalAddress 192.168.56.1 -RemoteAddress 192.168.56.128 -Profile Any
```

This rule does not override other broad allow rules. Inspect/remove broad Python/port-5000 permissions or disconnect other adapters. PostgreSQL needs no guest access; keep port 5432 local. Remove the lab rule when finished:

```powershell
Remove-NetFirewallRule -DisplayName 'Avenor private VMware lab'
```

From Kali:

```bash
ip -4 addr
ip route
curl -i --connect-timeout 5 http://192.168.56.1:5000/
curl -i http://192.168.56.1:5000/admin
```

Copy just `demo_paths.txt` and `demo_passwords.txt` to Kali via VMware shared folders or a local removable drive. No Internet download or leaked lists are required. See `PRESENTER_GUIDE.md` for bounded Gobuster/Hydra commands.

## Troubleshooting

| Symptom | Check |
|---|---|
| Windows works, Kali times out | VMnet1 addresses on both systems, Kali host-only adapter connected, scoped Windows Firewall rule. Ping may be blocked; HTTP is the useful check. |
| Wrong IP | Use the Windows IPv4 on the same VMnet as Kali; use `ipconfig`, not a public-IP website. |
| Flask unreachable | Confirm terminal says `0.0.0.0:5000`, not loopback only, and process is still running. |
| VMware has no private connectivity | In Virtual Network Editor verify VMnet1 is host-only, host virtual adapter enabled and DHCP enabled; reconnect Kali adapter and renew its address. |
| Database authentication fails | Check PostgreSQL service, role/password, URL encoding, port and database name. Test `psql -h localhost -U cyberlab -d cybersecurity_demo`. Do not change existing server authentication to trust. |
| Relation users does not exist | Run reset with the same `.env` as the application. |
| Secure login fails after switching | Stop, reset in secure mode, restart; use secure fixture. Wait 60 seconds after a lockout. |
| Port 5000 occupied | `Get-NetTCPConnection -LocalPort 5000 -State Listen` then `Get-Process -Id PID`. Stop only a known process you own. |
| Python launcher error | Repair the stale installation/launcher; use a working full Python path or the prepared `.venv\Scripts\python.exe`. |

## Verification

`tests/test_lab.py` is an integration suite that needs a dedicated disposable PostgreSQL database. Never run it against a database with useful data: it resets the lab account. Set `LAB_TEST_DATABASE_URL` to its PostgreSQL URL and run `.\.venv\Scripts\python.exe tests\test_lab.py`. It checks public pages and hidden-route separation, authentication, session invalidation, secure controls, fixtures, and password-free logs. Actual guest connectivity must be checked from your Kali VM.

## Three-account role demonstration

Reset now seeds admin, alex.scott (Staff) and support.account (Support). See SCENARIO_MATERIALS.md for fictional evidence, weak/secure fixture credentials and permission rules. Staff/support use the same login form but have separate read-only workspaces and receive 403 on the administrator dashboard. Stop Flask, reset and restart to create the additional accounts. Existing account table fields are sufficient.

Account rename: reset migrates the earlier alex.demo and support.demo fixture names to alex.scott and support.account. If both old and new records already exist, the old fixture is retired and its sessions invalidated. Vulnerable passwords are alexscott_may52002 and supportaccount@2026; secure fixtures stay separate. Copy demo_usernames.txt and demo_passwords.txt to Kali for the short multi-account demonstration.

## Optional application privilege escalation lab

See PRIVILEGE_ESCALATION_GUIDE.md for the Burp Repeater walkthrough. Add PRIVILEGE_ESCALATION_DEMO=true in .env to enable the separately gated, intentionally missing role authorization check. It defaults to false and is independent of VULNERABLE_MODE. Stop/reset/restart before each comparison. Reset restores staff/support roles and invalidates old sessions. Switching the authorization flag off alone does not demote a previously promoted user. POST /api/account/role only changes the authenticated caller, with a CSRF token and fixed role allowlist. In the vulnerable branch it accepts changes from the named Alex/Support fixtures; protected mode requires an administrator. Every role change attempt reaching authorization is logged in logs/auth.log. The workflow is available through Review account access in the authenticated Staff/Support workspace, never through public navigation.
