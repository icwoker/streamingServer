from flask import Blueprint,request,jsonify,current_app,make_response
from app.routes.auth import get_user_from_token
import os
from app.models.user import Live
from app.methods.image.main import save_image
import datetime
from app.db.database import db
import uuid
livehome_bp = Blueprint('livehome', __name__)
from app.env import BASE_DIR
from flask_socketio import SocketIO
socketio = SocketIO()

LIVE_IMAGE_DIR = os.path.join(BASE_DIR,'static','image','live')

def init_livehome(app):
    socketio.init_app(app, cors_allowed_origins="*")
@livehome_bp.route('/create_room',methods=['POST'])
def create_room():
    title = request.form.get('title')
    tags = request.form.get('category')
    image = request.files.get('cover')
    user = get_user_from_token()
    if user is None:
        return jsonify({'message': '未登录或登录已过期'}), 401
    user_id = user.id
    if not title or not tags or not image:
        return jsonify({'message': '请输入直播间标题、标签和封面'}), 400
    image_name = str(user_id) + '.' + image.filename.split('.')[-1]
    save_image(image, LIVE_IMAGE_DIR, image_name)
    ImagePath = os.path.join('static','image','live',image_name)
    stream_key = f'liveroom_{user_id}'
    id = uuid.uuid4()
    live = Live(id=id,user_id=user_id,title=title,tags=tags,cover_url=ImagePath,start_time=datetime.datetime.now()
                ,stream_key=stream_key,status='live')
    #找到之前的直播间（根据start_time最晚的那条记录），查看是否关闭了，如果关闭了，重新打开，如果没有关闭，关闭之前的直播，并设置end_time
    previous_live = db.session.query(Live).filter_by(user_id=user_id,status='live').order_by(Live.start_time.desc()).first()
    if previous_live:
        previous_live.end_time = datetime.datetime.now()
        previous_live.status = 'end'
        db.session.commit()
    db.session.add(live)
    db.session.commit()
    return jsonify({'message': '直播间创建成功','stream_key':stream_key,'live_id':id})


def get_live_by_id(id):
    live = Live.query.filter_by(id=id).first()
    if not live:
        return {"error": "Live not found"}, 404

    # 确保访问的是正确的字段名
    user_name = live.user.name  # 使用 `name` 字段
    user_avatar = live.user.avatar_uel  # 使用 `avatar_url` 字段
    liver_id = live.user_id
    user= {
        'liver_id': liver_id,
        'name': user_name,
        'avatar_url': user_avatar
    }
    return live, user

@livehome_bp.route('/get_live_by_id/<id>',methods=['GET'])
def get_live_by_id_api(id):
    live,liver = get_live_by_id(id)
    if live is None:
        return jsonify({'message': '直播间不存在'}), 404
    pull_url = f'http://localhost:8080/live/{live.stream_key}.flv'
    return jsonify({'message': '直播间信息获取成功', 'data': {'liver_id':liver['liver_id'],'liver_name':liver['name'],'liver_avatar':liver['avatar_url'],
                                                              'title': live.title, 'tags': live.tags,
                                                              'cover_url': live.cover_url,
                                                              'start_time': live.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                            'status': live.status, 'pull_url': pull_url}})


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
    return jsonify({'message': '直播间关闭成功'})


@livehome_bp.route('/get_live_list',methods=['GET'])
def get_live_list():
    lives = Live.query.filter_by(status='live').all()
    data = []
    for live in lives:
        user_name = live.user.name  # 使用 `name` 字段
        user_avatar = live.user.avatar_uel  # 使用 `avatar_url` 字段
        data.append({'id': live.id, 'title': live.title, 'tags': live.tags, 'thumbnail': live.cover_url,
                      'streamer': user_name})
    return jsonify({'message': '直播间列表获取成功', 'data': data})

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
            'tags':live.tags,
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