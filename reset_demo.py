"""Reset only the three named fictional accounts; never drop a database."""
from sqlalchemy import select
from werkzeug.security import generate_password_hash
import config
from models import Base, User, database

def reset():
    engine, sessions = database()
    Base.metadata.create_all(engine)
    with sessions.begin() as db:
        # Migrate previous fixture names without leaving extra working accounts.
        for old_name, new_name in [('alex.demo', 'alex.scott'), ('support.demo', 'support.account')]:
            old = db.scalar(select(User).where(User.username == old_name))
            current = db.scalar(select(User).where(User.username == new_name))
            if old and current is None:
                old.username = new_name
                db.flush()
            elif old:
                old.role = 'retired'
                old.session_version += 1
        for username, role, weak, strong in config.DEMO_ACCOUNTS:
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(username=username, session_version=0)
                db.add(user)
            user.password_hash = generate_password_hash(weak if config.VULNERABLE_MODE else strong)
            user.role = role
            user.failed_attempts = 0
            user.locked_until = None
            user.credential_mode = 'vulnerable' if config.VULNERABLE_MODE else 'secure'
            user.session_version += 1
    engine.dispose()
    print('Demo environment reset successfully.')

if __name__ == '__main__':
    reset()
