from functools import wraps
import secrets
from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from app.db import get_db

bp = Blueprint('auth', __name__)


def load_user():
    g.user = get_db().execute('SELECT * FROM users WHERE id=?', (session.get('user_id'),)).fetchone()
    session.setdefault('csrf_token', secrets.token_hex(32))


def check_csrf() -> None:
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        token = request.form.get('csrf_token', '')
        if not token or not token.isascii() or not secrets.compare_digest(token, session['csrf_token']):
            abort(400)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def role_required(role: str):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user['role'] != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = get_db().execute('SELECT * FROM users WHERE username=?', (request.form.get('username', '').strip(),)).fetchone()
        if user and check_password_hash(user['password_hash'], request.form.get('password', '')):
            session.clear()
            session['user_id'] = user['id']
            session['csrf_token'] = secrets.token_hex(32)
            target = {'admin': 'policies.admin_list', 'finance': 'claims.finance_list', 'employee': 'policies.index'}
            return redirect(url_for(target[user['role']]))
        error = '账号或密码不正确，请检查后重试。'
    return render_template('login.html', error=error), 400 if error else 200


@bp.post('/logout')
def logout():
    session.clear()
    flash('已退出登录。', 'success')
    return redirect(url_for('policies.index'))
