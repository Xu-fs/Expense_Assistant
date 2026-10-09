from tests.support import WebTest


class AuthTests(WebTest):
    def test_login_and_logout(self):
        self.assertEqual(self.post('/login', {'username': 'employee', 'password': 'bad'}).status_code, 400)
        self.assertEqual(self.login().status_code, 302)
        with self.client.session_transaction() as s:
            self.assertIsNotNone(s.get('user_id'))
        self.post('/logout')
        self.assertEqual(self.client.get('/claims').status_code, 302)

    def test_forged_role_ignored(self):
        self.login()
        with self.client.session_transaction() as s:
            s['role'] = 'admin'
        self.assertEqual(self.client.get('/admin/policies').status_code, 403)

    def test_missing_csrf_rejected(self):
        self.assertEqual(self.client.post('/login', data={'username': 'employee', 'password': 'demo123'}).status_code, 400)

    def test_malformed_csrf_is_bad_request(self):
        self.csrf()
        self.assertEqual(self.client.post('/login', data={'csrf_token': '中文令牌'}).status_code, 400)

    def test_restart_preserves_data(self):
        from app import create_app
        self.sql("UPDATE policies SET title='持久化检查' WHERE id=1")
        second = create_app(self.config)
        self.assertIn('持久化检查', second.test_client().get('/').get_data(as_text=True))

    def test_password_is_hashed(self):
        self.assertNotEqual(self.sql('SELECT password_hash FROM users LIMIT 1')[0]['password_hash'], 'demo123')
