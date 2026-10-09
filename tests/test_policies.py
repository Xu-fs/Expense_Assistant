from datetime import date, timedelta
from tests.support import WebTest


class PolicyTests(WebTest):
    def policy(self, **values):
        return {'series_key': 'test-series', 'title': '测试制度', 'category': '其他', 'keywords': '测试',
                'version': 'V1', 'scope': '全体员工', 'content': '测试制度正文',
                'effective_date': '2026-10-01', 'expiry_date': '2026-10-09', 'enabled': '1', **values}

    def test_effective_boundaries(self):
        from app.policies import find_policies
        self.sql('UPDATE policies SET enabled=0')
        self.login('qiao')
        self.assertEqual(self.post('/admin/policies/new', self.policy()).status_code, 302)
        with self.app.app_context():
            self.assertEqual(len(find_policies('', date(2026, 10, 1))), 1)
            self.assertEqual(len(find_policies('', date(2026, 10, 9))), 0)

    def test_hidden_versions_not_public(self):
        ids = self.sql('SELECT id FROM policies WHERE id IN (4,5,6)')
        for row in ids:
            self.assertEqual(self.client.get(f"/policies/{row['id']}").status_code, 404)

    def test_query_no_match(self):
        text = self.client.get('/?q=火星旅行').get_data(as_text=True)
        self.assertIn('没有找到有效制度依据', text)
        self.assertIn('交通', self.client.get('/?q=%20%20').get_data(as_text=True))

    def test_admin_only(self):
        for name in ['employee', 'zhou']:
            self.login(name)
            self.assertEqual(self.post('/admin/policies/new', self.policy()).status_code, 403)

    def test_series_overlap_and_self_edit(self):
        self.login('qiao')
        self.assertEqual(self.post('/admin/policies/new', self.policy()).status_code, 302)
        self.assertEqual(self.post('/admin/policies/new', self.policy(version='V2', effective_date='2026-10-09', expiry_date='')).status_code, 302)
        self.assertEqual(self.post('/admin/policies/new', self.policy(version='V3', effective_date='2026-10-08', expiry_date='')).status_code, 400)
        row = self.sql("SELECT id FROM policies WHERE series_key='test-series' AND version='V1'")[0]
        self.assertEqual(self.post(f"/admin/policies/{row['id']}/edit", self.policy()).status_code, 302)

    def test_invalid_dates(self):
        self.login('qiao')
        for end in ['2026-10-01', '无效日期']:
            self.assertEqual(self.post('/admin/policies/new', self.policy(expiry_date=end)).status_code, 400)

    def test_toggle_and_overlap(self):
        self.login('qiao')
        self.assertEqual(self.post('/admin/policies/1/toggle').status_code, 302)
        self.assertEqual(self.client.get('/policies/1').status_code, 404)

    def test_search_by_question(self):
        self.assertIn('差旅交通', self.client.get('/?q=打车怎么报销').get_data(as_text=True))

    def test_generic_word_does_not_invent_topic_evidence(self):
        for query in ['餐费报销标准', '火星旅行报销标准']:
            text = self.client.get('/', query_string={'q': query}).get_data(as_text=True)
            self.assertIn('没有找到有效制度依据', text)
            self.assertNotIn('350', text)

    def test_nonexistent_zero_policy_not_success(self):
        self.login('qiao')
        self.assertEqual(self.post('/admin/policies/0/edit', self.policy()).status_code, 404)

    def test_unbounded_overlap_at_max_date(self):
        self.login('qiao')
        payload = self.policy(effective_date='9999-12-31', expiry_date='')
        self.assertEqual(self.post('/admin/policies/new', payload).status_code, 302)
        self.assertEqual(self.post('/admin/policies/new', payload).status_code, 400)

    def test_escaped_content_and_banner(self):
        self.sql("UPDATE policies SET content='<script>alert(1)</script>' WHERE id=1")
        text = self.client.get('/policies/1').get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>', text)
        self.assertIn('&lt;script&gt;', text)
        for url in ['/', '/login']:
            self.assertIn('教学演示', self.client.get(url).get_data(as_text=True))
