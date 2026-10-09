import secrets
from datetime import date
from pathlib import Path
import click
from flask import Flask, render_template
from app.db import init_db, close_db, get_db
from app.seed import seed_demo


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(DATABASE=str(Path(app.instance_path) / 'demo.sqlite3'),
                            SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                            MAX_CONTENT_LENGTH=1024 * 1024)
    if config:
        app.config.update(config)
    if not app.config.get('SECRET_KEY'):
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        key_path = Path(app.instance_path) / 'secret.key'
        try:
            with key_path.open('x', encoding='utf-8') as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config['SECRET_KEY'] = key_path.read_text(encoding='utf-8')
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    from app.auth import bp as auth_bp, load_user, check_csrf
    from app.policies import bp as policies_bp
    from app.claims import bp as claims_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(policies_bp)
    app.register_blueprint(claims_bp)
    app.before_request(load_user)
    app.before_request(check_csrf)

    @app.template_filter('money')
    def money(cents):
        return f'{cents // 100:,}.{cents % 100:02d}'

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error_page(error):
        messages = {400: '请求无效，请刷新页面后重试。', 403: '当前账号没有此操作权限。', 404: '内容不存在或不可访问。', 413: '提交内容过长，请缩短后重试。'}
        return render_template('error.html', message=messages.get(error.code, '操作失败'), code=error.code), error.code

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @app.cli.command('reset-demo')
    @click.option('--yes', is_flag=True, help='明确同意重置教学数据。')
    def reset_demo(yes):
        if not yes:
            raise click.ClickException('此操作会清空教学修改。确认后使用 reset-demo --yes。')
        db = get_db()
        for table in ['claim_history', 'claims', 'consents', 'policies', 'users']:
            db.execute(f'DELETE FROM {table}')
        db.commit()
        seed_demo(date.today())
        click.echo('教学演示数据已重置。')

    with app.app_context():
        init_db()
        seed_demo(date.today())
    return app
