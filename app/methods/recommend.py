import numpy as np
from collections import Counter
from sqlalchemy import func
from sklearn.metrics.pairwise import cosine_similarity
from app.models.user import WatchHistory, Live, Follow, LiveStatistics
from app.db.database import db


def recommend_lives(user_id, live_list=None):
    """
    根据当前正在直播的直播列表和用户信息，返回排序后的直播id列表。

    算法逻辑：
      1. 如果用户关注的主播正在直播，则优先推荐这部分，并
         根据用户最近5次观看该主播的观看时长排序。
      2. 对于非关注主播：
           a. 如果用户有观看记录，则构造用户兴趣标签向量，
              并计算每个直播的标签（用二值表示）与用户兴趣的余弦相似度，
              同时结合直播热度和主播粉丝数做综合排序。
           b. 如果用户没有观看记录，则直接根据直播热度（及主播粉丝数）排序。
      3. 最终返回直播id列表。
    """
    # 若未传入直播列表，则查询当前所有开播的直播
    if live_list is None:
        live_list = Live.query.filter(Live.status == "live").all()

    # 获取用户关注的主播ID集合
    follows = Follow.query.filter(Follow.follower_id == user_id).all()
    followed_user_ids = set([f.followed_id for f in follows])

    # 预先查询所有主播的粉丝数（用于后续辅助排序）
    fan_counts = dict(db.session.query(Follow.followed_id, func.count(Follow.id))
                      .group_by(Follow.followed_id).all())

    # 分组：关注的主播与非关注的主播
    followed_lives = []
    non_followed_lives = []
    for live in live_list:
        if live.user_id in followed_user_ids:
            followed_lives.append(live)
        else:
            non_followed_lives.append(live)

    recommended_lives = []

    # 1. 优先推荐关注的主播直播
    if followed_lives:
        live_scores = {}
        for live in followed_lives:
            # 查询用户最近5条观看该直播的记录，并累计观看时长
            records = (WatchHistory.query
                       .filter_by(user_id=user_id, live_id=live.id)
                       .order_by(WatchHistory.watched_at.desc())
                       .limit(5)
                       .all())
            total_duration = sum([r.watch_duration for r in records])
            live_scores[live] = total_duration
        # 根据观看时长降序排序
        followed_lives_sorted = sorted(followed_lives, key=lambda live: live_scores.get(live, 0), reverse=True)
        recommended_lives.extend(followed_lives_sorted)

    # 2. 对于非关注主播，根据用户观看记录进行推荐
    # 查询用户最近5条观看记录（全局）
    recent_histories = (WatchHistory.query
                        .filter_by(user_id=user_id)
                        .order_by(WatchHistory.watched_at.desc())
                        .limit(5)
                        .all())

    non_followed_scored = []
    if recent_histories:
        # 构造用户兴趣标签向量，观看时长作为权重
        user_tag_counter = Counter()
        for record in recent_histories:
            # 假设 record.live.tags 为包含标签对象的列表，每个标签对象有 name 属性
            for tag in record.live.tags:
                user_tag_counter[tag.name] += record.watch_duration

        # 如果用户存在兴趣标签，则构造向量空间
        if user_tag_counter:
            tag_space = list(user_tag_counter.keys())
            user_vector = np.array([user_tag_counter[tag] for tag in tag_space], dtype=float)
        else:
            user_vector = None

        for live in non_followed_lives:
            # 计算标签相似度
            if user_vector is not None:
                live_tags = [tag.name for tag in live.tags]
                # 构造直播的标签二值向量
                live_vector = np.array([1.0 if tag in live_tags else 0.0 for tag in tag_space])
                # 计算余弦相似度（注意：如果向量均为0，则设为0）
                if np.linalg.norm(user_vector) == 0 or np.linalg.norm(live_vector) == 0:
                    sim = 0.0
                else:
                    sim = cosine_similarity([user_vector], [live_vector])[0][0]
            else:
                sim = 0.0

            # 直播热度：使用直播统计中的 total_viewers（没有数据则为0）
            #获取直播热度统计的数据
            live_statistics = LiveStatistics.query.filter_by(live_id=live.id).first()
            heat = live_statistics.total_viewers if live.statistics else 0
            # 主播粉丝数
            fans = fan_counts.get(live.user_id, 0)
            # 综合得分：先看标签相似度，再看热度，最后看粉丝数
            non_followed_scored.append((live, sim, heat, fans))

        # 降序排序：以 (标签相似度, 热度, 粉丝数) 为排序依据
        non_followed_scored_sorted = sorted(non_followed_scored,
                                            key=lambda x: (x[1], x[2], x[3]),
                                            reverse=True)
        non_followed_lives_sorted = [item[0] for item in non_followed_scored_sorted]
        recommended_lives.extend(non_followed_lives_sorted)
    else:
        # 如果用户没有观看记录，则对全部非关注直播按照热度（和粉丝数）排序
        scored = []
        for live in non_followed_lives:
            heat = live.statistics.total_viewers if live.statistics else 0
            fans = fan_counts.get(live.user_id, 0)
            scored.append((live, heat, fans))
        scored_sorted = sorted(scored,
                               key=lambda x: (x[1], x[2]),
                               reverse=True)
        non_followed_lives_sorted = [item[0] for item in scored_sorted]
        recommended_lives.extend(non_followed_lives_sorted)

    # 3. 如果推荐列表为空（比如当前没有直播），则做一个兜底处理，按照热度和粉丝数排序所有直播
    if not recommended_lives:
        all_scored = []
        for live in live_list:
            heat = live.statistics.total_viewers if live.statistics else 0
            fans = fan_counts.get(live.user_id, 0)
            all_scored.append((live, heat, fans))
        all_scored_sorted = sorted(all_scored,
                                   key=lambda x: (x[1], x[2]),
                                   reverse=True)
        recommended_lives = [item[0] for item in all_scored_sorted]

    # 返回最终排序后的直播ID列表
    return [live.id for live in recommended_lives]