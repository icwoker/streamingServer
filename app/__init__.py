from flask import Flask
from app.config import Config
from app.db.database import db
from app.routes.auth import auth_bp
from app.routes.captcha import captcha_bp
from flask_cors import CORS
from app.config import Config
from app.routes.transaction import transaction_bp
from app.routes.livehome import init_livehome
from flask_socketio import SocketIO

socketio = None
def create_app():
    global socketio
    app = Flask(__name__,static_folder='static')

    # 确保在初始化数据库之前加载配置
    app.config.from_object(Config)

    # 初始化数据库
    db.init_app(app)

    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(captcha_bp, url_prefix='/api/captcha')
    app.register_blueprint(transaction_bp, url_prefix='/api/transaction')
    # app.register_blueprint(livehome_bp, url_prefix='/api/livehome')

    # 创建数据库表
    with app.app_context():
        db.create_all()

    CORS(app, supports_credentials=True)
    socketio = SocketIO(app, cors_allowed_origins="*")
    init_livehome(app,socketio)
    app.secret_key = Config.SECRET_KEY
    return app