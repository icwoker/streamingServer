from flask_socketio import join_room, leave_room
from flask import request
from app.models.user import WatchHistory
from app.db.database import db
import datetime
# 存储在线用户信息
online_users = {}

def init_socket(socketio):
    @socketio.on('connect')
    def handle_connect():
        user_id = request.args.get('userId')
        room_id = request.args.get('roomId')
        if user_id and room_id:
            online_users[request.sid] = {'userId': user_id, 'roomId': room_id}
            join_room(room_id)
            print(f"用户 {user_id} 加入了直播间 {room_id}")
            #记录用户进入直播间的历史记录到数据库，代表用户的观看历史
            watch_history = WatchHistory(user_id=user_id, live_id=room_id, watched_at=datetime.datetime.now())
            db.session.add(watch_history)
            db.session.commit()
        else:
            print("连接失败：缺少 userId 或 roomId")

    @socketio.on('disconnect')
    def handle_disconnect():
        user_info = online_users.pop(request.sid, None)
        if user_info:
            print(f"用户 {user_info['userId']} 离开了直播间 {user_info['roomId']}")
            leave_room(user_info['roomId'])

    @socketio.on('send_danmu')
    def handle_send_danmu(data):
        user_info = online_users.get(request.sid)
        if user_info:
            room_id = user_info['roomId']
            sender_id = user_info['userId']
            message = data.get('message', '')
            if message:
                print(f"收到弹幕：{message} 来自用户 {sender_id}")
                socketio.emit('receive_danmu', {
                    'senderId': sender_id,
                    'message': message,
                    'timestamp': data.get('timestamp', '')
                }, room=room_id)

    @socketio.on('send_gift')
    def handle_send_gift(data):

        user_info = online_users.get(request.sid)
        if user_info:
            room_id = user_info['roomId']
            sender_id = user_info['userId']
            gift_name = data.get('giftName', '')
            gitf_count = data.get('giftCount', '')
            print(f"触发这个事件, 礼物名称：{gift_name}, 礼物数量：{gitf_count}")
            if gift_name and gitf_count:
                print(f"收到礼物：{gift_name} 数量：{gitf_count} 来自用户 {sender_id}")
                socketio.emit('receive_gift', {
                    'senderId': sender_id,
                    'giftName': gift_name,
                    'giftCount': gitf_count,
                    'timestamp': data.get('timestamp', '')
                }, room=room_id)
