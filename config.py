import os
from dotenv import load_dotenv

load_dotenv()
VULNERABLE_MODE = os.getenv('VULNERABLE_MODE', 'true').lower() == 'true'
PRIVILEGE_ESCALATION_DEMO = os.getenv('PRIVILEGE_ESCALATION_DEMO', 'false').lower() == 'true'
DATABASE_URL = os.getenv('DATABASE_URL', '')
SECRET_KEY = os.getenv('SECRET_KEY', '')
DEMO_PASSWORD = 'Avenor2026!'
SECURE_PASSWORD = 'Orbit-Lab-Only!2026#Anchor'
# Fictional training fixtures only. Secure fixtures are not production secrets.
DEMO_ACCOUNTS = (
    ('admin', 'admin', DEMO_PASSWORD, SECURE_PASSWORD),
    ('alex.scott', 'staff', 'alexscott_may52002', 'Alex-Lab-Only!2026#Meadow'),
    ('support.account', 'support', 'supportaccount@2026', 'Support-Lab-Only!2026#Harbor'),
)

def validate():
    if not DATABASE_URL.startswith(('postgresql://', 'postgresql+psycopg2://')):
        raise RuntimeError('Set DATABASE_URL to a PostgreSQL URL in .env.')
    if len(SECRET_KEY) < 32 or SECRET_KEY == 'REPLACE_WITH_RANDOM_SECRET':
        raise RuntimeError('Set SECRET_KEY to a random value of at least 32 characters.')
