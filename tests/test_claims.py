from tests.support import WebTest


class ClaimTests(WebTest):
    def test_consent_required_and_revocation(self):
        self.login()
        self.assertEqual(self.client.get('/claims').status_code, 302)
        self.assertEqual(self.client.get('/claims/1').status_code, 302)
        self.post('/consent', {'action': 'grant'})
        self.assertEqual(self.client.get('/claims').status_code, 200)
        self.post('/consent', {'action': 'revoke'})
        self.assertEqual(self.client.get('/claims/1').status_code, 302)
        self.assertEqual(self.client.get('/claims').status_code, 302)

    def test_only_own_claims(self):
        self.login()
        self.post('/consent', {'action': 'grant'})
        text = self.client.get('/claims?user_id=2').get_data(as_text=True)
        self.assertIn('BX-2026-001', text)
        self.assertNotIn('BX-2026-004', text)
        self.assertEqual(self.client.get('/claims/4').status_code, 404)
        self.login('employee2')
        self.post('/consent', {'action': 'grant'})
        self.assertEqual(self.client.get('/claims/1').status_code, 404)

    def test_finance_only_verification(self):
        for user in ['employee', 'qiao']:
            self.login(user)
            self.assertEqual(self.post('/finance/claims/1/verify', {'status': '已付款', 'note': '核对通过'}).status_code, 403)

    def test_verification_note_required(self):
        self.login('zhou')
        self.assertEqual(self.post('/finance/claims/1/verify', {'status': '已付款', 'note': ' '}).status_code, 400)
        self.assertEqual(self.post('/finance/claims/1/verify', {'status': '已付款', 'note': '教学数据已核对'}).status_code, 302)
        row = self.sql('SELECT * FROM claims WHERE id=1')[0]
        self.assertEqual(row['status'], '已付款')
        self.assertEqual(row['verified'], 1)
        self.assertIsNotNone(row['verified_at'])
        self.assertEqual(self.sql('SELECT display_name FROM users WHERE id=?', (row['verified_by'],))[0]['display_name'], '周敏')

    def test_amount_and_invalid_status(self):
        self.sql('UPDATE claims SET amount_cents=12345 WHERE id=1')
        self.login()
        self.post('/consent', {'action': 'grant'})
        text = self.client.get('/claims/1').get_data(as_text=True)
        self.assertIn('123.45', text)
        self.assertIn('待周敏核对', text)
        self.login('zhou')
        self.assertEqual(self.post('/finance/claims/1/verify', {'status': '乱填', 'note': '测试'}).status_code, 400)

    def test_admin_and_finance_cannot_use_employee_consent(self):
        for user in ['qiao', 'zhou']:
            self.login(user)
            self.assertEqual(self.post('/consent', {'action': 'grant'}).status_code, 403)

    def test_consent_persists_after_login(self):
        self.login()
        self.post('/consent', {'action': 'grant'})
        self.post('/logout')
        self.login()
        self.assertEqual(self.client.get('/claims').status_code, 200)
