# Think Like a Hacker: Cybersecurity & Offensive Security

Before presenting: isolate VirtualBox host-only networking, initialize vulnerable mode, confirm Kali can reach the host, and copy both small wordlists to Kali. All commands below are solely for this owned local lab. Replace the example IP with the Windows VirtualBox host-only IPv4 if different.

1. Open the home page. “Start like a normal user.” Browse Home, Products, About and Contact. “What can we see? What else might exist?”
2. Switch to Kali in the folder containing the lists. Discover paths:

   ```bash
   gobuster dir -u http://192.168.56.1:5000 -w demo_paths.txt -t 1 --timeout 5s
   ```

   Expect `/admin` HTTP 200; missing paths return 404. “Discovery does not equal access.”

   For the larger built-in Kali directory list, if installed:

   ```bash
   gobuster dir -u http://192.168.56.1:5000 -w /usr/share/wordlists/dirb/common.txt -t 2 --timeout 5s
   ```

   Do not enable redirect following for the status-code comparison. Candidate coverage depends on the installed list; the supplied `demo_paths.txt` includes all discovery fixtures.

   | Paths | Expected response | Teaching point |
   |---|---|---|
   | `/support`, `/faq`, `/careers`, `/news`, `/docs`, `/status` | 200 | Reachable pages can exist outside navigation. |
   | `/documentation`, `/docs`, `/download`, `/downloads`, `/events` | 200 | Documentation, downloadable sample resources and a fictional event agenda. |
   | `/backup`, `/uploads`, `/private` | 403 | Discovery does not grant permission to access content. These are inert fixtures. |
   | `/admin` | 200 | A login portal exists; authentication is still required. |
   | Unknown paths | 404 | A genuine missing resource, not a catch-all success page. |

   The extra pages never reveal the login route or credentials. Navigation still contains only Home, Products, About and Contact. The downloads library serves only fixed fictional TXT/CSV resources; Events provides a sample calendar file. No downloadable backup, file upload, real infrastructure status or directory listing is implemented.

   Additional explicit matches from the supplied common.txt:
   - 302 aliases: `/help`, `/services`, `/company`, `/team`, `/partners`, `/press`, `/resources`. These redirect to relevant public pages.
   - 403 placeholders: `/.git/HEAD`, `/.htaccess`, `/.htpasswd`, `/.ssh`, `/.config`, `/_backup`, `/_private`, `/config`, `/database`, `/backups`, `/logs`, `/includes`, `/server-status`. These never serve files or credentials. A 403 here is a deliberately constructed teaching fixture, not evidence of an underlying file.
   - The full 4,614-candidate list is not converted into real endpoints. Unmatched names still return 404 so discovery results remain meaningful.
3. Open `/admin`. Make two or three incorrect manual login attempts. Each displays `Invalid username or password`. “What happens if someone automates this?”
4. Perform the bounded authentication demonstration:

   ```bash
   hydra -l admin -P demo_passwords.txt -s 5000 -t 1 -f 192.168.56.1 http-post-form '/admin:username=^USER^&password=^PASS^:F=Invalid username or password'
   ```

   A small fictional candidate list, one worker, stop at first success. Stop immediately after identifying the fixture. Do not expand the target or wordlist.
5. Log in normally with the discovered fictional credential. `/admin/dashboard` demonstrates administrative access using read-only fictional data. Explain: exposed endpoint → weak authentication protection → valid credential → administrative access → possible business impact. Stop after proving access; no destructive actions.
6. “Now switch sides.” Logout, stop Flask, set `VULNERABLE_MODE=false`, reset, restart. Explain rate limits, temporary account lockout, stronger credentials, logging/alerting and MFA. MFA is a discussion point, not implemented.
7. Send six wrong manual attempts, or repeat the same bounded command. Inspect 429 responses and `logs/auth.log`. **Hydra's failure-string matcher intentionally treats 429s as failures, not successes**, because blocked responses retain the failure message. The weak wordlist contains no secure credential. Secure mode therefore changes both credentials and attempt handling; demonstrate 429 and logs to isolate the effect of throttling.
8. Wait 60 seconds with no requests, then sign in with the secure fixture `admin` / `Orbit-Lab-Only!2026#Anchor`. Use the log tail from README to show failed, restricted and successful events without passwords.

## Request contract

```http
POST /admin HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=admin&password=Avenor2026%21
```

Vulnerable failure: HTTP 200 containing exactly `Invalid username or password` as the error text. Success: HTTP 302 with `Location: /admin/dashboard`, a signed session cookie and no failure text. Secure restrictions: HTTP 429 containing the same failure text. Login has no dynamic token so the bounded lab exercise is repeatable. Logout is POST with a session CSRF token. Visiting the dashboard without a valid session redirects to `/admin`.

The weak training credential is `admin` / `Avenor2026!`, seventh in the list. Password hashes use scrypt; cracking/storage flaws are outside this lesson. A hidden endpoint is not an access control. Secure mode remains an educational HTTP lab, not a production deployment: production also requires HTTPS, distributed throttling, MFA and appropriately managed credentials.

After presenting: Ctrl+C, remove the scoped firewall rule, and restore the PC's normal networking. Reset in vulnerable mode before the next seminar if desired.

## Fictional OSINT teaching cue

Before automation, ask the audience to notice the public company name (Avenor) and the footer year (2026). Explain how predictable choices can combine a company name, current year and a common suffix into `Avenor2026!`. This is an intentionally constructed fictional scenario, not evidence that real organizations use this password. The supplied list includes that candidate seventh. Social engineering can be discussed as another way organizational context becomes known; no contacting or deceiving people is required.

## Optional role comparison

After the administrator proof, log out and sign in as alex.scott (vulnerable fixture: alexscott_may52002). Show the staff workspace, then manually request /admin/dashboard and show HTTP 403. Log out before testing support.account (vulnerable fixture: supportaccount@2026). Its support workspace is also denied administrator access. Use SCENARIO_MATERIALS.md for the simulated onboarding/helpdesk clues; these were invented, not obtained from real people. Keep the main live automation focused on one named account.
