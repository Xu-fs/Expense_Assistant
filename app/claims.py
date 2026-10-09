from datetime import datetime
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from app.auth import role_required
from app.db import get_db

bp = Blueprint('claims', __name__)
STATUSES = ('待核对', '审批中', '待付款', '已付款', '已退回')
CONSENT_VERSION = 'V1.0'


def consent_granted(user_id):
    row = get_db().execute('SELECT granted,version FROM consents WHERE user_id=?', (user_id,)).fetchone()
    return bool(row and row['granted'] and row['version'] == CONSENT_VERSION)


def list_own_claims(user_id: int) -> list:
    return get_db().execute('SELECT c.*,u.display_name AS verifier FROM claims c LEFT JOIN users u ON u.id=c.verified_by WHERE c.user_id=? ORDER BY c.id DESC', (user_id,)).fetchall()


def get_own_claim(user_id: int, claim_id: int):
    return get_db().execute('SELECT c.*,u.display_name AS verifier FROM claims c LEFT JOIN users u ON u.id=c.verified_by WHERE c.user_id=? AND c.id=?', (user_id, claim_id)).fetchone()


def verify_claim(claim_id: int, actor_id: int, status: str, note: str) -> None:
    if status not in STATUSES or not note.strip() or len(note) > 2000:
        raise ValueError('请选择有效状态并填写核对说明（最多 2000 字）。')
    db = get_db()
    if db.execute('SELECT id FROM claims WHERE id=?', (claim_id,)).fetchone() is None:
        abort(404)
    now = datetime.now().isoformat(timespec='seconds')
    with db:
        db.execute('UPDATE claims SET status=?,note=?,verified=?,verified_by=?,verified_at=? WHERE id=?', (status, note.strip(), int(status != '待核对'), actor_id, now, claim_id))
        db.execute('INSERT INTO claim_history (claim_id,status,note,actor_id,created_at) VALUES (?,?,?,?,?)', (claim_id, status, note.strip(), actor_id, now))


@bp.route('/consent', methods=['GET', 'POST'])
@role_required('employee')
def consent():
    if request.method == 'POST':
        action = request.form.get('action')
        if action not in ('grant', 'revoke'):
            abort(400)
        db = get_db()
        db.execute('INSERT INTO consents (user_id,granted,version,updated_at) VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET granted=excluded.granted,version=excluded.version,updated_at=excluded.updated_at', (g.user['id'], int(action == 'grant'), CONSENT_VERSION, datetime.now().isoformat(timespec='seconds')))
        db.commit()
        flash('已授权查询本人单据。' if action == 'grant' else '授权已撤销，系统停止展示本人单据。', 'success')
        return redirect(url_for('claims.own_list' if action == 'grant' else 'claims.consent'))
    record = get_db().execute('SELECT * FROM consents WHERE user_id=?', (g.user['id'],)).fetchone()
    return render_template('consent.html', granted=consent_granted(g.user['id']), record=record, version=CONSENT_VERSION)


@bp.get('/claims')
@role_required('employee')
def own_list():
    if not consent_granted(g.user['id']):
        return redirect(url_for('claims.consent'))
    rows = list_own_claims(g.user['id'])
    return render_template('claims.html', claims=rows)


@bp.get('/claims/<int:claim_id>')
@role_required('employee')
def own_detail(claim_id):
    if not consent_granted(g.user['id']):
        return redirect(url_for('claims.consent'))
    claim = get_own_claim(g.user['id'], claim_id)
    if claim is None:
        abort(404)
    history = get_db().execute('SELECT h.*,u.display_name FROM claim_history h JOIN users u ON u.id=h.actor_id WHERE h.claim_id=? ORDER BY h.id DESC', (claim_id,)).fetchall()
    return render_template('claim_detail.html', claim=claim, history=history)


@bp.get('/finance/claims')
@role_required('finance')
def finance_list():
    rows = get_db().execute('SELECT c.*,u.display_name AS owner FROM claims c JOIN users u ON u.id=c.user_id ORDER BY c.verified,c.id').fetchall()
    return render_template('finance.html', claims=rows, statuses=STATUSES)


@bp.post('/finance/claims/<int:claim_id>/verify')
@role_required('finance')
def verify(claim_id):
    error = None
    try:
        verify_claim(claim_id, g.user['id'], request.form.get('status', ''), request.form.get('note', ''))
    except ValueError as exc:
        error = str(exc)
    if error:
        rows = get_db().execute('SELECT c.*,u.display_name AS owner FROM claims c JOIN users u ON u.id=c.user_id ORDER BY c.verified,c.id').fetchall()
        return render_template('finance.html', claims=rows, statuses=STATUSES, error=error, failed_id=claim_id, submitted=request.form), 400
    flash('业务事实已核对，状态与说明已更新。此操作不会触发真实审批或付款。', 'success')
    return redirect(url_for('claims.finance_list'))
