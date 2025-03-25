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
from app.models.user import Live,WatchHistory,Tag,LiveTag,Follow,NotificationType
from app.routes.ChatMessage import delete_chat_message
from app.routes.LiveStatistics import create_LiveStatistics , update_total_duration
from app.routes.liveBanned import get_banned_me_list
from app.routes.Notification import batch_write_notifications, get_unread_notifications
from app.methods.recommend import recommend_lives
import json
import queue
import threading
import time


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

