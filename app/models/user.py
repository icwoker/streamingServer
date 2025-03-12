from app.db.database import db
import enum
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.String(255), nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    stream_key = db.Column(db.String(64), unique=True, nullable=True)  # 推流码
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return{
            'id': self.id,
            'name': self.name,
            'password': self.password,
            'avatar_url': self.avatar_uel,
            'bio': self.bio,
            'is_banned': self.is_banned,
            'created_at': self.created_at,
        }


# 创建关注关系表
class Follow(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # 添加联合唯一索引
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='uix_follow'),)

    def to_dict(self):
        return{
            'id': self.id,
            'follower_id': self.follower_id,
            'followed_id': self.followed_id,
            'created_at': self.created_at,
        }

#创建直播表

class LiveStatus(enum.Enum):
    PENDING = "pending"
    LIVE = "live"
    ENDED = "ended"
    BANNED = "banned"

#直播标签表
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

#创建直播-标签中间表
class LiveTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    live_id = db.Column(db.String(255), db.ForeignKey('live.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)

    # 添加联合唯一索引，确保一个直播不会重复添加同一个标签
    __table_args__ = (db.UniqueConstraint('live_id', 'tag_id', name='uix_live_tag'),)

    def to_dict(self):
        return{
            'id': self.id,
            'live_id': self.live_id,
            'tag_id': self.tag_id,
        }

class Live(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 外键
    title = db.Column(db.String(50), nullable=False)
    cover_url = db.Column(db.String(255), nullable=False)
    # tags = db.Column(db.String(255), nullable=False)
    stream_key = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default=LiveStatus.PENDING)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)

    # 定义与 User 的关系
    user = db.relationship('User', backref=db.backref('lives', lazy=True))

    # 添加与 Tag 的多对多关系
    tags = db.relationship('Tag', secondary='live_tag', backref=db.backref('lives', lazy='dynamic'))


    def to_dict(self):
        return{
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'cover_url': self.cover_url,
           'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status,
            'tags': self.tags,
            'stream_key': self.stream_key,
        }

#创建观看历史纪录表
class WatchHistory(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    live_id = db.Column(db.String(255), db.ForeignKey('live.id'), nullable=False)
    watched_at = db.Column(db.DateTime, default=db.func.now())
    watch_duration = db.Column(db.Integer, default=0,nullable=True)  # 观看时长（秒）


    live = db.relationship('Live', backref=db.backref('watch_history', lazy=True))

    # 添加索引
    __table_args__ = (
        db.Index('idx_watch_history_user_id', 'user_id'),
        db.Index('idx_watch_history_live_id', 'live_id'),
    )
    #确保记录的唯一性列，保证live_id和user_id的联合唯一性
    __table_args__ = (
        db.UniqueConstraint('user_id', 'live_id', name='unique_user_live'),
    )
    def to_dict(self):
        return{
            'id': self.id,
            'user_id': self.user_id,
            'live_id': self.live_id,
            'liver_id': self.liver_id,
            'watched_at': self.watched_at,
        }


#礼物表
class Gift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)#礼物名称
    description = db.Column(db.String(255), nullable=True)#描述
    price = db.Column(db.Float, nullable=False)  # 礼物价格

#礼物赠送表
class GiftRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    live_id = db.Column(db.String(255), db.ForeignKey('live.id'), nullable=False)
    gift_id = db.Column(db.Integer, db.ForeignKey('gift.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # 定义关系
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_gifts')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_gifts')
    live = db.relationship('Live', backref='gift_records')
    gift = db.relationship('Gift', backref='gift_records')



#钱包表
class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    balance = db.Column(db.Float, default=0.0)  # 余额
    total_income = db.Column(db.Float, default=0.0)  # 总收入
    total_expense = db.Column(db.Float, default=0.0)  # 总支出
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    #定义关系
    user = db.relationship('User', backref=db.backref('wallet', lazy=True))

#创建虚拟礼物表
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 用户 ID
    transaction_type = db.Column(db.String(50), nullable=False)  # 交易类型（如充值、送礼物、退款等）
    amount = db.Column(db.Float, nullable=False)  # 交易金额（正数表示增加，负数表示减少）
    balance_after = db.Column(db.Float, nullable=False)  # 交易后的余额
    reference_id = db.Column(db.String(100), nullable=True)  # 关联的外部 ID（如支付平台订单号）
    description = db.Column(db.String(255), nullable=True)  # 交易描述
    created_at = db.Column(db.DateTime, default=db.func.now())  # 交易时间

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'balance_after': self.balance_after,
            'reference_id': self.reference_id,
            'description': self.description,
            'created_at': self.created_at,
        }




#弹幕表
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 发送者
    live_id = db.Column(db.String(255), db.ForeignKey('live.id'), nullable=False)  # 直播ID
    content = db.Column(db.String(500), nullable=False)  # 消息内容
    is_highlighted = db.Column(db.Boolean, default=False)  # 是否高亮消息（付费消息）
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'live_id': self.live_id,
            'content': self.content,
            'is_highlighted': self.is_highlighted,
            'created_at': self.created_at,
        }


class NotificationType(enum.Enum):
    FOLLOW = "follow"  # 关注通知
    LIVE_START = "live_start"  # 直播开始通知
    GIFT = "gift"  # 礼物通知
    SYSTEM = "system"  # 系统通知

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 接收通知的用户
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 发送通知的用户（可能是系统）
    type = db.Column(db.Enum(NotificationType), nullable=False)  # 通知类型
    content = db.Column(db.String(500), nullable=False)  # 通知内容
    reference_id = db.Column(db.String(255), nullable=True)  # 相关ID（如直播ID、礼物ID等）
    is_read = db.Column(db.Boolean, default=False)  # 是否已读
    created_at = db.Column(db.DateTime, default=db.func.now())


class LiveBannedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    banned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 谁封禁的
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # 添加联合唯一索引，确保一个用户在一个直播间只被封禁一次
    __table_args__ = (db.UniqueConstraint('banned_by', 'user_id', name='uix_live_banned_user'),)


class LiveModerator(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 管理员ID
    appointed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 谁任命的
    created_at = db.Column(db.DateTime, default=db.func.now())

    # 添加联合唯一索引
    __table_args__ = (db.UniqueConstraint('appointed_by', 'user_id', name='uix_live_moderator'),)



class LiveStatistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    live_id = db.Column(db.String(255), db.ForeignKey('live.id'), nullable=False, unique=True)
    peak_viewers = db.Column(db.Integer, default=0)  # 最高同时在线人数
    total_viewers = db.Column(db.Integer, default=0)  # 总观看人数
    total_duration = db.Column(db.Integer, default=0)  # 直播总时长（秒）
    total_gifts = db.Column(db.Float, default=0.0)  # 总礼物价值
    total_messages = db.Column(db.Integer, default=0)  # 总消息数
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    #定义关系
    live = db.relationship('Live', backref=db.backref('statistics', lazy=True))