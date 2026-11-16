"""Integration checks against a dedicated disposable PostgreSQL database."""
import os
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if not os.getenv('LAB_TEST_DATABASE_URL'):
    raise SystemExit('Set LAB_TEST_DATABASE_URL to a disposable PostgreSQL database first.')
os.environ['DATABASE_URL'] = os.environ['LAB_TEST_DATABASE_URL']
os.environ['SECRET_KEY'] = 'integration-test-only-secret-key-0123456789'

import config
from app import FAILURE, create_app
from models import User, database
from reset_demo import reset
from sqlalchemy import select
from werkzeug.security import check_password_hash


class LabTests(unittest.TestCase):
    def setUp(self):
        config.VULNERABLE_MODE = True
        config.PRIVILEGE_ESCALATION_DEMO = False
        reset()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions['lab_engine'].dispose()

    def post(self, password='wrong-fixture', client=None, username='admin'):
        return (client or self.client).post('/admin', data=dict(username=username, password=password))

    def test_public_routes_and_fixtures(self):
        for path in ['/', '/products', '/about', '/contact']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b'/admin', response.data)
        for path in ['/not-a-route', '/robots.txt', '/sitemap.xml']:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get('/admin').status_code, 200)
        self.assertIn('admin', Path('demo_paths.txt').read_text().splitlines())
        self.assertIn(config.DEMO_PASSWORD, Path('demo_passwords.txt').read_text().splitlines())
        response = self.client.post('/contact', data={'name': '<script>demo</script>'})
        self.assertNotIn(b'<script>', response.data)

    def test_vulnerable_login_logout_and_hash(self):
        self.assertEqual(self.client.get('/admin/dashboard').location, '/admin')
        for _ in range(7):
            response = self.post()
            self.assertEqual(response.status_code, 200)
            self.assertIn(FAILURE.encode(), response.data)
        response = self.post(config.DEMO_PASSWORD)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/admin/dashboard')
        self.assertNotIn(FAILURE.encode(), response.data)
        page = self.client.get('/admin/dashboard')
        self.assertEqual(page.status_code, 200)
        self.assertEqual(self.client.post('/admin/logout').status_code, 400)
        token = re.search(rb'name="csrf" value="([^"]+)"', page.data).group(1).decode()
        self.assertEqual(self.client.post('/admin/logout', data={'csrf': token}).status_code, 302)
        self.assertEqual(self.client.get('/admin/dashboard').location, '/admin')
        engine, sessions = database()
        with sessions() as db:
            user = db.scalar(select(User).where(User.username == 'admin'))
            self.assertNotEqual(user.password_hash, config.DEMO_PASSWORD)
            self.assertTrue(check_password_hash(user.password_hash, config.DEMO_PASSWORD))
        engine.dispose()

    def test_secure_ip_limit_unknown_user(self):
        config.VULNERABLE_MODE = False
        reset()
        for _ in range(5):
            self.assertEqual(self.post(username='unknown').status_code, 200)
        response = self.post(username='unknown')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '60')
        self.assertIn(FAILURE.encode(), response.data)

    def test_secure_lockout_and_recovery(self):
        config.VULNERABLE_MODE = False
        reset()
        for i in range(5):
            response = self.client.post('/admin', data={'username': 'admin', 'password': 'wrong'},
                                        environ_overrides={'REMOTE_ADDR': f'127.0.0.{i+2}'})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.post(config.SECURE_PASSWORD).status_code, 429)
        # Advance only the account deadline to test recovery without sleeping.
        from datetime import datetime, timedelta, timezone
        engine, sessions = database()
        with sessions.begin() as db:
            user = db.scalar(select(User).where(User.username == 'admin'))
            user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        engine.dispose()
        self.assertEqual(self.post(config.SECURE_PASSWORD).status_code, 302)
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 200)

    def test_reset_invalidates_sessions_and_mode_requires_reset(self):
        self.post(config.DEMO_PASSWORD)
        reset()
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 302)
        config.VULNERABLE_MODE = False
        self.assertIn(FAILURE.encode(), self.post(config.DEMO_PASSWORD).data)
        reset()
        self.assertEqual(self.post(config.SECURE_PASSWORD).status_code, 302)

    def test_logs_do_not_contain_passwords(self):
        marker = 'unique-password-never-log-52630'
        self.post(marker, username='test\nforged')
        content = Path('logs/auth.log').read_text(encoding='utf-8')
        self.assertNotIn(marker, content)
        import json
        event = json.loads(content.splitlines()[-1])
        self.assertEqual(event['username'], 'test\nforged')
        self.assertIn('source_ip', event)
        self.assertIn('timestamp', event)

    def test_role_permissions_logout_and_reset_for_all_accounts(self):
        for secure in (False, True):
            config.VULNERABLE_MODE = not secure
            reset()
            # Fresh app clears the intentionally shared per-IP limit between scenarios.
            app = create_app()
            try:
                for username, role, weak, strong in config.DEMO_ACCOUNTS:
                    client = app.test_client()
                    home = {'admin': '/admin/dashboard', 'staff': '/workspace/staff',
                            'support': '/workspace/support'}[role]
                    self.assertEqual(client.get(home).location, '/admin')
                    response = client.post('/admin', data={'username': username,
                                                           'password': strong if secure else weak})
                    self.assertEqual(response.location, home)
                    self.assertEqual(client.get(home).status_code, 200)
                    for path, allowed in [('/admin/dashboard', role == 'admin'),
                                          ('/workspace/staff', role in ('admin', 'staff')),
                                          ('/workspace/support', role in ('admin', 'support'))]:
                        self.assertEqual(client.get(path).status_code, 200 if allowed else 403)
                    page = client.get(home)
                    token = re.search(rb'name="csrf" value="([^"]+)"', page.data).group(1).decode()
                    self.assertEqual(client.post('/admin/logout', data={'csrf': token}).status_code, 302)
                    self.assertEqual(client.get(home).location, '/admin')
                client = app.test_client()
                client.post('/admin', data={'username': 'alex.scott',
                                            'password': config.DEMO_ACCOUNTS[1][3 if secure else 2]})
                reset()
                self.assertEqual(client.get('/workspace/staff').location, '/admin')
            finally:
                app.extensions['lab_engine'].dispose()

    def test_account_lockout_is_independent_but_ip_limit_is_shared(self):
        config.VULNERABLE_MODE = False
        reset()
        for i in range(5):
            self.client.post('/admin', data={'username': 'alex.scott', 'password': 'wrong'},
                             environ_overrides={'REMOTE_ADDR': f'127.0.1.{i+1}'})
        self.assertEqual(self.client.post('/admin', data={'username': 'alex.scott',
                         'password': config.DEMO_ACCOUNTS[1][3]}).status_code, 429)
        self.assertEqual(self.client.post('/admin', data={'username': 'support.account',
                         'password': config.DEMO_ACCOUNTS[2][3]}).status_code, 302)
        for _ in range(3):
            self.post(username='unknown')
        # The five attempts above from this IP span different accounts.
        self.assertEqual(self.post(config.SECURE_PASSWORD).status_code, 429)

    def test_optional_privilege_escalation_and_authorization_fix(self):
        for weak_login in (True, False):
            config.VULNERABLE_MODE = weak_login
            for enabled in (False, True):
                config.PRIVILEGE_ESCALATION_DEMO = enabled
                reset()
                client = self.app.test_client()
                self.assertEqual(client.post('/api/account/role', data={'role': 'admin'}).location, '/admin')
                password = config.DEMO_ACCOUNTS[1][2 if weak_login else 3]
                client.post('/admin', data={'username': 'alex.scott', 'password': password})
                self.assertEqual(client.get('/admin/dashboard').status_code, 403)
                page = client.get('/workspace/access')
                self.assertEqual(page.status_code, 200)
                token = re.search(rb'name="csrf" value="([^"]+)"', page.data).group(1).decode()
                self.assertEqual(client.post('/api/account/role', data={'role': 'admin'}).status_code, 400)
                self.assertEqual(client.post('/api/account/role', data={'csrf': token, 'role': 'root'}).status_code, 400)
                response = client.post('/api/account/role', data={'csrf': token, 'role': 'admin', 'username': 'admin'})
                self.assertEqual(response.status_code, 200 if enabled else 403)
                self.assertEqual(client.get('/admin/dashboard').status_code, 200 if enabled else 403)
                engine, sessions = database()
                with sessions() as db:
                    alex = db.scalar(select(User).where(User.username == 'alex.scott'))
                    support = db.scalar(select(User).where(User.username == 'support.account'))
                    self.assertEqual(alex.role, 'admin' if enabled else 'staff')
                    self.assertEqual(support.role, 'support')
                engine.dispose()
                reset()
                self.assertEqual(client.get('/admin/dashboard').location, '/admin')
        import json
        events = [json.loads(line) for line in Path('logs/auth.log').read_text().splitlines()]
        changes = [e for e in events if e.get('event') == 'role_change']
        self.assertTrue(any(e['outcome'] == 'allowed' for e in changes))
        self.assertTrue(any(e['outcome'] == 'denied' for e in changes))

if __name__ == '__main__':
    unittest.main(verbosity=2)
