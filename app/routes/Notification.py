from app.models.user import User,Notification
from app.db.database import db

#写入一条记录
def write_notification(user_id, sender_id, content, type, reference_id=None):
    try:
        notification = Notification(user_id=user_id, sender_id=sender_id, content=content, type=type, reference_id=reference_id)
        db.session.add(notification)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error writing notification: {str(e)}")
        return False

#获取用户收到的通知列表
def get_user_notifications(user_id, page, page_size):
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return notifications


#获取最新未读的通知给前端""
def get_unread_notifications(user_id):
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).order_by(
        Notification.created_at.desc()).all()

    notification_list = []
    # 批量更新为已读状态
    if notifications:
        for notification in notifications:
            notification.is_read = True
        notification_list.append({
            'content':notification.content,
            'sender_id':notification.sender_id,
            'type':notification.type.name,
            'created_at':notification.created_at.isoformat(),
        })
        ## 仅在循环外提交一次
        db.session.commit()

    return notification_list


def batch_write_notifications(sender_id, content, type, reference_id=None, user_ids=None):
    """
    批量发送通知给多个用户（如主播给粉丝发送开播通知）

    参数:
    - sender_id: 发送者ID（如主播ID）
    - content: 通知内容（如"xxx开始直播了"）
    - type: 通知类型（如LIVE_START）
    - reference_id: 相关ID（如直播间ID）
    - user_ids: 接收通知的用户ID列表（粉丝列表）
    """
    try:
        # 创建所有通知对象，但暂不提交
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                sender_id=sender_id,
                content=content,
                type=type,
                reference_id=reference_id
            )
            notifications.append(notification)

        # 批量添加所有通知
        db.session.bulk_save_objects(notifications)
        db.session.commit()
        return True, len(notifications)
    except Exception as e:
        db.session.rollback()
        print(f"Error sending batch notifications: {str(e)}")
        return False, 0


