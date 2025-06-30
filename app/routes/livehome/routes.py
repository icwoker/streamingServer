from flask import Blueprint,request,jsonify,current_app,make_response,Response
from app.routes.auth import get_user_from_token
import os
from app.methods.image.main import save_image
import datetime
from app.db.database import db
import uuid
livehome_bp = Blueprint('livehome', __name__)
from app.env import BASE_DIR
from flask_socketio import SocketIO
from app.models.user import (Live,WatchHistory,Tag,LiveTag,Follow,NotificationType,User,RedPacket,RedPacketParticipant
,Transaction,Wallet)
from app.routes.ChatMessage import delete_chat_message
from app.routes.LiveStatistics import create_LiveStatistics , update_total_duration
from app.routes.liveBanned import get_banned_me_list
from app.routes.Notification import batch_write_notifications, get_unread_notifications
from app.methods.recommend import recommend_lives
from app.routes.liveModerator import check_moderator
import random


socketio = SocketIO()

LIVE_IMAGE_DIR = os.path.join(BASE_DIR,'static','image','live')

def init_livehome(app):
    socketio.init_app(app, cors_allowed_origins="*")


def check_user_is_live(user_id):
    if user_id is None:
        return False , None
    live = db.session.query(Live).filter_by(user_id=user_id, status='live').first()
    if live:
        live_id = live.id
        return True , live_id
    return False , None

@livehome_bp.route('/create_room', methods=['POST'])
def create_room():
    title = request.form.get('title')
    category = request.form.get('category')  # 现在是单一分类/标签
    image = request.files.get('cover')
    user = get_user_from_token()

    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401

    user_id = user.id
    if not title or not category or not image:
        return jsonify({'message': '请输入直播间标题、分类和封面'}), 400

    # 保存图片
    image_name = str(user_id) + '.' + image.filename.split('.')[-1]
    save_image(image, LIVE_IMAGE_DIR, image_name)
    ImagePath = os.path.join('static', 'image', 'live', image_name)

    # 生成直播相关信息
    stream_key = f'liveroom_{user_id}'
    id = str(uuid.uuid4())

    # 检查之前的直播状态并关闭
    previous_live = db.session.query(Live).filter_by(user_id=user_id, status='live').order_by(
        Live.start_time.desc()).first()
    if previous_live:
        previous_live.end_time = datetime.datetime.now()
        previous_live.status = 'end'
        db.session.commit()

    # 创建新直播记录
    live = Live(
        id=id,
        user_id=user_id,
        title=title,
        cover_url=ImagePath,
        start_time=datetime.datetime.now(),
        stream_key=stream_key,
        status='live'
    )

    # 先添加直播记录以获取ID
    db.session.add(live)
    db.session.flush()  # 确保live获得ID但还没提交事务

    # 处理标签关联
    # 检查标签是否存在，不存在则创建
    tag = db.session.query(Tag).filter_by(name=category).first()
    if not tag:
        tag = Tag(name=category)
        db.session.add(tag)
        db.session.flush()  # 确保tag获得ID

    # 创建直播-标签关联
    live_tag = LiveTag(live_id=id, tag_id=tag.id)
    db.session.add(live_tag)

    # 也可以通过relationship直接添加标签
    # live.tags.append(tag)

    db.session.commit()
    #创建直播统计信息
    create_LiveStatistics(live.id)

    #发送通知给关注该主播的用户
    fans = Follow.query.filter_by(followed_id=user_id).all()
    fan_ids = [fan.follower_id for fan in fans]
    #获取主播的名字，和直播间id,返回给前端
    liver_name = user.name
    # live_notification = {
    #     'type':'直播通知',
    #     'live_id':id,
    #     'liver_id':user.id,
    #     'liver_name': liver_name,
    #     'title':title,
    #     'cover_url':ImagePath,
    #     'timestamp':datetime.datetime.now().isoformat()
    # }
    #写入通知记录
    content = f'主播：{liver_name} 开始直播啦！'
    batch_write_notifications(user.id,content,NotificationType.LIVE_START,live.id,fan_ids)

    return jsonify({
        'message': '直播间创建成功',
        'stream_key': stream_key,
        'live_id': id
    })


def get_live_by_id(id):
    live = Live.query.filter_by(id=id).first()
    if not live:
        return {"error": "Live not found"}, 404

    # 确保访问的是正确的字段名
    user_name = live.user.name  # 使用 `name` 字段
    user_avatar = live.user.avatar_url  # 使用 `avatar_url` 字段
    liver_id = live.user_id
    user= {
        'liver_id': liver_id,
        'name': user_name,
        'avatar_url': user_avatar
    }
    return live, user


