from flask_socketio import join_room, leave_room
from flask import request
from app.models.user import WatchHistory, Live
from app.db.database import db
import datetime
from app.routes.watchHistory import create_watchHistory, leave_watchHistory
from app.routes.ChatMessage import add_chat_message
from app.routes.LiveStatistics import update_peak_viewers,update_total_messages
# Store online users information
online_users = {}


def init_socket(socketio):
    @socketio.on('connect')
    def handle_connect():
        try:
            user_id = request.args.get('userId')
            room_id = request.args.get('roomId')

            if user_id and room_id:
                # Store connection information
                online_users[request.sid] = {'userId': user_id, 'roomId': room_id}
                join_room(room_id)
                print(f"用户 {user_id} 连接 直播间 {room_id}")

                # Check if live stream exists and is active
                live = Live.query.filter_by(id=room_id).first()
                # print(f"直播间{live.id}被找到咯，状态是 {live.status}")
                if live and live.status == 'live':
                    # Create watch history record
                    history_id = create_watchHistory(user_id, room_id)
                    print(f"创建观看历史：ID {history_id} 用户 {user_id} 观看直播间 {room_id}")
                    #尝试更新直播间的最大观看人数
                    #人数
                    num_viewers = 0
                    for i in online_users.values():
                        if i['roomId'] == room_id:
                            num_viewers += 1
                    live.num_viewers = num_viewers
                    update_peak_viewers(room_id,num_viewers)
                    #尝试更新直播间的总消息数
                else:
                    print(f"直播间 {room_id} 没找到或者停止直播")
            else:
                print("连接失败：用户 ID 或直播间 ID 为空")
        except Exception as e:
            print(f"处理连接时发生错误: {str(e)}")

    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            user_info = online_users.pop(request.sid, None)
            if user_info:
                user_id = user_info['userId']
                room_id = user_info['roomId']

                print(f"用户 {user_id} 离开 直播间 {room_id}")
                leave_room(room_id)

                # Update watch history with duration
                try:
                    leave_watchHistory(user_id, room_id)
                    print(f"更新观看历史：用户 {user_id} 离开 {room_id}")
                except Exception as e:
                    print(f"更新观看历史失败: {str(e)}")
        except Exception as e:
            print(f"处理断开连接时发生错误: {str(e)}")

    @socketio.on('send_danmu')
    def handle_send_danmu(data):
        user_info = online_users.get(request.sid)
        if user_info:
            room_id = user_info['roomId']
            sender_id = user_info['userId']
            message = data.get('message', '')
            if isinstance(message, dict) and 'content' in message:
                message_content = message['content']
            else:
                message_content = str(message)  # Ensure it's a string

            add_chat_message(room_id, sender_id, message_content)
            if message:
                print(f"收到弹幕：{message} 来自用户 {sender_id}")
                #更新直播间的弹幕总数
                update_total_messages(room_id)
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
