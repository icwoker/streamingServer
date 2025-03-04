from app.db.database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    avatar_uel = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.String(255), nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    is_live = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return{
            'id': self.id,
            'name': self.name,
            'password': self.password,
            'avatar_uel': self.avatar_uel,
            'bio': self.bio,
            'is_live': self.is_live,
            'is_banned': self.is_banned,
            'created_at': self.created_at,
        }


# 创建关注关系表
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key= True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) #关注者
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) #被关注者
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return{
            'id': self.id,
            'follower_id': self.follower_id,
            'followed_id': self.followed_id,
            'created_at': self.created_at,
        }

#创建直播表

class Live(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 外键
    title = db.Column(db.String(50), nullable=False)
    cover_url = db.Column(db.String(255), nullable=False)
    tags = db.Column(db.String(255), nullable=False)
    stream_key = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)

    # 定义与 User 的关系
    user = db.relationship('User', backref=db.backref('lives', lazy=True))



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
    id = db.Column(db.Integer, primary_key= True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) #用户 id
    live_id = db.Column(db.String(255), db.ForeignKey('live.id'), nullable=False) #直播 id
    watched_at = db.Column(db.DateTime, default=db.func.now()) #观看时间

    def to_dict(self):
        return{
            'id': self.id,
            'user_id': self.user_id,
            'live_id': self.live_id,
            'watched_at': self.watched_at,
        }

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