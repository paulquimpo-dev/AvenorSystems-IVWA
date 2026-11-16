# Fictional evidence pack - presenter only

All material below was invented for this local seminar. It is not collected information about real people. Keep this file with presenter materials; it is not a public website route. No contacting or deceiving people is required.

## Public clues already on the website

- Company: Avenor Systems.
- Products: Flow, Signal and Connect.
- Footer year: 2026.
- These support company/product/year combinations. They do not reveal a complete password.

## Simulated onboarding handout

> AVENOR - FICTIONAL TRAINING HANDOUT
> Sample new starter: Alex Scott, account alex.scott, Staff role.
> In this intentionally poor historical practice, this fictional profile lists the display name Alex Scott and a fictional birthday of 5 May 2002. The poor password pattern joined the name, an underscore and the month/day/year. These details are invented for the lab, not real personal information.

Teaching point: an onboarding convention can make initial credentials predictable. Production systems should use unique, expiring activation links or unique temporary secrets, not a shared pattern.

## Simulated helpdesk conversation

> FICTIONAL TRANSCRIPT - NO REAL CONVERSATION OCCURRED
> Presenter: Which sample account covers the helpdesk?
> Sample employee: support.account. Our old training convention combined the account purpose without punctuation, an at sign and the year 2026.

Teaching point: a conversation can disclose a credential pattern. This is simulated evidence, not real social engineering or public OSINT.

## Presenter credentials

| Username | Role | Vulnerable fixture | Secure fixture |
|---|---|---|---|
| admin | Administrator | Avenor2026! | Orbit-Lab-Only!2026#Anchor |
| alex.scott | Staff | alexscott_may52002 | Alex-Lab-Only!2026#Meadow |
| support.account | Support | supportaccount@2026 | Support-Lab-Only!2026#Harbor |

All are documented fictional fixtures. Proper salted hashing is retained for every account.

## Role comparison

All three accounts use POST /admin with username and password fields. Admin success redirects to /admin/dashboard, staff to /workspace/staff and support to /workspace/support. Staff and support receive HTTP 403 at /admin/dashboard even if they type the URL directly. Staff cannot open the support workspace, and support cannot open staff's workspace. Admin can view all three read-only workspaces. All roles can log out.

## Secure-mode comparison

Stop Flask, change VULNERABLE_MODE, reset and restart. Reset restores only these three named accounts, clears their failed counters and invalidates their sessions. Existing schema already has the required fields; no database deletion or migration is needed.

Account lockouts are stored independently per account; the five-attempt per-IP limit remains shared across all usernames. To isolate account-lockout behavior during a test, use the integration suite with different simulated source IPs. In a live demonstration from one Kali IP, switching usernames must not bypass the IP limit. A single IP receiving 429 does not prove every account is locked.

Test one account at a time. For the short live demo, keep admin as the automation target, then sign in manually as staff and attempt /admin/dashboard to show authorization. Use the supplied demonstration wordlist for fictional candidates only.

The project password_list.txt contains the agreed 30 OSINT-inspired fictional candidates plus supportaccount@2026, supporting all three weak accounts. Copy this updated file to Kali. Existing Kali files are not changed automatically.
