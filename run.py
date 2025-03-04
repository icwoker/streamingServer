# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
#
# app = Flask(__name__)
#
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123456@localhost:5432/test'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#
# #初始化SQLAlchemy对象
#
# db = SQLAlchemy(app)
#
# #定义一个示例模型""
# class User(db.Model):
#     id = db.Column(db.Integer,primary_key=True)
#     name = db.Column(db.String(50),nullable=False)
#     email = db.Column(db.String(100),unique=True,nullable=False)
#
# with app.app_context():
#     db.create_all()
#
# @app.route('/')
# def index():
#     return "Flask app connected to PostgreSQL database"
#
# if __name__ == '__main__':
#     app.run(debug=True)


from app import create_app

# 创建 Flask 应用实例
app = create_app()

# 获取 socketio 实例
# 注意：socketio 是通过 create_app 初始化的，不能直接从全局变量导入
from app import socketio

if __name__ == '__main__':
    # 启动应用
    socketio.run(app, host='0.0.0.0', port=5000)