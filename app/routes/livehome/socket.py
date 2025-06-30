from flask_socketio import join_room, leave_room
from flask import request,current_app
from app.models.user import WatchHistory, Live,RedPacket,RedPacketParticipant,Wallet,Transaction
from app.db.database import db
import datetime
from app.routes.watchHistory import create_watchHistory, leave_watchHistory
from app.routes.ChatMessage import add_chat_message
from app.routes.LiveStatistics import update_peak_viewers,update_total_messages
from app.routes.livehome.routes import rp_is_expired
import uuid
from flask_apscheduler import APScheduler

from apscheduler.schedulers.background import BackgroundScheduler


# Store online users information
online_users = {}

#写入一条记录进入红包表
def create_red_packet(anchor_id,live_id,title,amount,winner_num,expire_time):
    red_packet_id = str(uuid.uuid4())
    try:
        red_packet = RedPacket(
            id=red_packet_id,
            anchor_id=anchor_id,
            room_id=live_id,
            title=title,
            amount=amount,
            winner_num=winner_num,
            expire_time=expire_time,
            status='ongoing'
        )
        db.session.add(red_packet)
        db.session.commit()
    except Exception as e:
        print(f"创建红包失败：{str(e)}")
        return False
    return red_packet_id

# 初始化调度器
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

#定时任务1-红包开奖时主动将中奖信息推送给前端
def check_and_notify_redpacket(socketio, redpacket_id, room_id,app):
    """检查红包状态并通知前端"""
    # from app import create_app
    # app = create_app()

    with app.app_context():
        try:
            from app.routes.livehome.routes import get_redpacket, allocate_red_packet

            # 使用上下文管理器统一管理事务
            with db.session.begin():
                redpacket = get_redpacket(redpacket_id)
                # print(f"红包 {redpacket_id} 状态：{redpacket.status}")

                if redpacket and redpacket.status == 'ongoing':
                    winners = allocate_red_packet(redpacket_id)
                    print(f"红包 {redpacket_id} 已开奖，中奖用户：{winners}")
                    if len(winners) > 0:
                        work_id = socketio.emit('redpacket_result', {
                            'redpacket_id': redpacket_id,
                            'winner': True,
                            'winners': winners,
                        }, room=room_id)
                        print(f"已向房间 {room_id} 推送红包结果，工作ID：{work_id}")
                    else:
                        current_app.logger.warning(f"Redpacket {redpacket_id} 无中奖用户")
                else:
                    current_app.logger.info(f"Redpacket {redpacket_id} 未到开奖时间")

        except Exception as e:
            current_app.logger.error(f"定时任务执行出错: {str(e)}")
            # 不需要显式rollback，上下文管理器会自动处理

def init_socket(socketio,app):
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
                work_id =socketio.emit('receive_danmu', {
                    'senderId': sender_id,
                    'message': message,
                    'timestamp': data.get('timestamp', '')
                }, room=room_id)
                print(f"已向房间 {room_id} 推送弹幕，工作ID：{work_id}")
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


    @socketio.on('send_redPackage')
    def handle_send_redPackage(data):
        # 首先检查用户是否在线
        user_info = online_users.get(request.sid)
        if not user_info:
            return

        # 获取用户信息
        room_id = user_info['roomId']
        anchor_id = user_info['userId']
        print(f"user_info['roomId']:{user_info['roomId']}")
        # 验证红包数据
        if not data or not all(key in data for key in ['title', 'amount', 'winnerNum', 'expireTime']):
            print("红包数据不完整")
            return

        title = data.get('title', '')
        amount = data.get('amount', 0)
        winner_num = data.get('winnerNum', 0)
        expire_time_minutes = data.get('expireTime', 0)

        # 验证金额和获奖人数是否合法
        if amount <= 0 or winner_num <= 0:
            print("金额或获奖人数必须大于0")
            return

        # 检查主播钱包余额
        anchor_wallet = Wallet.query.filter_by(user_id=anchor_id).first()
        if not anchor_wallet or anchor_wallet.balance < amount:
            print(f"主播 {anchor_id} 余额不足或钱包不存在，无法创建红包")
            return

        # 计算过期时间
        current_time = datetime.datetime.now()
        expire_time = current_time + datetime.timedelta(minutes=expire_time_minutes)
        formatted_time = expire_time.isoformat()

        # 创建红包记录
        redPacket_id = create_red_packet(anchor_id, room_id, title, amount, winner_num, formatted_time)
        if not redPacket_id:
            print("创建红包记录失败")
            return

        # 扣除主播余额并记录交易
        try:
            anchor_wallet.balance -= amount
            transaction = Transaction(
                user_id=anchor_id,
                transaction_type='红包',
                amount=-amount,
                reference_id=redPacket_id,
                description='红包活动',
                balance_after=anchor_wallet.balance,
                created_at=datetime.datetime.now()
            )
            db.session.add(transaction)
            db.session.commit()
            print(f"创建红包成功，扣除主播 {anchor_id} {amount} 元")
        except Exception as e:
            db.session.rollback()
            print(f"扣除余额时发生错误: {str(e)}")
            return

        # 广播红包信息给房间内所有用户
        socketio.emit('receive_redPackage', {
            'id': redPacket_id,
            'anchorId': anchor_id,
            'liveId': room_id,
            'title': title,
            'amount': amount,
            'winnerNum': winner_num,
            'expireTime': formatted_time,
            'has_join': False
        }, room=room_id)

        # 添加定时任务，在红包到期时开奖
        scheduler.add_job(
            check_and_notify_redpacket,
            'date',
            run_date=expire_time,
            args=[socketio,redPacket_id, room_id,app],
            id=f'red_packet_{redPacket_id}'
        )
        print(f"已创建红包 {redPacket_id}，将在 {expire_time} 开奖")


    #拉黑通知，发送一个信息，强制用户退出直播间
    @socketio.on('send_BanMessage')
    def send_BanMessage(data):
        try:
            print("收到了拉黑通知")
            # 获取主播信息（发送禁言的人）
            user_info = online_users.get(request.sid)
            if not user_info:
                return

            room_id = user_info['roomId']
            anchor_id = user_info['userId']  # 主播ID

            # 获取被拉黑的用户ID
            banned_user_id = data.get('banned_user')
            if not banned_user_id:
                print("未指定要禁言的用户")
                return

            # 查找被禁用户的所有活跃连接
            # banned_sockets = []
            # for sid, info in online_users.items():
            #     if info['userId'] == banned_user_id and info['roomId'] == room_id:
            #         banned_sockets.append(sid)
            #
            # if not banned_sockets:
            #     print(f"用户 {banned_user_id} 不在直播间 {room_id} 中")
            #     return

            socketio.emit('ban_notification', {
                'type': 'ban',
                "banned_user_id": banned_user_id,
                'message': '你已被主播禁言并移出直播间',
                'anchor_id': anchor_id,
                'room_id': room_id
            }, room=room_id)



        except Exception as e:
            print(f"发送禁言消息时发生错误: {str(e)}")