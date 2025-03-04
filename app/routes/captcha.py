from flask import Blueprint, send_file, session, jsonify, request
from io import BytesIO
from app.methods.captcha.main import CaptachaGenerator
from datetime import datetime, timedelta


captcha_bp = Blueprint('captcha', __name__)


@captcha_bp.route('/generate', methods=['GET'])
def get_captcha():
    generator = CaptachaGenerator()
    captcha_data = generator.generate_captcha()

    session['captcha_text'] = captcha_data['text']
    session['captcha_time'] = captcha_data['created_at']

    print('Session after generate:', session)#调试用

    return send_file(
        BytesIO(captcha_data['image']),
        mimetype='image/png'
    )


@captcha_bp.route('/verify', methods=['POST'])
def verify_captcha():
    print('Session before verify:', session)#调试用
    user_input = request.json.get('captcha')
    stored_captcha = session.get('captcha_text')
    captcha_time = session.get('captcha_time')

    if not stored_captcha or not captcha_time:
        return jsonify({'success': False, 'message': '验证码已过期'})

    # 检查验证码是否超时（例如 5 分钟）
    captcha_time = datetime.fromtimestamp(captcha_time)
    if datetime.now() - captcha_time > timedelta(minutes=5):
        return jsonify({'success': False, 'message': '验证码已过期'})

    if user_input.upper() == stored_captcha.upper():
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '验证码错误'})