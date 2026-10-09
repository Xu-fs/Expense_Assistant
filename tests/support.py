import tempfile
import unittest
from pathlib import Path

try:
    from app import create_app
except ImportError:
    create_app = None


class WebTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(create_app, '网站应用工厂尚未实现')
        scratch = Path(__file__).resolve().parents[1] / 'instance' / 'tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.config = {'TESTING': True, 'DATABASE': str(Path(self.temp.name) / 'test.db'), 'SECRET_KEY': 'testing'}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def csrf(self):
        self.client.get('/login')
        with self.client.session_transaction() as session:
            return session['csrf_token']

    def post(self, url, data=None):
        return self.client.post(url, data={**(data or {}), 'csrf_token': self.csrf()})

    def login(self, username='employee'):
        return self.post('/login', {'username': username, 'password': 'demo123'})

    def sql(self, sql, params=()):
        from app.db import get_db
        with self.app.app_context():
            db = get_db()
            result = db.execute(sql, params).fetchall()
            db.commit()
            return result
