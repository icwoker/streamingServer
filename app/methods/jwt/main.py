"""
创建一个jwt装饰器，用于验证请求头中的JWT
"""

from functools import wraps
from flask import request, jsonify,current_app
import jwt
from app.models.user import User


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]

        if not token:
            return jsonify({'message':"没有提供token!"}) , 401
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['id'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message':"token过期!"}) , 401
        except jwt.InvalidTokenError:
            return jsonify({'message':"无效的token!"}) , 401

        return f(current_user, *args, **kwargs)

    return decorated