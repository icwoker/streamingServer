from flask import Blueprint, send_file, session, jsonify, request
from sqlalchemy import func

from app.models.user import Live,User,LiveStatistics,GiftRecord,WatchHistory
from app.routes.auth import get_user_from_token
from app.db.database import db
import uuid
import datetime

LiveStatistics_bp = Blueprint('LiveStatistics_bp', __name__)

#先创造一条(只在开始直播的时候，创建一条)

def create_LiveStatistics(live_id):
   try:
       print("开始创建记录")
       live_statistics = LiveStatistics(
           live_id=live_id,
           peak_viewers=0,
           total_duration=0,
           total_gifts=0.0,
           total_messages=0,
           total_viewers=0,
       )
       db.session.add(live_statistics)
       db.session.commit()
       print('创建成功')
       return live_statistics
   except Exception as e:
       db.session.rollback()
       # 记录日志
       print(f'发生错误: {str(e)}')
       return None


#各项指标的细化更新
#最高同时在线人数
def update_peak_viewers(live_id, viewers):
    try:
        live_statistics = LiveStatistics.query.filter_by(live_id=live_id).first()
        if not live_statistics:
            return False
        if live_statistics.peak_viewers < viewers:
            live_statistics.peak_viewers = viewers
            db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        # 记录日志
        return False

#一口气更新一些其他表中联动的指标，（直播时长，礼物价值,观看人数）
def update_total_duration(live_id):
    try:
        # 获取直播信息和统计信息
        live = Live.query.filter_by(id=live_id).first()
        live_statistics = LiveStatistics.query.filter_by(live_id=live_id).first()

        if not live or not live_statistics:
            return False

        # 计算直播时长
        if live.end_time and live.start_time:
            live_duration = live.end_time - live.start_time
            live_statistics.total_duration = live_duration.total_seconds()

        # 使用子查询计算礼物总价值
        total_gifts = db.session.query(func.sum(GiftRecord.total_price)) \
                          .filter(GiftRecord.live_id == live_id).scalar() or 0.0
        live_statistics.total_gifts = total_gifts

        # 计算观众数量
        viewers_count = db.session.query(func.count(WatchHistory.id)) \
                            .filter(WatchHistory.live_id == live_id).scalar() or 0
        live_statistics.total_viewers = viewers_count

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        # 记录日志
        return False


#实时更新弹幕数量
def update_total_messages(live_id):
    # 使用原子更新操作
    LiveStatistics.query.filter_by(live_id=live_id).update(
        {LiveStatistics.total_messages: LiveStatistics.total_messages + 1}
    )
    db.session.commit()


#获取直播统计信息，返回给前端

def get_live_statistics(live_id):
    try:
        live_statistics = LiveStatistics.query.filter_by(live_id=live_id).first()
        if not live_statistics:
            return None
        return {
            'peak_viewers': live_statistics.peak_viewers,
            'total_duration': live_statistics.total_duration,
            'total_gifts': live_statistics.total_gifts,
            'total_messages': live_statistics.total_messages,
            'total_viewers': live_statistics.total_viewers,
        }
    except Exception as e:
        db.session.rollback()
        # 记录日志
        return None

@LiveStatistics_bp.route('/get_live_statistics',methods=['GET'])
def get_live_statistics_api():
    live_id = request.args.get('live_id')
    if not live_id:
        return jsonify({'code': 400, 'data': '参数错误'})
    live_statistics = get_live_statistics(live_id)
    if not live_statistics:
        return jsonify({'code': 400, 'data': '直播不存在'})
    return jsonify({'code': 200, 'data': live_statistics})

