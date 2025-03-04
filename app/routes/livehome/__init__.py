from flask import Blueprint
from .socket import init_socket

livehome_bp = Blueprint('livehome', __name__)


def init_livehome(app, socketio):
    # 初始化 WebSocket 逻辑
    init_socket(socketio)

    # 注册 livehome 蓝图
    from .routes import livehome_bp
    app.register_blueprint(livehome_bp, url_prefix='/api/livehome')