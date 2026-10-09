from datetime import date, datetime
import re
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from app.auth import role_required
from app.db import get_db

bp = Blueprint('policies', __name__)
FIELDS = ('series_key', 'title', 'category', 'keywords', 'version', 'scope', 'content', 'effective_date', 'expiry_date')


def find_policies(query: str, today: date) -> list:
    rows = get_db().execute('SELECT p.*,u.display_name AS maintainer FROM policies p JOIN users u ON u.id=p.updated_by WHERE enabled=1 AND effective_date<=? AND (expiry_date IS NULL OR expiry_date>?) ORDER BY p.id', (today.isoformat(), today.isoformat())).fetchall()
    query = query.strip().lower()
    if not query:
        return rows
    aliases = {'打车': '交通', '出租车': '交通', '酒店': '住宿', '宾馆': '住宿', '住店': '住宿', '高铁': '交通', '机票': '交通', '材料': '凭证', '电子票': '发票'}
    topics = [word for word in ['交通', '住宿', '发票', '凭证', '补贴', '餐费'] if word in query]
    for key, value in aliases.items():
        if key in query:
            topics.append(value)
    if topics:
        # 主题只匹配标题、分类和关键词，不能因正文偶然提及而跨主题推荐。
        return [r for r in rows if any(w in ' '.join(r[k] for k in ('title', 'category', 'keywords')).lower() for w in topics)]
    if query in ('报销', '出差', '标准', '提交'):
        words = [query]
    else:
        cleaned = re.sub(r'怎么|如何|报销|标准|规定|费用|多少|是什么|需要|哪些|可以|能否|的|？|\?', '', query)
        words = [w for w in re.split(r'\s+', cleaned) if w]
    return [r for r in rows if any(w in ' '.join(r[k] for k in ('title', 'category', 'keywords', 'content')).lower() for w in words)]


def save_policy(data: dict, actor_id: int, policy_id: int | None = None) -> int:
    values = {field: data.get(field, '').strip() for field in FIELDS}
    for field in ['series_key', 'title', 'category', 'version', 'scope', 'content', 'effective_date']:
        if not values[field]:
            raise ValueError('请填写全部必填项目。')
    if any(len(v) > (20000 if k == 'content' else 200) for k, v in values.items()):
        raise ValueError('字段过长，正文最多 20000 字，其他字段最多 200 字。')
    try:
        begin = date.fromisoformat(values['effective_date'])
        end = date.fromisoformat(values['expiry_date']) if values['expiry_date'] else None
    except ValueError:
        raise ValueError('日期格式不正确。') from None
    if end and end <= begin:
        raise ValueError('失效日期必须晚于生效日期；失效当天起不再有效。')
    values['effective_date'] = begin.isoformat()
    values['expiry_date'] = end.isoformat() if end else None
    enabled = 1 if data.get('enabled') == '1' else 0
    db = get_db()
    try:
        db.execute('BEGIN IMMEDIATE')
        if enabled:
            overlap = db.execute("SELECT id FROM policies WHERE series_key=? AND enabled=1 AND id!=? AND (? IS NULL OR effective_date < ?) AND (expiry_date IS NULL OR expiry_date>?)", (values['series_key'], policy_id if policy_id is not None else -1, values['expiry_date'], values['expiry_date'], values['effective_date'])).fetchone()
            if overlap:
                raise ValueError('同一制度系列存在有效日期重叠，请先调整旧版失效日期。')
        params = [values[k] for k in FIELDS] + [enabled, actor_id, datetime.now().isoformat(timespec='seconds')]
        if policy_id is None:
            marks = ','.join('?' for _ in params)
            cursor = db.execute(f"INSERT INTO policies ({','.join(FIELDS)},enabled,updated_by,updated_at) VALUES ({marks})", params)
            policy_id = cursor.lastrowid
        else:
            columns = (*FIELDS, 'enabled', 'updated_by', 'updated_at')
            db.execute(f"UPDATE policies SET {','.join(k+'=?' for k in columns)} WHERE id=?", [*params, policy_id])
        db.commit()
    except Exception:
        db.rollback()
        raise
    return policy_id


@bp.get('/')
def index():
    query = request.args.get('q', '').strip()[:200]
    policies = find_policies(query, date.today())
    return render_template('index.html', policies=policies, query=query, today=date.today().isoformat())


@bp.get('/policies/<int:policy_id>')
def detail(policy_id):
    policy = next((r for r in find_policies('', date.today()) if r['id'] == policy_id), None)
    if policy is None:
        abort(404)
    return render_template('policy_detail.html', policy=policy)


@bp.get('/admin/policies')
@role_required('admin')
def admin_list():
    rows = get_db().execute('SELECT * FROM policies ORDER BY enabled DESC,id DESC').fetchall()
    return render_template('admin_policies.html', policies=rows, today=date.today().isoformat())


@bp.route('/admin/policies/new', methods=['GET', 'POST'])
@bp.route('/admin/policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit(policy_id=None):
    policy = get_db().execute('SELECT * FROM policies WHERE id=?', (policy_id,)).fetchone() if policy_id is not None else None
    if policy_id is not None and not policy:
        abort(404)
    error = None
    if request.method == 'POST':
        try:
            save_policy(request.form, g.user['id'], policy_id)
            flash('制度已保存，员工查询将按有效日期显示。', 'success')
            return redirect(url_for('policies.admin_list'))
        except ValueError as exc:
            error = str(exc)
            policy = request.form
    return render_template('policy_form.html', policy=policy, error=error, editing=policy_id is not None), 400 if error else 200


@bp.post('/admin/policies/<int:policy_id>/toggle')
@role_required('admin')
def toggle(policy_id):
    policy = get_db().execute('SELECT * FROM policies WHERE id=?', (policy_id,)).fetchone()
    if policy is None:
        abort(404)
    try:
        save_policy({**dict(policy), 'expiry_date': policy['expiry_date'] or '', 'enabled': '0' if policy['enabled'] else '1'}, g.user['id'], policy_id)
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('policies.admin_list'))
    flash('制度状态已更新。', 'success')
    return redirect(url_for('policies.admin_list'))
