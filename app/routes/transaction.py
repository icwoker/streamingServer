from app.db.database import db
from app.models.user import Transaction,User,GiftRecord,Gift,Wallet
from flask import Blueprint,request,jsonify,current_app,make_response
from app.routes.auth import  get_user_from_token
import uuid
import datetime

transaction_bp = Blueprint('transaction',__name__)


def get_user_wallet(user_id):
    """获取用户的钱包，如果不存在则创建"""
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        # 创建新钱包
        wallet = Wallet(
            user_id=user_id,
            balance=0,
            total_income=0,
            total_expense=0,
            updated_at=datetime.datetime.now()
        )
        db.session.add(wallet)
        db.session.commit()
    return wallet


def get_latest_balance(user_id):
    """获取用户的最新余额"""
    wallet = get_user_wallet(user_id)
    return wallet.balance


@transaction_bp.route('/recharge', methods=['POST'])
def create_transaction():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401

    data = request.get_json()
    user_id = user.id
    amount = data.get('amount')

    if not amount:
        return jsonify({'message': '请输入充值金额'}), 400

    if amount <= 0:
        return jsonify({'message': '充值金额必须大于0'}), 400

    try:
        # 获取钱包信息
        wallet = get_user_wallet(user_id)
        old_balance = wallet.balance

        # 更新钱包余额（不提交事务）
        wallet.balance += amount
        wallet.total_income += amount
        wallet.updated_at = datetime.datetime.now()

        # 创建交易记录
        transaction_id = str(uuid.uuid4())
        transaction = Transaction(
            user_id=user_id,
            transaction_type='充值',
            amount=amount,
            reference_id=transaction_id,
            description='充值成功',
            balance_after=wallet.balance,  # 使用更新后的钱包余额
            created_at=datetime.datetime.now()
        )

        # 一次性提交所有操作，保证事务一致性
        db.session.add(transaction)
        db.session.commit()

        # 返回充值成功消息和最终余额
        return jsonify({
            'message': '充值成功',
            'balance': wallet.balance
        }), 200
    except Exception as e:
        # 发生异常时回滚事务
        db.session.rollback()
        return jsonify({'message': f'充值失败: {str(e)}'}), 500



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
    gift_id = data.get('gift_id')
    quantity = data.get('quantity', 1)
    receiver_id = data.get('receiver_id')  # 接收者ID
    live_id = data.get('live_id')  # 直播ID

    # 数据校验
    if not gift_id:
        return jsonify({'status': 'error', 'message': '礼物ID不能为空'}), 400
    if not receiver_id:
        return jsonify({'status': 'error', 'message': '接收者ID不能为空'}), 400
    if not live_id:
        return jsonify({'status': 'error', 'message': '直播ID不能为空'}), 400
    if not quantity or quantity <= 0:
        return jsonify({'status': 'error', 'message': '礼物数量必须为正数'}), 400

    try:
        # 获取礼物信息
        gift = Gift.query.get(gift_id)
        if not gift:
            return jsonify({'status': 'error', 'message': '礼物不存在'}), 404

        # 计算总价
        total_price = gift.price * quantity

        # 获取发送者钱包
        sender_wallet = get_user_wallet(user_id)

        # 检查余额是否足够
        if sender_wallet.balance < total_price:
            return jsonify({'status': 'error', 'message': '余额不足'}), 400

        # 获取接收者钱包
        receiver_wallet = get_user_wallet(receiver_id)

        # 计算平台分成，假设平台抽成50%
        platform_cut = total_price * 0.5
        receiver_amount = total_price - platform_cut

        # 更新发送者钱包
        sender_wallet.balance -= total_price
        sender_wallet.total_expense += total_price
        sender_wallet.updated_at = datetime.datetime.now()

        # 更新接收者钱包
        receiver_wallet.balance += receiver_amount
        receiver_wallet.total_income += receiver_amount
        receiver_wallet.updated_at = datetime.datetime.now()

        # 创建礼物记录
        gift_record = GiftRecord(
            sender_id=user_id,
            receiver_id=receiver_id,
            live_id=live_id,
            gift_id=gift_id,
            quantity=quantity,
            total_price=total_price,
            created_at=datetime.datetime.now()
        )
        db.session.add(gift_record)

        # 创建发送者交易记录
        sender_transaction = Transaction(
            user_id=user_id,
            transaction_type='送礼物',
            amount=-total_price,
            reference_id=str(uuid.uuid4()),
            description=f'赠送礼物: {gift.name} x {quantity}',
            balance_after=sender_wallet.balance,
            created_at=datetime.datetime.now()
        )
        db.session.add(sender_transaction)

        # 创建接收者交易记录
        receiver_transaction = Transaction(
            user_id=receiver_id,
            transaction_type='收到礼物',
            amount=receiver_amount,
            reference_id=str(uuid.uuid4()),
            description=f'收到礼物: {gift.name} x {quantity}',
            balance_after=receiver_wallet.balance,
            created_at=datetime.datetime.now()
        )
        db.session.add(receiver_transaction)

        # 提交事务
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '礼物发放成功',
            'sender_balance': sender_wallet.balance
        }), 200

    except Exception as e:
        # 回滚事务
        db.session.rollback()
        current_app.logger.error(
            f"礼物发放失败: 用户ID={user_id}, 接收者ID={receiver_id}, 礼物ID={gift_id}, 数量={quantity}, 错误={e}")
        return jsonify({'status': 'error', 'message': '礼物发放失败'}), 500


def get_transactions(user_id,page=1,page_size=10):
    """获取用户的交易记录"""
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).paginate(page=page,per_page=page_size,error_out=False)
    return transactions

@transaction_bp.route('/list', methods=['GET'])
def get_user_transactions():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401
    user_id = user.id
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    transactions = get_transactions(user_id,page,page_size)
    data = {
        'transactions': [t.to_dict() for t in transactions.items],
        'total': transactions.total,
        'page': transactions.page,
        'page_size': transactions.per_page
    }
    return jsonify(data), 200


#获取本场直播的大哥""
# Get gift ranking for the current live stream
def get_gift_records(live_id):
    # Get all gift records for this live stream
    gift_records = GiftRecord.query.filter_by(live_id=live_id).order_by(GiftRecord.created_at.desc()).all()

    # Sum up total spending for each sender
    gift_records_dict = {}
    for gift_record in gift_records:
        if gift_record.sender_id not in gift_records_dict:
            gift_records_dict[gift_record.sender_id] = gift_record.total_price
        else:
            gift_records_dict[gift_record.sender_id] += gift_record.total_price

    # Sort senders by total amount spent, in descending order
    sorted_gift_records = sorted(gift_records_dict.items(), key=lambda x: x[1], reverse=True)

    # Get user details for all senders
    user_ids = [user_id for user_id, amount in sorted_gift_records]
    users = User.query.filter(User.id.in_(user_ids)).all()

    # Map user IDs to their details
    user_dict = {user.id: {'username': user.name, 'avatar': user.avatar_url} for user in users}

    # Format result for frontend
    result = [
        {
            'username': user_dict[user_id]['username'],
            'avatar': user_dict[user_id]['avatar'],
            'amount': amount
        }
        for user_id, amount in sorted_gift_records
    ]

    return result

@transaction_bp.route('/gift_ranking', methods=['GET'])
def get_gift_ranking():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401
    live_id = request.args.get('live_id')
    if not live_id:
        return jsonify({'message': '直播ID不能为空'}), 400
    result = get_gift_records(live_id)
    return jsonify({'data': result}), 200