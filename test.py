from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123456@localhost:5432/test'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#初始化SQLAlchemy对象

db = SQLAlchemy(app)

#定义一个示例模型""
class User(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(50),nullable=False)
    email = db.Column(db.String(100),unique=True,nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "Flask app connected to PostgreSQL database"

if __name__ == '__main__':
    app.run(debug=True)