@livehome_bp.route('/get_live_by_id/<id>', methods=['GET'])
def get_live_by_id_api(id):
    live, liver = get_live_by_id(id)
    if live is None:
        return jsonify({'message': '直播间不存在'}), 404

    # 假设每个直播只有一个标签，获取第一个标签
    tag = live.tags[0] if live.tags else None
    tag_name = tag.name if tag else None

    pull_url = f'http://localhost:8080/live/{live.stream_key}.flv'
    return jsonify({
        'message': '直播间信息获取成功',
        'data': {
            'liver_id': liver['liver_id'],
            'liver_name': liver['name'],
            'liver_avatar': liver['avatar_url'],
            'title': live.title,
            'tag': tag_name,  # 返回标签名称
            'cover_url': live.cover_url,
            'start_time': live.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': live.status,
            'pull_url': pull_url
        }
    })


@livehome_bp.route('/close_live/<id>',methods=['GET'])
def close_live(id):
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    live = Live.query.filter_by(id=id,user_id=user.id).first()
    if not live:
        return jsonify({'message': '直播间不存在'}), 404
    live.end_time = datetime.datetime.now()
    live.status = 'end'
    db.session.commit()
    delete_chat_message(live.id)
    update_total_duration(live.id)
    return jsonify({'message': '直播间关闭成功'})


@livehome_bp.route('/get_live_list', methods=['GET'])
def get_live_list():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401

    banned_me_list = get_banned_me_list(user.id)
    lives = Live.query.filter_by(status='live').all()

    data = []

    # 遍历所有直播间，生成未排序的 data 列表
    for live in lives:
        if live.user.id in banned_me_list:
            continue

        user_name = live.user.name  # 使用 `name` 字段
        user_avatar = live.user.avatar_url  # 使用 `avatar_url` 字段

        # 假设每个直播只有一个标签，获取第一个标签
        tag = live.tags[0] if live.tags else None
        tag_name = tag.name if tag else None

        data.append({
            'id': live.id,
            'title': live.title,
            'tags': tag_name,
            'thumbnail': live.cover_url,
            'streamer': user_name
        })

    # 获取推荐算法提供的直播排序列表
    data_sorted = recommend_lives(user.id, lives)
    # 将 data 转换为字典，键是直播间 ID，值是直播间信息
    data_dict = {item['id']: item for item in data}
    # 根据 data_sorted 的顺序，重新排列 data
    sorted_data = []
    for live_id in data_sorted:
        if live_id in data_dict:
            sorted_data.append(data_dict[live_id])
    return jsonify({'message': '直播间列表获取成功', 'data': sorted_data})

@livehome_bp.route('/livehistory',methods=['GET'])
def getlivehistory():
    page = request.args.get('page',1,type=int)
    page_size = request.args.get('pageSize',5,type=int)
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    query = Live.query.filter_by(user_id=user.id).order_by(Live.start_time.desc())
    pagination = query.paginate(page=page,per_page=page_size,error_out=False)
    records = []

    for live in pagination.items:
        records.append({
            'id':live.id,
            'user_id':live.user_id,
            'title':live.title,
            'tags':live.tags[0].name if live.tags else None,
            'cover_url':live.cover_url,
            'start_time':live.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status':live.status,
            'end_time':live.end_time.strftime('%Y-%m-%d %H:%M:%S') if live.end_time else None
        })
    return jsonify({
        'records':records,
        'currentPage':page,
        'totalPages':pagination.pages,
        'totalItems':pagination.total,
        'pageSize':page_size
    })

@livehome_bp.route('/check_live')
def check_live():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    #根据用户id查询live表，根据时间倒序，找到最新的一条记录，如果status为live，则返回正在直播，否则返回直播结束
    live = Live.query.filter_by(user_id=user.id,status='live').order_by(Live.start_time.desc()).first()
    if live:
        return jsonify({'status': 'live','stream_key':live.stream_key,'live_id':live.id})
    else:
        return jsonify({'status': 'end'})



#获取未读通知
@livehome_bp.route('/get_unread_notifications',methods=['GET'])
def get_unread_notifications_api():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    notifications = get_unread_notifications(user.id)

    return jsonify({'message': '获取成功', 'data': notifications})



#检查进入直播间用户的权限""
def check_live_permission(user_id, live_id):
    """
    检查用户的权限

    参数:
    - user_id (int): 用户的ID
    - live_id (int): 直播间的ID

    返回值:
    - number ,数字1代表普通用户，数字2代表房管，数字3代表主播
    """

    #先检查进入者是不是主播，如果是主播，直接返回3
    live = Live.query.filter_by(id=live_id).first()
    if live.user_id == user_id:
        return 3

    #检查用户是否是房管
    if check_moderator(user_id, live.user_id)[0]:
        return 2

    #如果不是房管也不是主播，则返回1
    return 1


