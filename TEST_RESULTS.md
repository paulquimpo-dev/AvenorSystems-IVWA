# Verification — 16 October 2026

- Installed dependencies into `.venv` and passed `pip check`.
- Existing PostgreSQL service accepted connections on 5432 but required a password that was not provided. Its databases and configuration were left untouched.
- Initialized a separate disposable PostgreSQL 18 cluster on **127.0.0.1:55432**, using only the dedicated `lab_integration` database, for integration tests.
- All six integration tests passed: public routes and wordlists; repeated vulnerable login attempts, scrypt hashes and logout; secure rate limiting; account lockout and recovery; reset/session invalidation and credential switching; structured logs without passwords.
- Started Flask with debugging off on **0.0.0.0:5000**. Real HTTP requests verified all four public pages, the login portal, CSS, genuine 404s, invalid-login text, signed session cookies and successful dashboard access.
- Reviewed the homepage in the browser at the available narrow viewport and checked the admin form's labels and controls.
- The Flask preview and temporary PostgreSQL server were stopped after testing. The ignored disposable cluster directory remains available for local inspection; it is not part of application setup.

## Remaining environment checks

- The installed `py` launcher points to missing `C:\Python313\python.exe`; the bundled Python runtime was used to create the working project `.venv`. Use `.venv\Scripts\python.exe` directly or repair the system Python installation.
- No `.env` containing your actual PostgreSQL credential was created. Follow README to create a dedicated role/database and configure it.
- `ipconfig` showed Ethernet and the Hyper-V Default Switch, but no VMware VMnet1/VMnet8 adapter. Kali/private VMware connectivity could not be verified. Set up host-only networking and the scoped firewall rule before the seminar.
- Gobuster and Hydra were not available in this Windows test environment. Their HTTP contracts were verified; run the supplied bounded commands on Kali for the final rehearsal.
