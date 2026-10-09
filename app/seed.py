from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash
from app.db import get_db


def seed_demo(today: date) -> None:
    db = get_db()
    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
        return
    now = datetime.now().isoformat(timespec='seconds')
    password = generate_password_hash('demo123')
    db.executemany('INSERT INTO users VALUES (?,?,?,?,?)', [
        (1, 'employee', '林晓', password, 'employee'),
        (2, 'employee2', '陈晨', password, 'employee'),
        (3, 'qiao', '乔姐', password, 'admin'),
        (4, 'zhou', '周敏', password, 'finance'),
    ])
    start = (today - timedelta(days=30)).isoformat()
    past = (today - timedelta(days=90)).isoformat()
    old_end = (today - timedelta(days=31)).isoformat()
    future = (today + timedelta(days=30)).isoformat()
    records = [
        ('travel', '差旅交通费用报销制度', '交通差旅', '交通 打车 出租车 高铁 火车 机票 出差', 'V2.0', '全体员工',
         '一、适用范围\n因公出差产生的交通费用可按本演示制度申请报销。\n\n二、报销凭据\n高铁、火车及机票需提供行程信息与有效报销凭据。因公乘坐出租车，需提供发票、行程及用途说明。\n\n三、办理要求\n交通费用按实际发生金额填报，提交完整凭据。私人行程不在报销范围内。\n\n以上内容为虚构教学制度。', start, None, 1),
        ('hotel', '差旅住宿费用报销制度', '住宿标准', '住宿 酒店 宾馆 出差 标准 上限', 'V1.0', '全体员工',
         '一、演示标准\n因公出差住宿，演示报销上限为每人每晚 350 元。\n\n二、所需材料\n提交住宿发票、入住明细和出差说明。超出上限部分需附额外说明，是否受理由财务核对。\n\n三、注意事项\n本标准仅用于课程演示，不代表任何真实单位规定。', start, None, 1),
        ('invoice', '报销凭证与提交要求', '发票凭证', '发票 凭证 材料 电子发票 抬头 提交', 'V1.1', '全体员工',
         '一、材料清单\n申请报销需提交用途说明、有效发票及对应业务凭据。\n\n二、发票要求\n发票内容应与实际业务一致。演示发票抬头为“教学演示单位”，请勿据此开具真实发票。电子发票可提交原文件。\n\n三、核对分工\n行政专员乔姐维护本制度；实际材料是否完整、单据状态是否准确，由财务专员周敏核对。', start, None, 1),
        ('travel', '差旅交通费用旧版制度', '交通差旅', '交通 旧版', 'V1.0', '全体员工', '已失效的虚构旧版制度，不作为现行依据。', past, old_end, 1),
        ('future', '未来生效的餐费制度', '其他', '餐费', 'V1.0', '全体员工', '尚未生效，不可作为当前报销依据。', future, None, 1),
        ('disabled', '停用的演示补贴制度', '其他', '补贴', 'V1.0', '全体员工', '已停用，不可作为当前报销依据。', start, None, 0),
    ]
    db.executemany('INSERT INTO policies (series_key,title,category,keywords,version,scope,content,effective_date,expiry_date,enabled,updated_by,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,3,?)', [(*r, now) for r in records])
    submitted = (today - timedelta(days=3)).isoformat()
    db.executemany('INSERT INTO claims (id,number,user_id,purpose,amount_cents,submitted_date,status,verified,note,verified_by,verified_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)', [
        (1, 'BX-2026-001', 1, '项目交流 · 高铁交通费', 26800, submitted, '待核对', 0, '', None, None),
        (2, 'BX-2026-002', 1, '外地调研 · 两晚住宿费', 68000, submitted, '审批中', 1, '演示住宿凭据已核对，等待审批。', 4, now),
        (3, 'BX-2026-003', 1, '办公用品 · 打印耗材', 15650, submitted, '已付款', 1, '演示单据已核对，模拟付款完成。', 4, now),
        (4, 'BX-2026-004', 2, '陈晨的调研交通费', 42000, submitted, '待付款', 1, '属于另一位员工，用于验证查询隔离。', 4, now),
    ])
    db.commit()