@livehome_bp.route('/check_live_permission',methods=['POST'])
def check_live_permission_api():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    user_id = user.id
    live_id = request.json.get('live_id')

    permission = check_live_permission(user_id, live_id)
    return jsonify({'message': '权限检查成功', 'permission': permission})


#搜索功能
@livehome_bp.route('/search', methods=['GET'])
def search_lives():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'message': '请输入搜索内容'}), 400

    # 使用join来连接User表
    results = Live.query.join(Live.user).filter(
        Live.status == 'live',
        db.or_(
            Live.title.ilike(f"%{query}%"),
            User.name.ilike(f"%{query}%")
        )
    ).all()

    lives = []
    # 确保用户已登录再获取banned_me_list
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401

    banned_me_list = get_banned_me_list(user.id)

    for live in results:
        if live.user.id in banned_me_list:
            continue

        user_name = live.user.name
        user_avatar = live.user.avatar_url

        # 假设每个直播只有一个标签，获取第一个标签
        tag = live.tags[0] if live.tags else None
        tag_name = tag.name if tag else None

        lives.append({
            'id': live.id,
            'title': live.title,
            'tags': tag_name,
            'thumbnail': live.cover_url,
            'streamer': user_name
        })

    # 注意：这个return应该在for循环外面，否则只会返回第一个结果
    return jsonify({'message': '搜索结果获取成功', 'data': lives})


#搜索自动补全框接口
@livehome_bp.route('/search_autocomplete',methods=['GET'])
def search_autocomplete():
    query = request.args.get('q','')
    if len(query)<2:
        return jsonify({'suggestions': []})

    #查询直播标题
    title_results = db.session.query(Live.title).filter(
       Live.status == 'live',
       Live.title.ilike(f"%{query}%")
    ).limit(5).all()
    #查询用户名称(title_results)
    username_results = db.session.query(User.name).join(Live).filter(
        Live.status == 'live',
        User.name.ilike(f"%{query}%")
    ).limit(5).all()


#合并结果并去重
    suggesstions = []
    for title in title_results:
        suggesstions.append(title[0])
    for username in username_results:
        suggesstions.append(username[0])

    return jsonify({'suggestions': list(set(suggesstions))})



#红包相关的接口

#判断当前直播间是否已经存在红包活动了
def rp_is_expired(live_id):
    RP = RedPacket.query.filter_by(room_id=live_id,status='ongoing').first()
    # #并且检查红包的开奖时间是不是已经过了
    # print(RP.expire_time)
    # print(datetime.datetime.now())
    # print(RP.expire_time < datetime.datetime.now())
    if RP:
        if RP.expire_time > datetime.datetime.now():
            return True
        else:
            return False
    else:
        return False

#根据红包id返回红包信息
def get_redpacket(redpacket_id):
    red_packet = RedPacket.query.filter_by(id=redpacket_id).first()
    if not red_packet:
        return None
    else:
       #  red_packet_info = {
       #      'id':red_packet.id,
       #      'title':red_packet.title,
       #      "amount":red_packet.amount,
       #      "winner_num":red_packet.winner_num,
       #      "expire_time":red_packet.expire_time,
       #      "status":red_packet.status
       # }
       #  print(f"packet_info:{red_packet_info}")
        return  red_packet
#检查直播间是否有红包，如果有，返回红包信息,和用户的参与情况
def check_red_packet(live_id, user_id):
    # 获取所有进行中的红包
    red_packets = RedPacket.query.filter_by(room_id=live_id, status='ongoing').all()

    # 查找未过期的红包
    red_packet = None
    for rp in red_packets:
        if rp.expire_time > datetime.datetime.now():
            red_packet = rp
            break

    if not red_packet:
        return None

    # 检查用户是否有参与过抢红包的活动
    red_packet_participant = RedPacketParticipant.query.filter_by(
        redpacket_id=red_packet.id,
        user_id=user_id
    ).first()

    red_packet_info = {
        'id': red_packet.id,
        'title': red_packet.title,
        "amount": red_packet.amount,
        "winner_num": red_packet.winner_num,
        "expire_time": red_packet.expire_time,
        'has_join': red_packet_participant is not None,
    }

    return red_packet_info


