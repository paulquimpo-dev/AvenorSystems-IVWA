from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from io import BytesIO
import json
import logging
import secrets
import threading
import time

from flask import Flask, abort, redirect, render_template, request, session, url_for, send_file, g
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException
import config
from models import User, database
from discovery_routes import REDIRECTS, RESTRICTED

FAILURE = 'Invalid username or password'

def create_app():
    app = Flask(__name__)
    engine, sessions = database()
    app.config.update(SECRET_KEY=config.SECRET_KEY, MAX_CONTENT_LENGTH=16384,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      PERMANENT_SESSION_LIFETIME=timedelta(minutes=20))
    app.extensions['lab_engine'] = engine

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {
            400: ('Request not understood', 'Please check your input and try again.'),
            401: ('Authentication required', 'This resource requires a valid sign-in.'),
            403: ('Access restricted', 'Public access to this resource is not available.'),
            404: ('Page not found', 'The page may have moved, or the address may be incorrect.'),
            405: ('Request method not allowed', 'This page does not support that type of request.'),
            413: ('Request too large', 'Please reduce the amount of information and try again.'),
            429: ('Please wait a moment', 'Too many requests have been received. Try again shortly.'),
            500: ('Something went wrong', 'We could not complete this request. Please try again later.'),
            503: ('Temporarily unavailable', 'The service is currently unavailable. Please try again later.'),
        }
        title, message = messages.get(error.code, ('Request could not be completed',
                                                   'Please return to the homepage or try again later.'))
        # Preserve protocol headers such as Allow and Retry-After, and the real status.
        response = error.get_response()
        response.data = render_template('error.html', code=error.code, title=title, message=message)
        response.content_type = 'text/html; charset=utf-8'
        return response
    Path('logs').mkdir(exist_ok=True)
    logger = logging.getLogger('lab.auth')
    if not logger.handlers:
        handler = RotatingFileHandler('logs/auth.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    attempts = defaultdict(deque)
    mutex = threading.Lock()
    dummy_hash = generate_password_hash('dummy-unusable-account-password')

    def log(username, outcome):
        logger.info(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                                   username=username[:80], source_ip=request.remote_addr, outcome=outcome)))

    def limited():
        now = time.monotonic()
        with mutex:
            for ip in list(attempts):
                while attempts[ip] and attempts[ip][0] <= now - 60:
                    attempts[ip].popleft()
                if not attempts[ip]:
                    del attempts[ip]
            bucket = attempts[request.remote_addr]
            if len(bucket) >= 5:
                return True
            bucket.append(now)
        return False

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        if request.path.startswith(('/admin', '/workspace', '/api/account')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/')
    def index():
        return render_template('index.html', active='Home')

    @app.get('/products')
    def products():
        return render_template('products.html', active='Products')

    @app.get('/about')
    def about():
        return render_template('about.html', active='About')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        return render_template('contact.html', active='Contact', sent=request.method == 'POST')

    # Read-only discovery fixtures: no file access, uploads or management actions.
    discovery_pages = {
        '/support': ('Customer support', 'A little help goes a long way.',
                     'Our fictional support team helps teams get more from Avenor.',
                     [('Getting started', 'Explore the product family and plan your workspace.'),
                      ('Contact the team', 'Use the demonstration contact form for a sample enquiry.')]),
        '/faq': ('Frequently asked questions', 'Answers at a glance.',
                 'A few things to know about the Avenor product family.',
                 [('What does Avenor offer?', 'Flow, Signal and Connect bring operations, insights and collaboration together.'),
                  ('Can I request a walkthrough?', 'Our contact page provides a demonstration enquiry form.')]),
        '/careers': ('Careers', 'Build something thoughtful.',
                     'A fictional look at life at Avenor Systems.',
                     [('Our approach', 'Clear communication, curiosity and practical problem solving.'),
                      ('Open opportunities', 'There are no real vacancies or applications on this demonstration site.')]),
        '/news': ('Company news', 'Notes from Avenor.',
                  'Illustrative updates from our fictional team.',
                  [('October 2026 · Product perspective', 'A shared workspace can make everyday coordination easier.'),
                   ('September 2026 · Design journal', 'Our product family takes a consistent approach to clear information.')]),
        '/status': ('Service status', 'All systems operational.',
                    'Illustrative service information, not live infrastructure monitoring.',
                    [('Flow', 'Operational'), ('Signal', 'Operational'), ('Connect', 'Operational')]),
    }

    def discovery_page():
        title, heading, intro, sections = discovery_pages[request.path]
        return render_template('discovery.html', title=title, heading=heading,
                               intro=intro, sections=sections)

    for path in discovery_pages:
        app.add_url_rule(path, endpoint='discovery_' + path[1:], view_func=discovery_page, methods=['GET'])

    @app.get('/docs')
    @app.get('/documentation')
    def documentation():
        return render_template('documentation.html')

    @app.get('/download')
    @app.get('/downloads')
    def downloads():
        return render_template('downloads.html')

    @app.get('/downloads/<filename>')
    def download_file(filename):
        # Fixed catalog only; never resolve a user-provided filesystem path.
        catalog = {
            'avenor-getting-started.txt': ('text/plain',
                'AVENOR SYSTEMS — GETTING STARTED\nFictional product walkthrough\n\n'
                '1. Explore Flow, Signal and Connect on the Products page.\n'
                '2. Review the documentation for a sample workflow.\n'
                '3. Download the sample orders CSV to inspect its fictional records.\n'
                '4. Visit Contact to try a local demonstration enquiry.\n'
                'This sample does not install software or connect to a service.\n'),
            'sample-orders.csv': ('text/csv',
                'order_id,product,quantity,status\nDEMO-1001,Flow,3,Completed\n'
                'DEMO-1002,Signal,2,Processing\nDEMO-1003,Connect,5,Completed\n'),
            'workspace-checklist.txt': ('text/plain',
                'AVENOR WORKSPACE PLANNING CHECKLIST\nFictional planning resource\n\n'
                '[ ] Identify the workflow your team wants to improve.\n'
                '[ ] Assign a workflow owner.\n[ ] Define the stages of work.\n'
                '[ ] Agree on reporting measures.\n[ ] Schedule a review.\n'),
        }
        if filename not in catalog:
            abort(404)
        mime, content = catalog[filename]
        return send_file(BytesIO(content.encode('utf-8')), mimetype=mime,
                         as_attachment=True, download_name=filename)

    @app.get('/events')
    def events():
        return render_template('events.html')

    @app.get('/events/workspace-session.ics')
    def event_calendar():
        calendar = '\r\n'.join([
            'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Avenor//Demo Events//EN',
            'BEGIN:VEVENT', 'UID:workspace-session-20261112@avenor.example',
            'DTSTAMP:20261017T000000Z', 'DTSTART:20261112T020000Z',
            'DTEND:20261112T024500Z', 'SUMMARY:Avenor workspace walkthrough (fictional)',
            'DESCRIPTION:Fictional demonstration event. No real meeting or registration.',
            'LOCATION:Demo workspace - no live meeting', 'END:VEVENT', 'END:VCALENDAR', '',
        ])
        return send_file(BytesIO(calendar.encode('utf-8')), mimetype='text/calendar',
                         as_attachment=True, download_name='avenor-workspace-session.ics')

    @app.get('/backup')
    @app.get('/uploads')
    @app.get('/private')
    def restricted_resource():
        # These names are fixtures only: no backup files or upload handlers exist.
        abort(403)

    def legacy_resource():
        return redirect(REDIRECTS[request.path])

    for number, path in enumerate(REDIRECTS):
        app.add_url_rule(path, endpoint=f'legacy_resource_{number}',
                         view_func=legacy_resource, methods=['GET'])
    for number, path in enumerate(RESTRICTED):
        app.add_url_rule(path, endpoint=f'restricted_resource_{number}',
                         view_func=restricted_resource, methods=['GET'])

    @app.route('/admin', methods=['GET', 'POST'])
    def login():
        error, status = None, 200
        if request.method == 'POST':
            username = request.form.get('username', '')[:80]
            password = request.form.get('password', '')
            # INTENTIONALLY VULNERABLE FOR LOCAL TRAINING
            # Repeated authentication attempts are deliberately not rate-limited.
            # DO NOT deploy this configuration publicly.
            if not config.VULNERABLE_MODE and limited():
                log(username, 'rate_limited')
                return render_template('admin_login.html', error=FAILURE, restricted=True), 429, {'Retry-After': '60'}
            with sessions.begin() as db:
                user = db.scalar(select(User).where(User.username == username).with_for_update())
                now = datetime.now(timezone.utc)
                locked = user and user.locked_until and user.locked_until > now
                valid = check_password_hash(user.password_hash if user else dummy_hash, password)
                mode_ok = config.VULNERABLE_MODE or (user and user.credential_mode == 'secure')
                if not config.VULNERABLE_MODE and locked:
                    log(username, 'locked')
                    error, status = FAILURE, 429
                elif valid and user and mode_ok and user.role in ('admin', 'staff', 'support'):
                    user.failed_attempts = 0
                    user.locked_until = None
                    session.clear()
                    session.update(uid=user.id, version=user.session_version, csrf=secrets.token_urlsafe(24),
                                   mode=config.VULNERABLE_MODE)
                    session.permanent = True
                    log(username, 'success')
                    return redirect(url_for({'admin': 'dashboard', 'staff': 'staff_workspace',
                                             'support': 'support_workspace'}[user.role]))
                else:
                    if user and not config.VULNERABLE_MODE:
                        if user.locked_until and user.locked_until <= now:
                            user.failed_attempts = 0
                            user.locked_until = None
                        user.failed_attempts += 1
                        if user.failed_attempts >= 5:
                            user.locked_until = now + timedelta(seconds=60)
                    log(username, 'failure' if mode_ok else 'reset_required')
                    error = FAILURE
        response = app.make_response((render_template('admin_login.html', error=error, restricted=status == 429), status))
        if status == 429:
            response.headers['Retry-After'] = '60'
        return response

    def authenticated(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with sessions() as db:
                user = db.get(User, session.get('uid')) if session.get('uid') else None
                if not user or user.role not in ('admin', 'staff', 'support') or user.session_version != session.get('version') or session.get('mode') != config.VULNERABLE_MODE:
                    session.clear()
                    return redirect(url_for('login'))
                # Read authorization from the database on every request, not a form or cookie role.
                g.current_user = user
            return fn(*args, **kwargs)
        return wrapper

    @app.get('/admin/dashboard')
    @authenticated
    def dashboard():
        if g.current_user.role != 'admin':
            abort(403)
        return render_template('dashboard.html', vulnerable=config.VULNERABLE_MODE)

    @app.get('/workspace/staff')
    @authenticated
    def staff_workspace():
        if g.current_user.role not in ('staff', 'admin'):
            abort(403)
        return render_template('workspace.html', role='Staff', username=g.current_user.username,
                               heading='Your daily workspace.',
                               records=[('FLOW-104', 'Review sample product notes', 'In progress'),
                                        ('FLOW-108', 'Prepare weekly team summary', 'Planned')])

    @app.get('/workspace/support')
    @authenticated
    def support_workspace():
        if g.current_user.role not in ('support', 'admin'):
            abort(403)
        return render_template('workspace.html', role='Support', username=g.current_user.username,
                               heading='Your support queue.',
                               records=[('DEMO-201', 'Sample workspace question', 'Open'),
                                        ('DEMO-204', 'Sample reporting enquiry', 'Awaiting review')])

    @app.get('/workspace/access')
    @authenticated
    def access_review():
        return render_template('access_review.html', account=g.current_user)

    @app.post('/api/account/role')
    @authenticated
    def update_own_role():
        # Keep CSRF protection: this lesson is missing authorization, not CSRF.
        if not secrets.compare_digest(request.form.get('csrf', ''), session.get('csrf', '')):
            abort(400)
        requested = request.form.get('role', '')
        if requested not in ('staff', 'support', 'admin'):
            abort(400)
        with sessions.begin() as db:
            actor = db.scalar(select(User).where(User.id == g.current_user.id).with_for_update())
            if not actor or actor.session_version != session.get('version'):
                abort(403)
            old_role = actor.role
            # INTENTIONALLY VULNERABLE FOR LOCAL TRAINING ONLY.
            # The demo branch checks login but omits the administrator permission check.
            # Limit changes to the caller's own named fictional fixture account.
            fixture = actor.username in ('alex.scott', 'support.account')
            allowed = actor.role == 'admin' or (config.PRIVILEGE_ESCALATION_DEMO and fixture)
            logger.info(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                                       event='role_change', username=actor.username,
                                       source_ip=request.remote_addr, previous_role=old_role,
                                       requested_role=requested,
                                       outcome='allowed' if allowed else 'denied')))
            if not allowed:
                abort(403)
            # The exercise never changes another user or grants OS-level permissions.
            actor.role = requested
        return render_template('role_result.html', previous=old_role, current=requested)

    @app.post('/admin/logout')
    @authenticated
    def logout():
        if not secrets.compare_digest(request.form.get('csrf', ''), session['csrf']):
            abort(400)
        session.clear()
        return redirect(url_for('login'))

    return app

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=5000, debug=False, threaded=True)
