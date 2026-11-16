# Optional privilege escalation demonstration - Burp Repeater

This explicitly expands the original authentication-only scope. It changes only the caller's fictional application role, not Windows privileges. It adds no shell, command execution, file modification or ability to change other accounts.

## Prepare

Stop Flask. Add `PRIVILEGE_ESCALATION_DEMO=true` to .env. For the familiar credentials, also use `VULNERABLE_MODE=true`. Reset and start:

```powershell
.\.venv\Scripts\python.exe reset_demo.py
.\.venv\Scripts\python.exe app.py
```

The flags are independent. VULNERABLE_MODE controls login defenses/credentials; PRIVILEGE_ESCALATION_DEMO controls the intentional role authorization flaw. False is the default for the new flag. No database migration is needed.

## Demonstrate

1. Open Burp's browser with Intercept off. Use `http://192.168.56.1:5000` to avoid the .app browser HTTPS requirement. Target only your host-only lab.
2. Log in as `alex.scott` / `alexscott_may52002`.
3. Request `/admin/dashboard`: show 403. Return to `/workspace/staff`.
4. Click **Review account access**, then **Submit role review**. This submits the current `role=staff` in a hidden field with a CSRF token. The baseline submission changes nothing.
5. In Burp Proxy HTTP history find `POST /api/account/role`. Send to Repeater.
6. Keep the signed session Cookie header and csrf token. Change only `role=staff` to `role=admin`, then Send. Burp adjusts Content-Length.
7. Response 200 shows previous/current roles. In the same Burp browser request `/admin/dashboard`: access is now granted. Authorization is read from PostgreSQL on every request; no re-login needed.
8. Stop after proving access. Inspect logs/auth.log for JSON `event=role_change`, actor, previous/requested role, IP and allowed/denied. No password or session token is logged.

Say: **The application checked who I am, but failed to check whether I can change roles. A hidden form field is not authorization.**

Request body shape (use actual session/token from your own captured request):

```text
csrf=CAPTURED_TOKEN&role=admin
```

## Show the fix

Stop Flask, set `PRIVILEGE_ESCALATION_DEMO=false`, reset and restart. Keep VULNERABLE_MODE unchanged to isolate the authorization fix. Reset is essential: turning the switch off does not demote accounts already promoted.

Log in as Alex again. Old cookies/tokens are invalid after reset, so capture a fresh review request and send it to Repeater. A Staff POST now returns styled 403 (even the unchanged review submission). Changing role to admin is denied, its DB role remains staff, and `/admin/dashboard` stays 403. Check the denied log event.

Existing administrators can submit role updates to their own account; non-administrators cannot when protected. The intentional flaw is bounded to alex.scott and support.account and only updates the caller's own role. Unknown role values return 400. Missing/invalid CSRF tokens return 400. Unauthenticated requests redirect to login. Reset restores all three canonical roles and invalidates old sessions.

End by resetting with the escalation flag false. The existing two-page PDF covers login testing; use this guide for the additional Burp exercise.
