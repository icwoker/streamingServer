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
from app.routes.watchHistory import watchHistory_bp
from app.routes.follow import follow_bp
from app.routes.liveModerator import liveModerator_bp
from app.routes.liveBanned import liveBanned_bp
from app.routes.ChatMessage import ChatMessage_bp
from app.routes.LiveStatistics import LiveStatistics_bp

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
    app.register_blueprint(watchHistory_bp, url_prefix='/api/watchHistory')
    app.register_blueprint(follow_bp, url_prefix='/api/follow')
    app.register_blueprint(liveModerator_bp, url_prefix='/api/liveModerator')
    app.register_blueprint(liveBanned_bp, url_prefix='/api/liveBanned')
    app.register_blueprint(ChatMessage_bp, url_prefix='/api/ChatMessage')
    app.register_blueprint(LiveStatistics_bp, url_prefix='/api/LiveStatistics')

    # 创建数据库表
    with app.app_context():
        db.create_all()

    CORS(app, supports_credentials=True)
    socketio = SocketIO(app, cors_allowed_origins="*")
    init_livehome(app,socketio)
    app.secret_key = Config.SECRET_KEY
    return app