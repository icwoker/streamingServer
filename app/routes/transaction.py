from app.db.database import db
from app.models.user import Transaction
from flask import Blueprint,request,jsonify,current_app,make_response
from app.routes.auth import  get_user_from_token
import uuid
import datetime

transaction_bp = Blueprint('transaction',__name__)

def get_latest_balance(user_id):
    """获取用户的最新余额"""
    # 使用只读查询，避免隐式启动事务！！！要记住！不要重复开启事务！
    latest_transaction = db.session.query(Transaction.balance_after)\
        .filter(Transaction.user_id == user_id)\
        .order_by(Transaction.created_at.desc())\
        .first()

    if latest_transaction:
        return latest_transaction.balance_after
    else:
        return 0

@transaction_bp.route('/recharge', methods=['POST'])
def create_transaction():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401

    data = request.get_json()
    user_id = user.id
    amount = data.get('amount')
    old_balance = get_latest_balance(user_id)

    if not amount:
        return jsonify({'message': '请输入充值金额'}), 400

    transaction_id = str(uuid.uuid4())
    new_balance = old_balance + amount  # 计算新的余额

    transaction = Transaction(
        user_id=user_id,
        transaction_type='充值',
        amount=amount,
        reference_id=transaction_id,
        description='充值成功',
        balance_after=new_balance,
        created_at=datetime.datetime.now()
    )
    db.session.add(transaction)
    db.session.commit()

    # 返回充值成功消息和最终余额
    return jsonify({
        'message': '充值成功',
        'balance': new_balance  # 返回最终余额
    }), 200

@transaction_bp.route('/balance',methods=['GET'])
def get_balance():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401
    user_id = user.id
    balance = get_latest_balance(user_id)
    return jsonify({'balance': balance}), 200


@transaction_bp.route('/give_gift', methods=['POST'])
def give_gift():
    user = get_user_from_token()
    if not user:
        return jsonify({'status': 'error', 'message': '未登录或登录已过期'}), 401

    user_id = user.id
    data = request.get_json()
    amount = data.get('amount')
    description = data.get('description')
    liver_id = data.get('liver_id')

    # 数据校验
    if not amount or amount <= 0:
        return jsonify({'status': 'error', 'message': '礼物金额必须为正数'}), 400
    if not liver_id:
        return jsonify({'status': 'error', 'message': '主播ID不能为空'}), 400
    if not isinstance(amount, (int, float)):
        return jsonify({'status': 'error', 'message': '礼物金额格式错误'}), 400

    try:
        # 获取余额
        old_balance = get_latest_balance(user_id)
        liver_balance = get_latest_balance(liver_id)

        user_new_balance = old_balance - amount
        liver_new_balance = liver_balance + amount / 2

        if user_new_balance < 0:
            return jsonify({'status': 'error', 'message': '余额不足'}), 400

        # 创建交易记录
        user_transaction = Transaction(
            user_id=user_id,
            transaction_type='送礼物',
            amount=amount,
            reference_id=str(uuid.uuid4()),
            description=description,
            balance_after=user_new_balance,
            created_at=datetime.datetime.now()
        )
        db.session.add(user_transaction)

        liver_transaction = Transaction(
            user_id=liver_id,
            transaction_type='收到礼物',
            amount=amount / 2,
            reference_id=str(uuid.uuid4()),
            description=description,
            balance_after=liver_new_balance,
            created_at=datetime.datetime.now()
        )
        db.session.add(liver_transaction)

        # 提交事务
        db.session.commit()

    except Exception as e:
        # 回滚事务
        db.session.rollback()
        current_app.logger.error(f"礼物发放失败: 用户ID={user_id}, 主播ID={liver_id}, 金额={amount}, 错误={e}")
        return jsonify({'status': 'error', 'message': '礼物发放失败'}), 500

    return jsonify({'status': 'success', 'message': '礼物发放成功'}), 200