#用户参与红包活动
def join_red_packet(red_packet_id, user_id):
    #检查红包是否存在
    print(red_packet_id)
    red_packet = RedPacket.query.filter_by(id=red_packet_id,status='ongoing').first()
    if not red_packet:
        return False , '红包不存在或已结束'
    #检查用户是否已经参与过红包活动
    red_packet_participant = RedPacketParticipant.query.filter_by(redpacket_id=red_packet_id,user_id=user_id).first()

    if red_packet_participant:
        return False , '您已经参与过该活动'
    #如果用户没参与过，就创建一条红包参与记录
    red_packet_participant = RedPacketParticipant(redpacket_id=red_packet_id,user_id=user_id,participate_time=datetime.datetime.now())
    db.session.add(red_packet_participant)
    db.session.commit()
    return True , '参与成功'


from sqlalchemy.exc import SQLAlchemyError


#更新·红包·中奖者的余额和交易记录
def update_winner_balance(red_packet, red_packet_participants, score):
    try:
        # 移除了 db.session.begin()，由外层函数管理事务

        for participant in red_packet_participants:
            participant.is_winner = True
            participant.award_amount = score

            wallet = Wallet.query.filter_by(user_id=participant.user_id).with_for_update().first()
            wallet.balance += score

            transaction = Transaction(
                user_id=participant.user_id,
                transaction_type='红包',
                amount=score,
                reference_id=red_packet.id,
                description='红包活动',
                balance_after=wallet.balance,
                created_at=datetime.datetime.now()
            )
            db.session.add(transaction)

        red_packet.status = 'finished'
        return [participant.user.name for participant in red_packet_participants]

    except SQLAlchemyError as e:
        current_app.logger.error(f"Error updating winner balance: {str(e)}")
        raise


#分配红包函数
def allocate_red_packet(red_packet_id):
    try:
        # 移除了 db.session.begin()，由外层函数管理事务

        red_packet = RedPacket.query.filter_by(id=red_packet_id).with_for_update().first()
        if not red_packet:
            print("红包不存在")
            return []

        red_packet_participants = RedPacketParticipant.query.filter_by(
            redpacket_id=red_packet_id
        ).all()

        winner_num = red_packet.winner_num

        if not red_packet_participants:
            print("没有人参与过红包活动")
            return []

        if len(red_packet_participants) <= winner_num:
            score = red_packet.amount / len(red_packet_participants)
        else:
            red_packet_participants = random.sample(red_packet_participants, winner_num)
            score = red_packet.amount / winner_num

        return update_winner_balance(red_packet, red_packet_participants, score)

    except SQLAlchemyError as e:
        current_app.logger.error(f"Error allocating red packet: {str(e)}")
        raise


@livehome_bp.route('/rp_is_expired',methods=['GET'])
def rp_is_expired_api():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    live_id = request.args.get('live_id')
    result = rp_is_expired(live_id)
    if result:
        return jsonify({'message': '红包存在，请等待红包活动结束才能继续发送','status':True})
    else:
        return jsonify({'message': '当前直播间没有红包活动','status':False})

@livehome_bp.route('/join_red_packet',methods=['POST'])
def join_red_packet_api():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    data = request.get_json()
    red_packet_id = data.get('red_packet_id')
    result, message = join_red_packet(red_packet_id, user.id)
    if result:
        return jsonify({'message': message}) , 200
    else:
        return jsonify({'message': message}), 400    # 参与失败，返回400状态码

@livehome_bp.route('/check_red_packet',methods=['GET'])
def check_red_packet_api():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    live_id = request.args.get('live_id')
    red_packet_info = check_red_packet(live_id, user.id)
    if red_packet_info:
        return jsonify({'message': '红包信息获取成功', 'data': red_packet_info})
    else:
        return jsonify({'message': '当前直播间没有红包',"data":None})


def get_redpacket_result(red_packet_id):
    red_packet = RedPacket.query.filter_by(id=red_packet_id).first()
    if not red_packet:
        return None
    else:
        red_packet_participants = RedPacketParticipant.query.filter_by(
            redpacket_id=red_packet_id,
            is_winner=True
        ).all()
        return [participant.user.name for participant in red_packet_participants]    # 返回中奖者的用户名列表
@livehome_bp.route('/get_redpacket_result',methods=['GET'])
def get_redpacket_result_api():
    print("----有被调用------")
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    red_packet_id = request.args.get('red_packet_id')
    winner_names = get_redpacket_result(red_packet_id)
    if winner_names:
        return jsonify({'message': '红包结果获取成功', 'data': winner_names}),200
    else:
        return jsonify({'message': '红包不存在或已结束',"data":None}),400


@livehome_bp.route('/get_live_id_by_mine',methods=['GET'])
def get_live_id_by_mine():
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    live_list = Live.query.filter_by(user_id=user.id).first()
    if live_list:
        return jsonify({'message': '获取成功', 'data': live_list.id}),200
    else:
        return jsonify({'message': '当前用户没有直播间',"data":None}),400
