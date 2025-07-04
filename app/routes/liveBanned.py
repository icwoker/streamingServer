from flask import Blueprint, send_file, session, jsonify, request
from app.models.user import LiveBannedUser,User,Live
from app.routes.auth import get_user_from_token
from app.db.database import db
import uuid
import datetime


liveBanned_bp = Blueprint('liveBanned_bp', __name__)

#主播将用户送入自己的小黑屋
def create_live_banned_user(user_id, banned_by,room_id):
    try:
        # 检查用户是否已进入小黑屋，若已进入不允许再次进入
        exist_live_banned_user = LiveBannedUser.query.filter_by(user_id=user_id, banned_by=banned_by).first()
        if exist_live_banned_user:
            return jsonify({'message': '用户已进入小黑屋，不允许重复进入'}), 400

        # 检查用户和主播是否存在
        exist_user = User.query.get(user_id)
        exist_live = User.query.get(banned_by)
        if not exist_user:
            return jsonify({'message': '用户不存在'}), 400
        if not exist_live:
            return jsonify({'message': '主播不存在'}), 400
        #检查一下直播间属于谁，如果是主播的房管封禁，应该把banned_by改成主播的id
        live = Live.query.filter_by(id=room_id).first()
        #找到直播间真正的所有者
        if live.user_id == banned_by:
            banned_by = live.user_id
        else:
            banned_by = live.user_id
        # 创建小黑屋用户
        reason = '违反主播规定和直播条例'
        live_banned_user = LiveBannedUser(reason=reason, user_id=user_id, banned_by=banned_by)
        db.session.add(live_banned_user)
        db.session.commit()

        return jsonify({'message': '用户已进入小黑屋'}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': '服务器内部错误'}), 500

def delete_live_banned_user(user_id, banned_by):
    try:
        # 检查用户是否已进入小黑屋，若未进入不允许移出
        exist_live_banned_user = LiveBannedUser.query.filter_by(user_id=user_id, banned_by=banned_by).first()
        if not exist_live_banned_user:
            return jsonify({'message': '用户未进入小黑屋，不允许移出'}), 400

        # 移出小黑屋用户
        db.session.delete(exist_live_banned_user)
        db.session.commit()

        return jsonify({'message': '用户已移出小黑屋'}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': '服务器内部错误'}), 500


#检查用户是否在主播的小黑屋中
def check_live_banned_user(user_id, banned_by):
    try:
        # 检查用户是否已进入小黑屋
        exist_live_banned_user = LiveBannedUser.query.filter_by(user_id=user_id, banned_by=banned_by).first()
        return bool(exist_live_banned_user)  # 返回布尔值
    except Exception as e:
        print(e)
        return False

#获取主播的小黑屋列表
def get_live_banned_list(banned_by, page, per_page):
    try:
        # 通过 User 联合查询，获取主播的小黑屋列表
        banner_pagination = db.session.query(LiveBannedUser, User). \
            join(User, LiveBannedUser.user_id == User.id). \
            filter(LiveBannedUser.banned_by == banned_by). \
            paginate(page=page, per_page=per_page, error_out=False)

        banner_list = []
        for banned_user, user in banner_pagination.items:
            banner_list.append({
                'id': user.id,
                'name': user.name,
                'avatar_url': user.avatar_url,
                'bio': user.bio,
                'ban_time': banned_user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        return jsonify({
            'message': '获取小黑屋用户成功',
            'banned_users': banner_list,
            'total': banner_pagination.total,
            'pages': banner_pagination.pages,
            'current_page': page
        }), 200
    except Exception as e:
        print(e)
        return jsonify({'message': f'获取小黑屋用户失败: {str(e)}'}), 500


#找出所有拉黑我的主播对。
def get_banned_me_list(user_id):
    try:
        banned_me_list =[ ]
        live_banned_users = LiveBannedUser.query.filter_by(user_id=user_id).all()
        for live_banned_user in live_banned_users:
            banned_me_list.append(live_banned_user.banned_by)
        return banned_me_list
    except Exception as e:
        print(e)
        return []

@liveBanned_bp.route('/create', methods=['POST'])
def create_live_banned_user_api():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    banned_by = user.id
    user_id = request.json.get('user_id')
    room_id = request.json.get('room_id')
    if not user_id:
        return jsonify({'message': '缺少必要参数'}), 400
    return create_live_banned_user(user_id, banned_by,room_id)


@liveBanned_bp.route('/delete', methods=['POST'])
def delete_live_banned_user_api():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    banned_by = user.id
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'message': '缺少必要参数'}), 400
    return delete_live_banned_user(user_id, banned_by)

@liveBanned_bp.route('/check', methods=['GET'])
def check_live_banned_user_api():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    banned_by = user.id
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'message': '缺少必要参数'}), 400
    return jsonify({'is_banned': check_live_banned_user(user_id, banned_by)}), 200


@liveBanned_bp.route('/list', methods=['GET'])
def get_live_banned_list_api():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    banned_by = user.id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    return get_live_banned_list(banned_by, page, per_page)

