"""Discovery HTTP contracts; these routes do not require database access."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from discovery_routes import REDIRECTS, RESTRICTED


class DiscoveryTests(unittest.TestCase):
    def test_styled_errors_keep_status_and_protocol_headers(self):
        with patch('app.database', return_value=(None, None)):
            app = create_app()
        app.config.update(TESTING=True, SECRET_KEY='discovery-tests-only')
        client = app.test_client()
        for path, method, status in [('/missing-page', 'get', 404),
                                     ('/private', 'get', 403),
                                     ('/products', 'post', 405)]:
            response = getattr(client, method)(path)
            self.assertEqual(response.status_code, status)
            self.assertIn(b'error-page', response.data)
            self.assertIn(b'/static/css/style.css', response.data)
            self.assertNotIn(b'/admin', response.data)
        self.assertIn('GET', client.post('/products').headers['Allow'])
        response = client.post('/admin', data={'password': 'x' * 17000})
        self.assertEqual(response.status_code, 413)
        self.assertIn(b'error-page', response.data)
        # Exercise generic errors without adding public demonstration routes.
        from werkzeug.exceptions import BadRequest, InternalServerError, TooManyRequests
        with app.test_request_context('/'):
            for error in [BadRequest(), InternalServerError(), TooManyRequests(retry_after=60)]:
                response = app.handle_http_exception(error)
                self.assertEqual(response.status_code, error.code)
                self.assertIn(b'error-page', response.data)
            self.assertEqual(response.headers['Retry-After'], '60')

    def test_discovery_responses_and_public_separation(self):
        # No production connection, account reset or credential changes needed.
        with patch('app.database', return_value=(None, None)):
            app = create_app()
        app.config.update(TESTING=True, SECRET_KEY='discovery-tests-only')
        client = app.test_client()
        public = ['/', '/products', '/about', '/contact', '/support', '/faq',
                  '/careers', '/news', '/docs', '/status', '/documentation',
                  '/download', '/downloads', '/events']
        for path in public:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b'/admin', response.data)
                self.assertEqual(client.head(path).status_code, 200)
        for name, mime, marker in [
                ('avenor-getting-started.txt', 'text/plain', b'GETTING STARTED'),
                ('sample-orders.csv', 'text/csv', b'DEMO-1001,Flow,3,Completed'),
                ('workspace-checklist.txt', 'text/plain', b'PLANNING CHECKLIST')]:
            response = client.get('/downloads/' + name)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, mime)
            self.assertIn('attachment;', response.headers['Content-Disposition'])
            self.assertIn(name, response.headers['Content-Disposition'])
            self.assertIn(marker, response.data)
        calendar = client.get('/events/workspace-session.ics')
        self.assertEqual(calendar.status_code, 200)
        self.assertEqual(calendar.mimetype, 'text/calendar')
        self.assertIn(b'DTSTART:20261112T020000Z\r\n', calendar.data)
        for path in ['/downloads/.env', '/downloads/unknown.txt', '/downloads/../config.py']:
            self.assertEqual(client.get(path).status_code, 404)
        for path in ['/backup', '/uploads', '/private']:
            response = client.get(path)
            self.assertEqual(response.status_code, 403)
            self.assertNotIn(b'/admin', response.data)
            self.assertEqual(client.post(path).status_code, 405)
        for path in ['/not-real-7319', '/backup/secrets.txt', '/uploads/file.txt', '/docs/missing']:
            self.assertEqual(client.get(path).status_code, 404)
        for path, destination in REDIRECTS.items():
            response = client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, destination)
            page = client.get(path, follow_redirects=True)
            self.assertEqual(page.status_code, 200)
            self.assertNotIn(b'/admin', page.data)
        for path in RESTRICTED:
            response = client.get(path)
            self.assertEqual(response.status_code, 403)
            self.assertNotIn(b'/admin', response.data)
            self.assertNotIn(b'ref: refs/', response.data)
            self.assertEqual(client.post(path).status_code, 405)
        self.assertEqual(client.get('/.git/config').status_code, 404)
        self.assertEqual(client.get('/admin').status_code, 200)
        candidates = Path('demo_paths.txt').read_text().splitlines()
        for path in public[4:] + ['/backup', '/uploads', '/private', '/admin']:
            self.assertIn(path.lstrip('/'), candidates)


if __name__ == '__main__':
    unittest.main(verbosity=2)
