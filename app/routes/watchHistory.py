from flask import Blueprint,request,jsonify,current_app,make_response
from app.routes.auth import  get_user_from_token
from app.models.user import WatchHistory,Live,User
from app.db.database import db
import uuid
from datetime import datetime

watchHistory_bp = Blueprint('watchHistory_bp',__name__)

def update_watchHistory(user_id,live_id):
    watchHistory = WatchHistory.query.filter_by(user_id=user_id,live_id=live_id).first()
    watchHistory.watched_at = db.func.now()
    db.session.commit()

def leave_watchHistory(user_id,live_id):
    watchHistory = WatchHistory.query.filter_by(user_id=user_id,live_id=live_id).first()
    #获取现在的时间 减去 观看最新观看时间得到秒数
    watchHistory.watch_duration = (datetime.now() - watchHistory.watched_at).total_seconds()
    db.session.commit()


def create_watchHistory(user_id, live_id):
    # Check if history exists
    existing_history = WatchHistory.query.filter_by(user_id=user_id, live_id=live_id).first()

    # If exists and live is active, update it and return its ID
    if existing_history:
        if Live.query.filter_by(id=live_id).first().status == 'Live':
            update_watchHistory(user_id, live_id)
            return existing_history.id

    # Otherwise create new entry
    id = str(uuid.uuid4())
    watchHistory = WatchHistory(id=id, user_id=user_id, live_id=live_id, watched_at=db.func.now())
    db.session.add(watchHistory)
    db.session.commit()
    return id


#根据user_id找到对应的user，返回user的name
def get_user_info(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return None, None  # or raise an exception
    return user.name, user.avatar_url
#根据live_id找到对应的live，返回live的标题，封面图，直播状态
def get_live_info(live_id):
    live = Live.query.filter_by(id=live_id).first()
    liver_id = live.user_id
    #根据id返回user的名称
    liver_name,avatar_url = get_user_info(liver_id)
    obj = {
        'liver_name':liver_name,
        'title':live.title,
        'avatar_url':avatar_url,
        'status':live.status,
    }
    return obj


#获取观看历史，分页显示
def get_watchHistory(user_id, page, page_size):
    # Use a join to fetch watch history and live info in one query
    query = db.session.query(
        WatchHistory, Live, User
    ).join(
        Live, WatchHistory.live_id == Live.id
    ).join(
        User, Live.user_id == User.id
    ).filter(
        WatchHistory.user_id == user_id
    ).order_by(
        WatchHistory.watched_at.desc()
    )

    # Get total count (for pagination)
    total = query.count()

    # Get paginated items
    results = query.offset((page - 1) * page_size).limit(page_size).all()

    # Format the results
    items = []
    for watch_history, live, user in results:
        watch_history_dict = {
            'id': watch_history.id,
            'user_id': watch_history.user_id,
            'live_id': watch_history.live_id,
            'watched_at': watch_history.watched_at,
            'watch_duration': watch_history.watch_duration,
            'live_info': {
                'liver_name': user.name,
                'title': live.title,
                'avatar_url': user.avatar_url,
                'status': live.status
            }
        }
        items.append(watch_history_dict)

    return items, total


@watchHistory_bp.route('/history', methods=['GET'])
def history():
    try:
        # Get user from token
        user = get_user_from_token()
        if not user:
            return jsonify({'error': '没有登录'}), 401

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)

        # Fetch watch history
        items, total = get_watchHistory(user.id, page, page_size)

        # Return paginated response
        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
    except Exception as e:
        current_app.logger.error(f"获取观看历史失败: {str(e)}")
        return jsonify({'error': '在获取观看历史时发生错误'}), 500


# Delete a specific watch history entry
@watchHistory_bp.route('/history/<history_id>', methods=['DELETE'])
def delete_history(history_id):
    try:
        # Get user from token
        user = get_user_from_token()
        if not user:
            return jsonify({'error': '没有登录'}), 401

        # Find the watch history
        watch_history = WatchHistory.query.filter_by(id=history_id, user_id=user.id).first()
        if not watch_history:
            return jsonify({'error': '没有找到该聊天记录或者不是你的记录'}), 404

        # Delete the watch history
        db.session.delete(watch_history)
        db.session.commit()

        return jsonify({
            'message': '删除观看历史成功'
        })
    except Exception as e:
        current_app.logger.error(f"删除观看历史失败: {str(e)}")
        return jsonify({'error': '在删除观看历史时发生错误'}), 500


# Clear all watch history for a user
@watchHistory_bp.route('/history/clear', methods=['POST'])
def clear_history():
    try:
        # Get user from token
        user = get_user_from_token()
        if not user:
            return jsonify({'error': '没有登录'}), 401

        # Delete all watch history records for this user
        WatchHistory.query.filter_by(user_id=user.id).delete()
        db.session.commit()

        return jsonify({
            'message': '全部历史记录已清除'
        })
    except Exception as e:
        current_app.logger.error(f"清除观看历史失败: {str(e)}")
        return jsonify({'error': '在清除观看历史时发生错误'}), 500
