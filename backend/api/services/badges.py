"""生産者のバッジ判定（列では持たない）

バッジは表示のたびに producers の列から決める（年が変わってもデータを更新しなくて済む）。
返す値は badges_for() の並び順（Notion の定義順）で、当てはまるものだけ:
  - new_farmer: 新規就業。career_start_year が日本時間の今年から5年前〜今年（未設定・未来の年は対象外）
                画面の「新規就農」「新規就漁」などの出し分けはフロントが genre を見て行う
  - new_participant: 新規参加。approved_at から30日未満（未設定・未来の日時は対象外）
  - accepts_experience: 体験受け入れ中 / recruiting: 担い手募集中
注目（featured_score）はバッジにしない（スコアの上位を並べる・絞り込むのに使う）

使う場所: GET /producers・GET /producers/:producerId・GET /producers/:producerId/story（producer の項目）
"""
from datetime import timedelta

from django.utils import timezone

NEW_FARMER_YEARS = 5
NEW_PARTICIPANT_DAYS = 30


def new_farmer_years(today=None):
    """新規就業になる career_start_year の範囲 (いちばん古い年, 今年)。一覧の絞り込みにも使う"""
    year = (today or timezone.localdate()).year
    return year - NEW_FARMER_YEARS, year


def badges_for(producer, now=None):
    """生産者のバッジ（文字列のリスト）。一覧では now を1回だけ作って渡す"""
    now = now or timezone.now()
    oldest, this_year = new_farmer_years(timezone.localdate(now))
    badges = []
    if producer.career_start_year is not None and oldest <= producer.career_start_year <= this_year:
        badges.append("new_farmer")
    approved_at = producer.approved_at
    if approved_at is not None and now - timedelta(days=NEW_PARTICIPANT_DAYS) < approved_at <= now:
        badges.append("new_participant")
    if producer.accepts_experience:
        badges.append("accepts_experience")
    if producer.recruiting:
        badges.append("recruiting")
    return badges
