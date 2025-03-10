from flask import Blueprint, send_file, session, jsonify, request
from app.models.user import ChatMessage,User,Live
from app.routes.auth import get_user_from_token
from app.db.database import db
import uuid
import datetime
from app.routes.liveModerator import check_moderator
from app.routes.liveBanned import check_live_banned_user
ChatMessage_bp = Blueprint('ChatMessage_bp', __name__)


#为直播间添加添加一条信息，但是最多10条，多出来的，队头删除。
def add_chat_message(live_id, user_id, content):
    try:
        # Check message count more efficiently
        message_count = ChatMessage.query.filter_by(live_id=live_id).count()

        if message_count >= 10:
            # Find and delete the oldest message
            oldest_message = ChatMessage.query.filter_by(live_id=live_id).order_by(ChatMessage.created_at.asc()).first()
            if oldest_message:
                db.session.delete(oldest_message)

        # Add new message
        new_message = ChatMessage(live_id=live_id, user_id=user_id, content=content)
        db.session.add(new_message)
        db.session.commit()
        return True, "添加成功"
    except Exception as e:
        db.session.rollback()
        print(e)
        return False, str(e)

#删除关于这个直播间的所有信息
def delete_chat_message(live_id):
    ChatMessage.query.filter_by(live_id=live_id).delete()
    db.session.commit()

#获取直播间的所有消息
def get_chat_message(live_id):
    #使用联合搜索，获取用户的基本信息和消息内容
    messages = db.session.query(ChatMessage,User).\
        join(User,ChatMessage.user_id == User.id).\
        filter(ChatMessage.live_id == live_id).\
        order_by(ChatMessage.created_at.asc()).all()
    message_list = []
    live = Live.query.filter_by(id=live_id).first()
    for message,user in messages:
        message_list.append({
            'id': user.id,
            'username': user.name,
            'avatar': user.avatar_url,
            'isAdmin':user.id == live.user_id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return message_list


@ChatMessage_bp.route('/get_chat_message', methods=['GET'])
def get_chat_message_api():
    live_id = request.args.get('live_id')
    if not live_id:
        return jsonify({'code': 400, 'msg': '缺少live_id参数'})

    # Check if live exists
    live = Live.query.get(live_id)
    if not live:
        return jsonify({'code': 404, 'msg': '直播间不存在'})

    message_list = get_chat_message(live_id)
    return jsonify({'code': 200, 'msg': '获取成功', 'data': message_list})