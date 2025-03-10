from flask import Blueprint, send_file, session, jsonify, request
from app.models.user import LiveModerator,User
from app.routes.auth import get_user_from_token
from app.db.database import db
import uuid
import datetime

liveModerator_bp = Blueprint('liveModerator_bp', __name__)

def create_live_moderator(appointed_by, user_id):
    # 检查是否已经是主播的房管
    existing_moderator = LiveModerator.query.filter_by(appointed_by=appointed_by, user_id=user_id).first()
    if existing_moderator:
        return jsonify({'message': '已经是主播的房管，不允许重复设置'}), 400

    # 检查主播和房管 ID 是否存在
    user = User.query.get(user_id)
    live = User.query.get(appointed_by)
    if not user or not live:
        return jsonify({'message': '主播或房管不存在'}), 404

    try:
        # 创建房管
        new_moderator = LiveModerator(
            id=str(uuid.uuid4()),  # 确保 UUID 是字符串
            appointed_by=appointed_by,
            user_id=user_id
        )
        db.session.add(new_moderator)
        db.session.commit()
        return jsonify({'message': '设置成功'}), 200
    except Exception as e:
        db.session.rollback()  # 回滚事务
        return jsonify({'message': f'设置失败: {str(e)}'}), 500


#撤销房管资格
def remove_moderator(appointed_by, user_id):
    moderator = LiveModerator.query.filter_by(appointed_by=appointed_by, user_id=user_id).first()
    if not moderator:
        return jsonify({'message': '房管资格不存在'}), 404
    try:
        db.session.delete(moderator)
        db.session.commit()
        return jsonify({'message': '撤销成功'}), 200
    except Exception as e:
        db.session.rollback()  # 回滚事务
        return jsonify({'message': f'撤销失败: {str(e)}'}), 500


#判断user是否是liver的房管
def check_moderator(user_id, appointed_by):
    try:
        moderator = LiveModerator.query.filter_by(user_id=user_id, appointed_by=appointed_by).first()
        return bool(moderator) , 200   # 返回布尔值
    except Exception as e:
        return False , 500 # 查询失败时返回 False

#获取liver的房管列表
def get_moderators(appointed_by, page, per_page):
    try:
        moderators_pagination = db.session.query(LiveModerator, User). \
            join(User, LiveModerator.user_id == User.id). \
            filter(LiveModerator.appointed_by == appointed_by). \
            paginate(page=page, per_page=per_page, error_out=False)

        moderators_list = []
        for moderator, user in moderators_pagination.items:
            moderators_list.append({
                'id': moderator.id,
                'user_id': user.id,
                'name': user.name,
                'avatar_url': user.avatar_url,
                'created_at': moderator.created_at.strftime('%Y-%m-%d %H:%M:%S')  # 使用 created_at
            })

        return jsonify({
            'message': '获取房管列表成功',
            'moderators': moderators_list,
            'total': moderators_pagination.total,
            'pages': moderators_pagination.pages,
            'current_page': page
        }), 200
    except Exception as e:
        return jsonify({'message': f'获取房管列表失败: {str(e)}'}), 500


@liveModerator_bp.route('/create',methods=['POST'])
def create_live_moderator_route():
    try:
       user = get_user_from_token()
       if not user:
           return jsonify({'message': '用户未登录'}), 401
       moderator_id = request.json.get('moderator_id')
       if not moderator_id:
           return jsonify({'message': '请输入房管ID'}), 400
       return create_live_moderator(user.id, moderator_id)
    except Exception as e:
        return jsonify({'message': f'创建房管失败: {str(e)}'}), 500

@liveModerator_bp.route('/remove',methods=['POST'])
def remove_live_moderator_route():
    try:
       user = get_user_from_token()
       if not user:
           return jsonify({'message': '用户未登录'}), 401
       moderator_id = request.json.get('moderator_id')
       if not moderator_id:
           return jsonify({'message': '请输入房管ID'}), 400
       return remove_moderator(user.id, moderator_id)
    except Exception as e:
        return jsonify({'message': f'撤销房管失败: {str(e)}'}), 500

@liveModerator_bp.route('/check',methods=['GET'])
def check_live_moderator_route():
    try:
       user = get_user_from_token()
       if not user:
           return jsonify({'message': '用户未登录'}), 401
       moderator_id = request.args.get('moderator_id')
       if not moderator_id:
           return jsonify({'message': '请输入房管ID'}), 400
       return check_moderator(user.id, moderator_id)
    except Exception as e:
        return jsonify({'message': f'检查房管失败: {str(e)}'}), 500

@liveModerator_bp.route('/list',methods=['GET'])
def get_live_moderators_route():
    try:
       user = get_user_from_token()
       if not user:
           return jsonify({'message': '用户未登录'}), 401
       page = request.args.get('page', 1, type=int)
       per_page = request.args.get('per_page', 10 , type=int)
       return get_moderators(user.id, page, per_page)
    except Exception as e:
        return jsonify({'message': f'获取房管列表失败: {str(e)}'}), 500



