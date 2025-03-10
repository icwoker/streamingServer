from flask import Blueprint, send_file, session, jsonify, request
from app.models.user import Follow,User
from app.routes.auth import get_user_from_token
from app.db.database import db
import uuid
import datetime
from app.routes.liveModerator import check_moderator
from app.routes.liveBanned import check_live_banned_user
follow_bp = Blueprint('follow_bp', __name__)

#关注
def follow(follower_id,followed_id):
    #检查用户是否存在
    follwer = User.query.filter_by(id=follower_id).first()
    followed = User.query.filter_by(id=followed_id).first()
    if not follwer or not followed:
        return jsonify({'message': '用户不存在'})
    #不能关注自己账号
    if follwer.id == followed.id:
        return jsonify({'message': '不能关注自己账号'})
    #检查是否已经关注
    existing = Follow.query.filter_by(follower_id=follower_id,followed_id=followed_id).first()
    if existing:
        return jsonify({'message': '已经关注了'})
    id = uuid.uuid4()
    follow = Follow(id=id, follower_id=follower_id, followed_id=followed_id, created_at=datetime.datetime.now())
    try:
        db.session.add(follow)
        db.session.commit()
        return jsonify({'message': '关注成功'}) , 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'关注失败: {str(e)}'}), 500

def unfollow(follower_id,followed_id):

    follow = Follow.query.filter_by(follower_id=follower_id,followed_id=followed_id).first()
    if follow:
        db.session.delete(follow)
        db.session.commit()
        return jsonify({'message': '取消关注成功'}) ,200
    else:
        return jsonify({'message': '未关注'}), 400


def get_my_fans(user_id, page=1, per_page=20):
    try:
        # 查询粉丝列表，并判断是否互粉
        fans_pagination = db.session.query(Follow, User). \
            join(User, Follow.follower_id == User.id). \
            filter(Follow.followed_id == user_id). \
            paginate(page=page, per_page=per_page, error_out=False)

        fans_list = []
        for follow, user in fans_pagination.items:
            # 判断当前用户是否已关注该粉丝
            is_following = Follow.query.filter_by(follower_id=user_id, followed_id=user.id).first() is not None
            is_live_moderator = check_moderator(user.id,user_id)
            is_live_banned = check_live_banned_user(user.id,user_id)
            fans_list.append({
                'id': user.id,
                'name': user.name,
                'avatar_url': user.avatar_url,
                'bio': user.bio,
                'follow_time': follow.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_following': is_following , # 是否已关注该粉丝
                'is_live_moderator': is_live_moderator[0], # 是否是房管
                'is_live_banned': is_live_banned # 是否是禁言用户
            })

        return jsonify({
            'message': '获取粉丝成功',
            'fans': fans_list,
            'total': fans_pagination.total,
            'pages': fans_pagination.pages,
            'current_page': page
        }), 200
    except Exception as e:
        return jsonify({'message': f'获取粉丝失败: {str(e)}'}), 500


def get_my_follows(user_id, page=1, per_page=20):
   try:
       # 使用联合查询提高效率
       follows_pagination = db.session.query(Follow, User). \
           join(User, Follow.followed_id == User.id). \
           filter(Follow.follower_id == user_id). \
           paginate(page=page, per_page=per_page, error_out=False)

       follows_list = []
       for follow, user in follows_pagination.items:
           follows_list.append({
               'id': user.id,
               'name': user.name,
               'avatar_url': user.avatar_url,
               'bio': user.bio,
               'follow_time': follow.created_at.strftime('%Y-%m-%d %H:%M:%S')
           })

       return jsonify({
           'message': '获取关注成功',
           'follows': follows_list,
           'total': follows_pagination.total,
           'pages': follows_pagination.pages,
           'current_page': page
       }) , 200
   except Exception as e:
       return jsonify({'message': f'获取关注失败: {str(e)}'}), 500


def check_follow_status(follower_id, followed_id):
    try:
        existing = Follow.query.filter_by(follower_id=follower_id, followed_id=followed_id).first()
        return jsonify({
            'is_following': existing is not None
        }), 200
    except Exception as e:
        return jsonify({'message': f'获取关注状态失败: {str(e)}'}), 500


# 获取用户粉丝数和关注数
def get_follow_stats(user_id):
    try:
        fans_count = Follow.query.filter_by(followed_id=user_id).count()
        follows_count = Follow.query.filter_by(follower_id=user_id).count()
        return jsonify({
            'fans_count': fans_count,
            'follows_count': follows_count
        }), 200
    except Exception as e:
        return jsonify({'message': f'获取粉丝数和关注数失败: {str(e)}'}), 500

@follow_bp.route('/get_follow_stats', methods=['GET'])
def api_get_follow_stats():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    user_id = user.id
    return get_follow_stats(user_id)

@follow_bp.route('/follow',methods=['POST'])
def api_follow():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    follower_id = user.id
    followed_id = request.json.get('followed_id')
    return follow(follower_id,followed_id)

@follow_bp.route('/unfollow',methods=['POST'])
def api_unfollow():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    follower_id = user.id
    followed_id = request.json.get('followed_id')
    return unfollow(follower_id,followed_id)

@follow_bp.route('/get_my_fans',methods=['GET'])
def api_get_my_fans():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    user_id = user.id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    return get_my_fans(user_id, page, per_page)

@follow_bp.route('/get_my_follows',methods=['GET'])
def api_get_my_follows():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    user_id = user.id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    return get_my_follows(user_id, page, per_page)

@follow_bp.route('/check_follow_status',methods=['GET'])
def api_check_follow_status():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '用户未登录'}), 401
    follower_id = user.id
    followed_id = request.args.get('followed_id')
    return check_follow_status(follower_id, followed_id)

