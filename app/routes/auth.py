import jwt
from flask import Blueprint,request,jsonify,current_app,make_response
from app.models.user import User
from app.db.database import db
from app.methods.passwordUtils.main import check_password_hash,generate_password_hash
from datetime import timedelta,datetime
from app.methods.jwt.main import token_required
import os
from app.methods.image.main import save_image
from app.env import BASE_DIR

auth_bp = Blueprint('auth',__name__)
AVATAR_PATH = os.path.join(BASE_DIR,'static','image','avatar')
UPLOAD_FOLDER = 'static/images/avatars'  # 假设在 static 文件夹下

def error_response(message, status_code):
    return jsonify({'error': message}), status_code


@auth_bp.route('/register',methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error':"每个字段不能为空"})
    name = data.get('username')
    password = data.get('password')
    if name and password:
        user = User(name=name,password=password)
        user.password = generate_password_hash(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message':"注册成功"})
    else:
        return jsonify({'error':"每个字段不能为空"})


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return error_response("请求数据不能为空", 400)

    name = data.get('username')
    password = data.get('password')

    if not name or not password:
        return error_response("用户名和密码不能为空", 400)

    user = User.query.filter_by(name=name).first()
    if not user:
        return error_response("用户不存在", 401)

    if not check_password_hash(user.password, password):
        return error_response("密码错误", 401)

    # 生成 JWT Token
    token = jwt.encode({
        'id': user.id,
        'exp': datetime.utcnow() + timedelta(days=1)  # 设置过期时间为 1 天
    },
    current_app.config['JWT_SECRET_KEY'],
    algorithm='HS256'
    )

    # 创建响应对象
    response = make_response(jsonify({'message': "登录成功",'user_id': user.id, 'user_name': user.name}), 200)

    # 将 Token 存储在 HttpOnly Cookie 中
    response.set_cookie(
        key='auth_token',          # Cookie 名称
        value=token,              # Token 值
        httponly=True,            # 防止 JavaScript 访问
        # secure=True,              # 仅通过 HTTPS 传输 (生产环境)
        secure=False,           # 仅通过 HTTPS 传输 (开发环境)
        samesite='Lax',           # 防止 CSRF 攻击
        max_age=86400             # 设置有效期为 1 天（秒）
    )

    return response


@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'message': "退出成功"}), 200)
    response.set_cookie(
        key='auth_token',
        value='',
        expires=0,  # 立即过期
        httponly=True,
        secure=True,
        samesite='Lax'
    )
    return response

@auth_bp.route('/test', methods=['GET'])
@token_required
def test():
    users = User.query.all()  # 查询所有用户
    users_list = [user.to_dict() for user in users]  # 将每个用户对象转换为字典
    return jsonify(users_list)  # 返回 JSON 格式的用户列表

@auth_bp.route('/get_path_test',methods=['GET'])
def get_path_test():
    return jsonify({'path': AVATAR_PATH})

def get_user_from_token():
    token = request.cookies.get('auth_token')
    if not token:
        return None
    try:
        data = jwt.decode(token,current_app.config['JWT_SECRET_KEY'],algorithms=['HS256'])
        user = User.query.filter_by(id=data['id']).first()
        return user
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None



@auth_bp.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401

    file = request.files['avatar']
    if not file:
        return jsonify({'message': '请选择文件'}), 400
    ImageName = str(user.id) + '.' + file.filename.split('.')[-1]
    ImagePath = os.path.join('static','image','avatar',ImageName)
    save_image(file, AVATAR_PATH, ImageName)
    user.avatar_url = ImagePath
    db.session.commit()
    return jsonify({'message': '上传成功', 'avatar_url': user.avatar_url}), 200

@auth_bp.route('/me',methods=['GET'])
def get_me_info():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401

    return jsonify({'user_id': user.id, 'user_name': user.name,'bio': user.bio,'avatar_url': user.avatar_url}) , 200

@auth_bp.route('/change_me_info',methods=['POST'])
def change_me_info():
    user = get_user_from_token()
    if not user:
        return jsonify({'message': '未登录或登录已过期'}), 401
    data = request.get_json()
    if not data:
        return jsonify({'message': '请求数据不能为空'}), 400
    bio = data.get('bio')
    name = data.get('username')
    if not bio or not name:
        return jsonify({'message': '用户名和简介不能为空'}), 400
    user.bio = bio
    user.name = name
    db.session.commit()
    return jsonify({'message': '修改成功', 'bio': user.bio, 'username': user.name}), 200