"""開発用：画面の確認に使うデータをまとめて入れる

使い方:
    docker compose exec backend python manage.py seed_dev           # データを入れる
    docker compose exec backend python manage.py seed_dev --reset   # このコマンドのデータを消して入れ直す
    docker compose exec backend python manage.py seed_dev --masters-only  # マスタだけ入れる

- 開発用のアカウントやサンプルデータの投入は DEBUG=True のときだけ動く（本番 DB でのデモ投入も明示的に DEBUG=True を指定する）
- 何回実行しても増えない（開発用アカウントがもうあれば、何もしないで終わる）
- ほかのデータは消さない。--reset が消すのは、開発用アカウントとその人たちに紐づくデータだけ
- マスタ（カテゴリー・都道府県）も一緒に入れる（marche/fixtures/ の内容。もうある行はそのままにする）
- 画像は marche/seed_images/ の写真（product-01.jpg・producer-1-cover.jpg・experience-1.jpg など）を使う。
  その名前のファイルがなければ、色つきのダミー画像を作って代わりにする（保存先は開発では backend/media/）

入るデータ（パスワードは全員 DEV_PASSWORD）:
    会員     buyer1@example.com（注文・予約・応募・お気に入り・カートあり）
             buyer2@example.com（配達完了注文・レビュー・体験の予約・求人の採用あり）
             applicant@example.com（生産者申請が審査中）
    生産者   producer1@example.com 山本農園（農業・長野・公開中）
             producer2@example.com 海風水産（漁業・静岡・公開中・新規参加）
             producer3@example.com 牧ファーム（畜産・北海道・運営が掲載停止中）
             producer4@example.com 和束茶園（農業・京都・公開中）
             producer5@example.com そらべじ農園（農業・千葉・公開中）
             producer6@example.com 阿蘇ひだまり牧場（畜産・熊本・公開中）
             producer7@example.com 十勝のびのび牧場（畜産・北海道・公開中）
    商品31件（公開26件・全8カテゴリー。下書き・非公開・掲載停止・在庫切れ等も含む）
    体験8件（公開7件。buyer1 が未予約の申込可能な体験3件以上）
    求人8件（公開7件。buyer1 が勤務日を選べる未応募の求人3件以上）
    注文13件（支払い待ち・未発送・発送済み・配達完了・キャンセル申請中・返金待ち・返金済み・ゲスト・決済失敗）
    ストーリー5件（公開。全6項目入力済み）
    レビュー18件（返信あり・なし。3件以上の商品が3商品以上）
"""
import hashlib
import io
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone
from PIL import Image, ImageDraw

from api.services.pricing import tax_amounts
from api.services.reviews import recalculate_rating
from marche.models import (Address, ApplicationWorkDate, Area, CartItem, Category, Experience, ExperienceImage,
                            ExperienceSlot, FavoriteProducer, FavoriteProduct, Job, JobApplication, JobWorkDate,
                            MessageThread, Order, OrderItem, OrderShipment, Prefecture, Producer, ProducerApplication,
                            ProducerImage, ProducerStory, Product, ProductImage, ProductReview, PublishStatus, Report,
                            Reservation, ShippingSetting, User, UserConsent, WagePayment)

DEV_PASSWORD = "MarcheDev#2026"
ORDER_PREFIX = "TM-SEED-"
RESERVATION_PREFIX = "RV-SEED-"
# 確認用の写真の置き場所（Git に入れる。ファイル名は product-01.jpg・producer-1-profile.jpg・experience-1.jpg など）
SEED_IMAGE_DIR = Path(__file__).resolve().parent.parent.parent / "seed_images"
FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

# (メール, 姓, 名, 電話, 都道府県ID)
MEMBERS = [
    ("buyer1@example.com", "佐藤", "花子", "09011110001", 13),
    ("buyer2@example.com", "鈴木", "大輔", "09011110002", 27),
    ("applicant@example.com", "高橋", "美咲", "09011110003", 40),
]
PRODUCER_USERS = [
    ("producer1@example.com", "山本", "健太", "09022220001", 20),
    ("producer2@example.com", "海野", "洋平", "09022220002", 22),
    ("producer3@example.com", "牧", "草太", "09022220003", 1),
    ("producer4@example.com", "辻", "宗一郎", "09022220004", 26),
    ("producer5@example.com", "青木", "陽菜", "09022220005", 12),
    ("producer6@example.com", "黒木", "誠", "09022220006", 43),
    ("producer7@example.com", "川村", "悠", "09022220007", 1),
]
SEED_EMAILS = [row[0] for row in MEMBERS + PRODUCER_USERS]

# 商品: (生産者, 名前, カテゴリー, 内容量, 価格, 温度帯, 色, そのほかの項目)
PRODUCTS = [
    (1, "安曇野ふじ 家庭用 5kg", "果物", "5kg", 5400, "normal", (200, 60, 60),
     dict(discount_rate=10, stock=12, accepts_delivery_date=True)),
    (1, "シナノゴールド 3kg", "果物", "3kg", 3800, "normal", (225, 200, 80), dict(stock=8)),
    (1, "朝どれレタス 3玉", "野菜", "3玉", 1200, "chilled", (120, 200, 120), dict(stock=None)),
    (1, "完熟トマト 2kg", "野菜", "2kg", 2400, "chilled", (220, 70, 50), dict(stock=3)),
    (1, "季節の野菜セット", "野菜", "8〜10品", 3500, "normal", (90, 160, 90),
     dict(stock=20, is_subscription=True)),
    (1, "安曇野のコシヒカリ 5kg", "米", "5kg", 3900, "normal", (235, 225, 200), dict(stock=30, tax_rate=8)),
    (1, "りんごジュース 1L×3本", "加工品", "1L×3本", 3300, "normal", (230, 170, 60), dict(stock=0)),
    (1, "りんごのドライチップス", "加工品", "50g×3袋", 1500, "normal", (200, 140, 90), dict(discount_rate=20, stock=15)),
    (1, "新米の予約 10kg", "米", "10kg", 7200, "normal", (240, 235, 215), dict(stock=10, is_preorder=True)),
    (1, "試作中のりんごバター", "加工品", "150g", 900, "normal", (210, 150, 100),
     dict(stock=None, publish_status=PublishStatus.DRAFT, image=False)),
    (2, "沼津 あじの開き干し 10枚", "魚介類", "10枚", 3200, "chilled", (120, 160, 200), dict(stock=25)),
    (2, "金目鯛の煮付けセット", "魚介類", "2切れ×2", 4800, "frozen", (220, 90, 90), dict(discount_rate=15, stock=6)),
    (2, "釜揚げしらす 500g", "魚介類", "500g", 2600, "chilled", (235, 235, 240), dict(stock=2)),
    (2, "桜えびのかき揚げ 6枚", "加工品", "6枚", 2900, "frozen", (240, 150, 130), dict(stock=18)),
    (2, "さばのみりん干し 6枚", "魚介類", "6枚", 2200, "chilled", (150, 130, 100), dict(stock=0)),
    (2, "干物の詰め合わせ", "魚介類", "5種", 5500, "chilled", (100, 140, 180),
     dict(stock=9, accepts_delivery_date=True)),
    (2, "販売をやめた干物", "魚介類", "3枚", 1800, "chilled", (140, 140, 140),
     dict(stock=5, publish_status=PublishStatus.PRIVATE)),
    (2, "運営が掲載を止めた商品", "その他", "1個", 1000, "chilled", (170, 120, 170),
     dict(stock=5, publish_status=PublishStatus.SUSPENDED)),
    (3, "放牧牛のハンバーグ 6個", "肉", "150g×6", 4200, "frozen", (150, 90, 70), dict(stock=10)),
    (3, "手づくりソーセージ", "肉", "300g", 1900, "frozen", (190, 110, 90), dict(stock=10)),
    (4, "京都・和束の一番茶 特上煎茶", "お茶", "100g", 1800, "normal", (80, 150, 90), dict(stock=30)),
    (4, "和束の砂炒りほうじ茶 ティーバッグ", "お茶", "3g×30包", 1400, "normal", (140, 100, 60), dict(stock=25)),
    (4, "石臼挽き和束産抹茶と煎茶の贈り物セット", "お茶", "抹茶30g・煎茶80g", 4200, "normal", (80, 130, 70),
     dict(stock=15, accepts_delivery_date=True)),
    (6, "阿蘇あか牛 サーロインステーキ用", "肉", "400g", 6400, "frozen", (160, 90, 80),
     dict(stock=12, discount_rate=10, accepts_delivery_date=True)),
    (6, "阿蘇放牧牛の手ごねハンバーグ", "肉", "150g×6個", 4200, "frozen", (150, 90, 70), dict(stock=20)),
    (6, "阿蘇あか牛のハーブソーセージ", "肉", "300g", 2200, "frozen", (190, 110, 90), dict(stock=18)),
    (6, "阿蘇の平飼い有精卵「ひだまり卵」", "その他", "20個入り", 2100, "chilled", (220, 190, 120),
     dict(stock=20, is_subscription=True)),
    (6, "南阿蘇の百花蜜 非加熱はちみつ", "その他", "300g", 3400, "normal", (230, 170, 60), dict(stock=15)),
    (5, "南房総の朝摘み完熟いちご", "果物", "280g×2パック", 3200, "chilled", (210, 70, 70), dict(stock=5)),
    (7, "十勝のびのび牧場のノンホモ牛乳", "その他", "900ml×2本", 2300, "chilled", (235, 235, 220), dict(stock=18)),
    (7, "十勝の手づくりナチュラルチーズ", "加工品", "セミハード 200g", 2700, "chilled", (225, 190, 130),
     dict(stock=12)),
]


PRODUCT_TEXT = [
    ("北アルプスの寒暖差で甘みを蓄えた、歯ごたえのよいふじです。形にばらつきはありますが、家族で楽しめるたっぷり5kgをお届けします。",
     "樹上で完熟するまで葉を摘まず、草生栽培で土を育てています。収穫後は一玉ずつ傷を確かめて箱詰めします。"),
    ("黄金色の果皮に、すっきりした甘さと爽やかな酸味が詰まっています。冷やすと軽快な香りがいっそう引き立ちます。",
     "畑に草を残して土の乾燥を抑え、農薬の使用を減らしています。袋をかけず日差しを浴びせて育てます。"),
    ("朝露が残るうちに収穫した、葉の柔らかなレタスです。サラダはもちろん、さっと火を通しても甘みを楽しめます。",
     "土の水分を見ながら灌水し、必要な分だけ肥料を与えています。収穫後すぐに予冷して鮮度を保ちます。"),
    ("枝で赤く熟した実を選んで摘み取ります。果肉がしっかりしていて、切るだけで食卓が華やぎます。",
     "風通しをよくして病気を防ぎ、完熟した実だけを朝に収穫します。傷を付けないよう手作業で選別します。"),
    ("安曇野の畑から、その週に食べごろを迎えた野菜を詰め合わせます。旬ごとに中身が変わる楽しみがあります。",
     "露地と小さなハウスを使い分け、季節に合う品種を育てています。収穫当日に野菜ごとの状態を見て箱詰めします。"),
    ("北アルプスの雪解け水で育てた、粒立ちのよいコシヒカリです。炊きたてはもちろん、冷めても甘みが続きます。",
     "田に水を張る時期を見極め、稲の生育に合わせて水量を調整します。収穫後は低温で保管し、発送前に精米します。"),
    ("農園のりんごを搾った、果実本来の香りが広がるジュースです。朝食やおやつに飲みやすい1L瓶を3本お届けします。",
     "完熟果を洗浄してから低温で搾汁し、香りを損なわないよう短時間で瓶詰めしています。"),
    ("りんごの甘酸っぱさを薄いチップスに閉じ込めました。お茶のお供や、ヨーグルトのトッピングにも合います。",
     "皮付きの果実を薄切りにし、低温の温風で時間をかけて乾燥しています。砂糖は加えていません。"),
    ("安曇野の田んぼで育つ次の新米を、収穫後に精米してお届けします。秋の食卓を待つ楽しみとしてご予約ください。",
     "苗から育てて水管理を続け、実りを確認して刈り取ります。乾燥後は低温保管し、発送前に精米します。"),
    ("農園のりんごを使った試作中のスプレッドです。果実の酸味とやさしい甘みのバランスを調整しています。",
     "小鍋で果肉をゆっくり煮詰め、バターを合わせて少量ずつ仕込んでいます。"),
    ("沼津港で仕入れた真あじを手開きにした、香りのよい干物です。焼くと皮は香ばしく、身はふっくら仕上がります。",
     "水揚げ後の魚を冷やし、手開きして天日塩で下味を付けます。潮風の中で干してから冷蔵で届けます。"),
    ("ふっくらした金目鯛を甘辛い煮汁で仕上げました。湯せんで温めるだけで港町の味を楽しめます。",
     "身を切り分けてから醤油と生姜を合わせた煮汁で煮込み、急速冷凍して食感を守ります。"),
    ("やわらかな釜揚げしらすを、海の香りごと食卓へお届けします。ご飯や卵焼きにのせてお楽しみください。",
     "水揚げしたしらすをすぐに釜へ運び、塩分を抑えた湯で短時間だけ茹でます。冷却後に小分けします。"),
    ("香り高い桜えびを衣で軽くまとめたかき揚げです。温めれば、えびの甘みとサクッとした食感が戻ります。",
     "桜えびと刻んだ野菜を少量の衣で揚げ、余分な油を切って急速冷凍しています。"),
    ("脂ののったさばにみりんの甘みを重ねました。焼き目が付くころ、香ばしい香りが台所に広がります。",
     "さばを開いて骨を確認し、みりんと醤油のたれに漬けてから低温で干しています。"),
    ("沼津の干物を少しずつ食べ比べられる詰め合わせです。魚ごとの脂のりや旨みの違いを楽しめます。",
     "その日の水揚げに合わせて魚を選び、手開きと塩加減を変えながら干し上げています。"),
    ("以前販売していた干物の記録用商品です。公開を終えていますが、当時の加工内容を残しています。",
     "水揚げした魚を手開きし、塩水に漬けてから乾燥しました。"),
    ("掲載を停止した商品の確認用データです。販売ページには表示されません。",
     "素材を選別してから小分けに加工しています。"),
    ("十勝の牧草で育てた牛肉を使った、食べ応えのあるハンバーグです。焼くと肉の香りが広がります。",
     "粗挽き肉を手で成形し、急速冷凍してから出荷しています。"),
    ("肉の旨みを生かしたソーセージです。朝食や屋外の食事で温めてお楽しみください。",
     "挽き肉を練って天然の腸に詰め、低温で燻製してから冷凍しています。"),
    ("春の芽吹きに摘んだ一番茶だけを使った和束産の煎茶です。湯冷ましして淹れると、やわらかな旨みが広がります。",
     "和束町の山間茶園で新芽を育て、摘採前に短期間覆いを掛けます。収穫後は浅蒸しで香りを残します。"),
    ("一番茶の茎を使い、香ばしく焙じたティーバッグです。食後にも飲みやすい、澄んだ味わいに仕上げました。",
     "選別した茶の茎にじっくり火を入れ、焦がさないよう香りを確かめながら焙煎します。"),
    ("石臼挽きの抹茶と香りのよい煎茶を詰め合わせました。自宅での一服にも、大切な方への贈り物にも向いています。",
     "日光を遮って育てた碾茶を石臼で少量ずつ挽きます。煎茶は収穫後すぐに蒸して乾燥させます。"),
    ("阿蘇の草原で育ったあか牛のサーロインです。赤身の濃い旨みと、軽やかな脂の味わいを楽しめます。",
     "春から秋は牧野で放牧し、冬は干し草を与えて育てます。部位ごとに切り分け、急速冷凍します。"),
    ("放牧牛の粗挽き肉を使った、肉の食感が主役のハンバーグです。焼くだけで手軽に牧場の味を楽しめます。",
     "牛肉を粗く挽き、玉ねぎと塩を合わせて手で成形します。焼く前の状態で急速冷凍します。"),
    ("牛肉に香りのよいハーブを合わせたソーセージです。パリッとした食感と、やさしい燻製香が特徴です。",
     "天然羊腸に肉と自家栽培のハーブを詰め、桜のチップでじっくり燻製します。"),
    ("阿蘇の風が通る鶏舎で育った鶏の卵です。黄身のコクを、炊きたてのご飯や料理でお楽しみください。",
     "鶏が自由に歩ける平飼いの鶏舎で飼育します。毎日集卵し、殻を確認して箱詰めします。"),
    ("南阿蘇の花々から集めた百花蜜です。季節ごとに変わる香りを、パンやヨーグルトと一緒に味わえます。",
     "巣箱の中で十分に熟した蜜を採り、加熱せずに濾して瓶詰めしています。"),
    ("ヘタの際まで赤く熟してから朝に摘む、香り高いいちごです。甘みと酸味の釣り合いを楽しめます。",
     "高設ベンチで実が土に触れないよう育て、熟した実を一粒ずつ手で摘み取ります。"),
    ("十勝の牧場で搾った牛乳を、コクとやさしい口当たりを楽しめる二本組にしました。冷やしてそのまま飲むほか、朝の料理にも使えます。",
     "搾乳後すぐに冷却し、低温で加熱殺菌します。脂肪球を均質化せず、温度を管理しながら瓶詰めしています。"),
    ("十勝の生乳を使った、ほどよい弾力のあるセミハードタイプのチーズです。薄く切ってパンと合わせたり、温めて料理に添えたりできます。",
     "生乳に乳酸菌と凝乳酵素を加えて固め、型に詰めて水分を抜きます。温度と湿度を見ながら熟成させています。"),
]

# レビューは注文明細の商品の内容に合わせる。同じ商品を複数回購入した場合も文面を変える。
REVIEW_TEXT = {
    "安曇野ふじ 家庭用 5kg": ["甘みと酸味のバランスがよく、家族で食べきりました。", "歯ごたえがよく、毎朝の楽しみになっています。", "箱を開けるとりんごの香りが広がりました。"],
    "安曇野のコシヒカリ 5kg": ["炊きたての香りがよく、おにぎりにしてもおいしかったです。"],
    "りんごのドライチップス": ["薄くて食べやすく、りんごの甘酸っぱさが残っています。"],
    "朝どれレタス 3玉": ["葉がみずみずしく、サラダでたっぷりいただきました。"],
    "完熟トマト 2kg": ["赤く熟していて、切るだけで甘みを楽しめました。"],
    "沼津 あじの開き干し 10枚": ["身がふっくらして塩加減もちょうどよかったです。", "焼くと香ばしく、朝ごはんによく合いました。", "一枚ずつ使いやすく、魚の旨みを楽しめました。"],
    "釜揚げしらす 500g": ["やわらかく、ご飯にのせておいしくいただきました。"],
    "金目鯛の煮付けセット": ["湯せんで手軽に食べられ、身もふっくらしていました。"],
    "京都・和束の一番茶 特上煎茶": ["香りが爽やかで、ゆっくり淹れる時間が楽しみです。", "湯冷ましして淹れると旨みがよく分かりました。", "後味がすっきりしていて、食後にも飲みやすいです。"],
    "阿蘇あか牛 サーロインステーキ用": ["赤身の旨みが濃く、焼いても柔らかく仕上がりました。", "脂が重すぎず、肉の味をしっかり楽しめました。", "厚みがあり、家族の夕食の主役になりました。"],
}


def seed_image(names, color):
    """names の順に marche/seed_images/{名前}.jpg を探し、最初に見つかった写真を返す。なければ色つきのダミー画像"""
    for name in names:
        path = SEED_IMAGE_DIR / f"{name}.jpg"
        if path.is_file():
            return path.read_bytes()
    return dummy_image(color)


def dummy_image(color):
    """色つきのダミー画像（JPEG のバイト列）"""
    image = Image.new("RGB", (800, 600), color)
    draw = ImageDraw.Draw(image)
    light = tuple(min(255, c + 35) for c in color)
    draw.ellipse((250, 150, 550, 450), fill=light)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


class Command(BaseCommand):
    help = "画面の確認に使う開発用データ、またはマスターデータだけを入れる"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--reset", action="store_true",
                          help="このコマンドが作ったアカウントと、その人たちのデータを消してから入れ直す")
        mode.add_argument("--masters-only", action="store_true",
                          help="カテゴリー・エリア・都道府県の不足分だけを入れる")

    def handle(self, *args, **options):
        if not options["masters_only"] and not settings.DEBUG:
            raise CommandError("開発用データは DEBUG=True のときだけ投入できます。")
        self.load_masters()
        if options["masters_only"]:
            self.stdout.write(self.style.SUCCESS("マスターデータを確認し、不足分を登録しました。"))
            return

        exists = User.objects.filter(email__in=SEED_EMAILS).exists()
        if exists and not options["reset"]:
            self.stdout.write("開発用のデータはもう入っています（入れ直すときは --reset を付けてください）。")
            self.print_accounts()
            return
        with transaction.atomic():
            if exists:
                self.reset()
            self.seed()
        self.stdout.write(self.style.SUCCESS(
            f"開発用のデータを入れました：会員 {len(MEMBERS)}・生産者 {len(PRODUCER_USERS)}・"
            f"商品 {len(PRODUCTS)}・体験 {Experience.objects.filter(producer__user__email__in=SEED_EMAILS).count()}・"
            f"求人 {Job.objects.filter(producer__user__email__in=SEED_EMAILS).count()}・"
            f"注文 {Order.objects.filter(order_no__startswith=ORDER_PREFIX).count()}・"
            f"レビュー {ProductReview.objects.filter(user__email__in=SEED_EMAILS).count()}"))
        self.print_accounts()

    @transaction.atomic
    def load_masters(self):
        """カテゴリー・エリア・都道府県のマスタを入れる（marche/fixtures/ の内容）

        loaddata は ID を決めて入れるので、同じ名前の行が別の ID でもうあると失敗する。
        ここでは名前（都道府県は ID）で探し、ない行だけを足す。何回実行しても増えない。
        """
        for record in json.loads((FIXTURE_DIR / "categories.json").read_text(encoding="utf-8")):
            fields = record["fields"]
            Category.objects.get_or_create(name=fields["name"], defaults={"sort_order": fields["sort_order"]})
        areas = {}  # フィクスチャーの中のエリアID → 実際の行
        for record in json.loads((FIXTURE_DIR / "prefectures.json").read_text(encoding="utf-8")):
            fields = record["fields"]
            if record["model"] == "marche.area":
                areas[record["pk"]], _ = Area.objects.get_or_create(
                    name=fields["name"], defaults={"sort_order": fields["sort_order"]})
            else:
                Prefecture.objects.get_or_create(
                    pk=record["pk"], defaults={"name": fields["name"], "area": areas[fields["area"]]})

    def print_accounts(self):
        self.stdout.write(f"ログイン用のアカウント（パスワードは全員 {DEV_PASSWORD}）:")
        for email, last_name, first_name, *_ in MEMBERS + PRODUCER_USERS:
            self.stdout.write(f"  {email}  {last_name} {first_name}")

    # ------------------------------------------------------------------
    # 消す（--reset）
    # ------------------------------------------------------------------
    def reset(self):
        """開発用アカウントと、その人たち（会員として・生産者として）に紐づくデータだけを消す"""
        users = User.objects.filter(email__in=SEED_EMAILS)
        producers = Producer.objects.filter(user__in=users)
        image_keys = self.seed_image_keys(users)
        try:
            ProductReview.objects.filter(Q(user__in=users) | Q(product__producer__in=producers)).delete()
            orders = Order.objects.filter(
                Q(order_no__startswith=ORDER_PREFIX) | Q(user__in=users) | Q(order_shipments__producer__in=producers))
            Order.objects.filter(pk__in=orders.values("pk")).delete()
            Reservation.objects.filter(Q(user__in=users) | Q(slot__experience__producer__in=producers)).delete()
            applications = JobApplication.objects.filter(Q(user__in=users) | Q(job__producer__in=producers))
            WagePayment.objects.filter(job_application__in=applications).delete()
            applications.delete()
            MessageThread.objects.filter(Q(user__in=users) | Q(producer__in=producers)).delete()
            Report.objects.filter(reporter__in=users).delete()
            Experience.objects.filter(producer__in=producers).delete()
            Job.objects.filter(producer__in=producers).delete()
            Product.objects.filter(producer__in=producers).delete()
            producers.delete()
            UserConsent.objects.filter(user__in=users).delete()
            users.delete()
        except ProtectedError as error:
            raise CommandError(f"ほかのデータから参照されているため消せませんでした: {error}")
        for key in image_keys:
            try:
                default_storage.delete(key)
            except Exception:  # 画像が消せなくてもデータの入れ直しは続ける
                pass
        self.stdout.write("前回の開発用のデータを消しました。")

    def seed_image_keys(self, users):
        """このコマンドが作った画像（images/{ユーザーID}/seed-…）のキー"""
        keys = []
        for user in users:
            prefix = f"images/{user.id}/"
            try:
                _, files = default_storage.listdir(prefix)
            except Exception:
                continue
            keys += [prefix + name for name in files if name.startswith("seed-")]
        return keys

    # ------------------------------------------------------------------
    # 入れる
    # ------------------------------------------------------------------
    def seed(self):
        now = timezone.now()
        today = timezone.localdate()
        self.image_count = 0

        def make_user(email, last_name, first_name, phone, prefecture_id):
            return User.objects.create_user(
                email=email, password=DEV_PASSWORD, last_name=last_name, first_name=first_name, phone=phone,
                birth_date="1988-04-01", prefecture_id=prefecture_id, interests=["vegetables", "experiences"],
                email_verified_at=now)

        buyer1, buyer2, applicant = [make_user(*row) for row in MEMBERS]
        user1, user2, user3, user4, user5, user6, user7 = [make_user(*row) for row in PRODUCER_USERS]

        # ---- 生産者 ----
        producer1 = self.make_producer(
            1, user1, "山本農園", Producer.Genre.AGRICULTURE, "安曇野市", "りんご・野菜・米",
            "北アルプスのふもとで、りんごと野菜を育てています。", (90, 140, 90),
            career_start_year=2012, founded_year=1975, accepts_experience=True, recruiting=True,
            approved_at=now - timedelta(days=200), featured_score=80)
        producer2 = self.make_producer(
            2, user2, "海風水産", Producer.Genre.FISHERY, "沼津市", "干物・しらす",
            "沼津港で水揚げした魚を、その日のうちに干物にしています。", (80, 130, 180),
            career_start_year=today.year - 1, founded_year=today.year - 1, accepts_experience=True, recruiting=False,
            approved_at=now - timedelta(days=10), featured_score=60)
        producer3 = self.make_producer(
            3, user3, "牧ファーム", Producer.Genre.LIVESTOCK, "帯広市", "牛肉・加工品",
            "十勝の放牧牛を育てています。", (150, 110, 80),
            career_start_year=2005, founded_year=2005, accepts_experience=False, recruiting=False,
            approved_at=now - timedelta(days=400), publish_status=PublishStatus.SUSPENDED)
        producer4 = self.make_producer(
            4, user4, "和束茶園", Producer.Genre.AGRICULTURE, "相楽郡和束町", "和束産の煎茶・ほうじ茶・抹茶",
            "霧深い京都・和束町の山の斜面で、三代にわたり茶を育てています。一番茶の香りを食卓へお届けします。",
            (80, 140, 80), career_start_year=2016, founded_year=1952, accepts_experience=True, recruiting=True,
            approved_at=now - timedelta(days=90), featured_score=95)
        producer5 = self.make_producer(
            5, user5, "そらべじ農園", Producer.Genre.AGRICULTURE, "南房総市", "朝採れ野菜・完熟いちご",
            "温暖な南房総の太陽と潮風を受けて育つ旬の野菜といちごを、朝摘みでお届けします。",
            (120, 170, 90), career_start_year=today.year - 2, founded_year=today.year - 2,
            accepts_experience=True, recruiting=True, approved_at=now - timedelta(days=14), featured_score=75)
        producer6 = self.make_producer(
            6, user6, "阿蘇ひだまり牧場", Producer.Genre.LIVESTOCK, "阿蘇郡南阿蘇村", "あか牛・平飼い卵・百花蜜",
            "阿蘇の草原であか牛を放牧し、鶏を平飼いしています。豊かな土地の味わいをお届けします。",
            (160, 120, 80), career_start_year=today.year - 3, founded_year=2008,
            accepts_experience=False, recruiting=True, approved_at=now - timedelta(days=60), featured_score=85)
        producer7 = self.make_producer(
            7, user7, "十勝のびのび牧場", Producer.Genre.LIVESTOCK, "河東郡上士幌町", "放牧牛・乳製品",
            "十勝の広い牧草地で牛たちの歩く時間を大切にしています。牧場の毎日を食卓へつなぎます。",
            (150, 120, 90), career_start_year=today.year - 6, founded_year=today.year - 6,
            accepts_experience=False, recruiting=False, approved_at=now - timedelta(days=300), featured_score=0)
        producers = {1: producer1, 2: producer2, 3: producer3, 4: producer4, 5: producer5, 6: producer6, 7: producer7}

        settings_by_producer = {
            1: {"normal": self.shipping(producer1, "normal", 900, 8000, "2〜4日で発送"),
                "chilled": self.shipping(producer1, "chilled", 1200, None, "翌日発送")},
            2: {"chilled": self.shipping(producer2, "chilled", 1100, 10000, "注文から3日以内に発送"),
                "frozen": self.shipping(producer2, "frozen", 1300, None, "注文から5日以内に発送")},
            3: {"frozen": self.shipping(producer3, "frozen", 1500, None, "1週間以内に発送")},
            4: {"normal": self.shipping(producer4, "normal", 750, 6000, "2〜3日で発送")},
            5: {"chilled": self.shipping(producer5, "chilled", 1100, 8000, "翌日発送")},
            6: {"normal": self.shipping(producer6, "normal", 850, 7000, "3〜5日で発送"),
                "chilled": self.shipping(producer6, "chilled", 1200, None, "2〜4日で発送"),
                "frozen": self.shipping(producer6, "frozen", 1400, 10000, "3〜5日で発送")},
            7: {"chilled": self.shipping(producer7, "chilled", 1200, 6000, "2〜4日で発送")},
        }
        stories = [
            (producer1,
             "北アルプスの風と日差しを生かし、果実が樹上で熟す時間を大切にしています。毎朝畑を歩いて一玉ずつ状態を見ます。",
             "祖父の畑を継いだとき、安曇野のりんごをもっと多くの食卓に届けたいと思いました。畑の仕事を家族と続けています。",
             "葉を残したまま実を育て、下草も土づくりに使います。必要な手入れを見極めて農薬を減らしています。",
             "収穫した果実は農園で選果し、傷を確かめて箱詰めします。発送まで温度を管理して香りを守ります。",
             "北アルプスの雪解け水と昼夜の寒暖差が、果実の味を支えています。畑の周りの草花も残しています。",
             "若い人が働きに来たくなる農園を育てます。食べる人にも畑の四季を感じてほしいです。"),
            (producer2,
             "魚ごとの脂のりを見て塩加減と干し時間を変えています。焼いたときの香りとふっくらした身を大切にしています。",
             "地元の港に戻り、沼津の魚の味を届ける仕事を始めました。海と暮らす人の手仕事を次へつなぎたいです。",
             "朝の魚を冷やして鮮度を保ち、富士山の伏流水と天日塩で一枚ずつ仕込みます。魚の厚みに合わせて干し上げます。",
             "市場で仕入れ、手開き、塩漬け、乾燥、箱詰めまで加工場で行います。各工程で身の状態を確かめます。",
             "規格外の魚も加工品に活用し、食材を余さず使います。包材を減らす工夫も続けています。",
             "沼津の干物を全国の食卓へ届けます。港の魅力を体験でも伝えていきます。"),
            (producer4,
             "霧に包まれる和束の茶畑で、芽の色と柔らかさを見ながら摘み取ります。一番茶の香りを生かします。",
             "家族が守ってきた茶畑を継ぎ、産地の味を直接伝えたいと思いました。茶を淹れる時間も届けたいです。",
             "斜面の畝を整え、新芽に短期間覆いを掛けて旨みを育てます。摘んだ葉はすぐに蒸して香りを閉じ込めます。",
             "摘採から蒸し、揉み、乾燥まで状態を見ながら進めます。仕上げた茶葉は少量ずつ袋詰めします。",
             "山あいの寒暖差と朝霧が茶の生育を支えています。畑の水はけを保ち、土を流さないよう管理します。",
             "和束の茶を毎日の一杯にしてもらうことが目標です。体験を通じて手仕事も伝えます。"),
            (producer5,
             "野菜もいちごも、食べごろを見て朝に収穫します。南房総の光を受けたみずみずしさを届けます。",
             "海と畑が近いこの土地に惹かれて農業を始めました。旬を食べる楽しさを伝えたいです。",
             "風通しを整え、必要な量だけ水と肥料を与えます。いちごは実が土に触れない高設ベンチで育てます。",
             "朝に収穫し、傷を確認してから予冷します。箱を開けたときに畑の香りが残るよう丁寧に詰めます。",
             "温暖な気候と潮風を生かし、畑ごとに品種を選びます。土づくりには植物由来の堆肥を使います。",
             "近くの人にも遠くの人にも南房総の旬を届けます。農園で収穫の喜びを分かち合いたいです。"),
            (producer6,
             "牛が草原を歩き、鶏が地面をつつく時間を大切にしています。育つ環境が味に表れると考えています。",
             "阿蘇の草原を守りながら家畜を育てたいと思い、牧場に入りました。日々の世話を食卓につなぎます。",
             "季節に合わせて放牧地を移し、冬は干し草を与えます。鶏は風の通る鶏舎で平飼いしています。",
             "毎朝の健康観察から飼料づくりまで牧場で行います。肉は部位ごとに整え、温度を管理して出荷します。",
             "阿蘇の牧草地と水が家畜を支えています。草地を休ませながら使い、土が痩せないようにします。",
             "牧場の仕事を知る人を増やし、草原と暮らしを次の世代につなぎます。"),
        ]
        for producer, craft, reason, method, process, environment, goal in stories:
            ProducerStory.objects.create(producer=producer, craft=craft, reason=reason, method=method,
                                         process=process, environment=environment, goal=goal,
                                         publish_status=PublishStatus.PUBLIC)
        ProducerStory.objects.create(producer=producer3)

        # 生産者申請が審査中の会員
        pending = Producer.objects.create(
            user=applicant, business_name="高橋茶園", representative_name="高橋 美咲", genre=Producer.Genre.AGRICULTURE,
            prefecture_id=40, city="八女市", production_items="お茶", intro="八女でお茶を育てています。",
            profile_image=self.save_image(applicant, (80, 150, 80), "producer-pending-profile"),
            cover_image=self.save_image(applicant, (100, 170, 90), "producer-pending-cover"),
            approval_status=Producer.ApprovalStatus.PENDING, publish_status=PublishStatus.DRAFT)
        ProducerApplication.objects.create(producer=pending, status=ProducerApplication.Status.PENDING,
                                           application_reason="直販を始めたいため", submitted_at=now - timedelta(days=1))

        # ---- 商品 ----
        categories = {category.name: category for category in Category.objects.all()}
        products = {}
        descriptions = PRODUCT_TEXT
        for index, (owner, name, category, volume, price, zone, color, extra) in enumerate(PRODUCTS):
            description, method = descriptions[index]
            fields = dict(tax_rate=8, description=description, method=method,
                          publish_status=PublishStatus.PUBLIC, popularity_score=len(PRODUCTS) - index)
            fields.update(extra)
            with_image = fields.pop("image", True)
            product = Product.objects.create(
                producer=producers[owner], category=categories[category],
                shipping_setting=settings_by_producer[owner][zone], name=name, volume=volume, price=price, **fields)
            if with_image:
                ProductImage.objects.create(
                    product=product, sort_order=0,
                    image=self.save_image(producers[owner].user, color, f"product-{index + 1:02d}"))
            if index == 0:  # 1件目は画像を2枚にする（商品詳細の画像の切り替え）
                ProductImage.objects.create(
                    product=product, sort_order=1, image=self.save_image(user1, (230, 110, 90), "product-01b"))
            # 新着順の確認用に、登録日時を1日ずつずらす
            Product.objects.filter(pk=product.pk).update(created_at=now - timedelta(days=index))
            product.refresh_from_db()
            products[name] = product
            if index == 28:
                ProductImage.objects.create(product=product, sort_order=1,
                                            image=self.save_image(producers[owner].user, color, "product-29b"))
        apple = products["安曇野ふじ 家庭用 5kg"]
        lettuce = products["朝どれレタス 3玉"]
        tomato = products["完熟トマト 2kg"]
        rice = products["安曇野のコシヒカリ 5kg"]
        chips = products["りんごのドライチップス"]
        aji = products["沼津 あじの開き干し 10枚"]
        kinme = products["金目鯛の煮付けセット"]
        shirasu = products["釜揚げしらす 500g"]

        # ---- 購入者まわり（お届け先・カート・お気に入り） ----
        Address.objects.create(user=buyer1, recipient_name="佐藤 花子", postal_code="150-0001", prefecture_id=13,
                               city="渋谷区", address_line1="神宮前1-2-3", address_line2="マルシェハイツ101",
                               phone="09011110001", is_default=True)
        CartItem.objects.create(user=buyer1, product=apple, quantity=1)
        CartItem.objects.create(user=buyer1, product=aji, quantity=2)
        FavoriteProduct.objects.create(user=buyer1, product=apple)
        FavoriteProduct.objects.create(user=buyer1, product=kinme)
        FavoriteProducer.objects.create(user=buyer1, producer=producer2, notify=True)

        # ---- 注文13件 ----
        paid, pending_status, failed = Order.PaymentStatus.PAID, Order.PaymentStatus.PENDING, Order.PaymentStatus.FAILED
        status = OrderShipment.Status
        self.order_count = 0
        self.make_order(buyer1, pending_status, 0, [(producer1, "normal", status.UNSHIPPED, [(apple, 1)], {})],
                        ordered_at=now - timedelta(minutes=5))
        self.make_order(buyer1, paid, 1, [(producer1, "normal", status.UNSHIPPED, [(rice, 1), (chips, 2)], {})])
        order3 = self.make_order(buyer1, paid, 4, [
            (producer1, "normal", status.SHIPPED, [(apple, 1)],
             dict(shipped_at=now - timedelta(days=2), tracking_no="1234-5678-9012")),
            (producer1, "chilled", status.SHIPPED, [(tomato, 1)], dict(shipped_at=now - timedelta(days=2))),
            (producer2, "chilled", status.UNSHIPPED, [(aji, 1)], {}),
        ])
        order4 = self.make_order(buyer1, paid, 45, [
            (producer1, "normal", status.DELIVERED, [(apple, 2), (rice, 1), (chips, 1)],
             dict(shipped_at=now - timedelta(days=43), tracking_no="1111-2222-3333")),
            (producer1, "chilled", status.DELIVERED, [(lettuce, 1)], dict(shipped_at=now - timedelta(days=43))),
        ])
        order5 = self.make_order(buyer1, paid, 20, [
            (producer2, "chilled", status.DELIVERED, [(aji, 1), (shirasu, 1)],
             dict(shipped_at=now - timedelta(days=18))),
            (producer2, "frozen", status.DELIVERED, [(kinme, 1)], dict(shipped_at=now - timedelta(days=18))),
            (producer1, "normal", status.DELIVERED, [(apple, 1)], dict(shipped_at=now - timedelta(days=18))),
        ])
        self.make_order(buyer1, paid, 2, [
            (producer1, "normal", status.CANCEL_REQUESTED, [(chips, 3)], dict(cancel_reason="間違えて注文しました。"))])
        self.make_order(buyer1, paid, 6, [
            (producer2, "chilled", status.CANCELED, [(shirasu, 2)],
             dict(cancel_reason="日程が合わなくなりました。", canceled_at=now - timedelta(days=5)))],
            payment_method="konbini")  # コンビニ払いなので返金待ち（運営が返金する）
        self.make_order(buyer1, paid, 30, [
            (producer1, "normal", status.CANCELED, [(rice, 1)],
             dict(cancel_reason="住所を間違えました。", canceled_at=now - timedelta(days=29), refunded=True))])
        self.make_order(None, paid, 1, [(producer1, "normal", status.UNSHIPPED, [(apple, 1)], {})])
        self.make_order(buyer1, failed, 8, [(producer2, "frozen", status.UNSHIPPED, [(kinme, 1)], {})])

        # buyer2 の配達完了注文。魚・茶・肉にも評価順で並べられるレビューを用意する
        tea = products["京都・和束の一番茶 特上煎茶"]
        beef = products["阿蘇あか牛 サーロインステーキ用"]
        review_orders = []
        buyer2_delivery = dict(ship_name="鈴木 大輔", ship_postal_code="530-0001", ship_prefecture="大阪府",
                               ship_city="大阪市北区", ship_address_line1="梅田1-2-3", ship_phone=buyer2.phone)
        for days_ago in (36, 25):
            review_orders.append(self.make_order(buyer2, paid, days_ago, [
                (producer2, "chilled", status.DELIVERED, [(aji, 1)], dict(shipped_at=now - timedelta(days=days_ago - 2))),
                (producer4, "normal", status.DELIVERED, [(tea, 1)], dict(shipped_at=now - timedelta(days=days_ago - 2))),
                (producer6, "frozen", status.DELIVERED, [(beef, 1)], dict(shipped_at=now - timedelta(days=days_ago - 2))),
            ], ship_to=buyer2_delivery))
        review_orders.append(self.make_order(buyer2, paid, 12, [
            (producer4, "normal", status.DELIVERED, [(tea, 1)], dict(shipped_at=now - timedelta(days=10))),
            (producer6, "frozen", status.DELIVERED, [(beef, 1)], dict(shipped_at=now - timedelta(days=10))),
        ], ship_to=buyer2_delivery))

        # ---- レビュー18件（発送済み・配達完了の明細に1件ずつ） ----
        items = OrderItem.objects.filter(
            shipment__order__in=[order3, order4, order5, *review_orders],
            shipment__status__in=[status.SHIPPED, status.DELIVERED]).select_related("product", "shipment__order")
        review_counts = {}
        for index, item in enumerate(items.order_by("id")):
            replied = index % 3 == 0
            review_number = review_counts.get(item.product.name, 0)
            review_counts[item.product.name] = review_number + 1
            ProductReview.objects.create(
                order_item=item, product=item.product, user=item.shipment.order.user,
                rating=4 if review_number % 3 == 1 else 5,
                body=REVIEW_TEXT[item.product.name][review_number % len(REVIEW_TEXT[item.product.name])],
                reply="ありがとうございます。またのご利用をお待ちしています。" if replied else None,
                replied_at=now if replied else None)
        for product_id in set(items.values_list("product_id", flat=True)):
            recalculate_rating(product_id)

        # ---- 体験8件 ----
        def make_experience(number, producer, title, color, publish=PublishStatus.PUBLIC, **extra):
            fields = dict(
                description=f"{title}です。初めての方も歓迎します。", place=f"{producer.business_name}（{producer.city}）",
                price_adult=3000, price_child=1500, age_condition="3歳以上", family_ok=True, beginner_ok=True,
                flow=[{"time": "10:00", "text": "集合・説明"}, {"time": "10:30", "text": "体験"},
                      {"time": "12:00", "text": "解散"}],
                belongings=["汚れてもよい服装", "飲み物"], notes=["雨天の場合は内容を変更することがあります。"],
                cancel_policy="開催の24時間前までキャンセルできます。", booking_deadline_hours=24,
                prefecture=producer.prefecture, publish_status=publish)
            fields.update(extra)
            experience = Experience.objects.create(producer=producer, title=title, **fields)
            ExperienceImage.objects.create(experience=experience, sort_order=0,
                                           image=self.save_image(producer.user, color, f"experience-{number}"))
            return experience

        def make_slot(experience, start_at, capacity=10):
            return ExperienceSlot.objects.create(experience=experience, start_at=start_at, duration_min=120,
                                                 capacity=capacity, reserved_count=0)

        def local_at(days, hour=10):
            """投入日からの相対日付を、日本時間の自然な開始時刻にそろえる"""
            day = today + timedelta(days=days)
            return datetime.combine(day, time(hour), tzinfo=ZoneInfo("Asia/Tokyo"))

        self.reservation_count = 0
        harvest = make_experience(1, producer1, "安曇野りんごの選果とジュースづくり体験", (230, 90, 80))
        past = make_slot(harvest, local_at(-14))
        open_slot = make_slot(harvest, local_at(7))
        make_slot(harvest, local_at(14))
        self.reserve(past, buyer1, 2, 1, Reservation.Status.ATTENDED)
        self.reserve(open_slot, buyer1, 2, 1)
        full = make_experience(2, producer1, "高原野菜の畑の冬支度体験", (110, 170, 100))
        self.reserve(make_slot(full, local_at(30), capacity=4), buyer2, 3, 1)
        closed = make_experience(3, producer2, "沼津港・伝統の天日干し干物づくり体験", (110, 150, 200), price_child=None,
                                 family_ok=False, age_condition="中学生以上")
        # 当日 13 時が過ぎていれば翌日 10 時。どちらも開始前で申込期限は過ぎている。
        closed_start = local_at(0, 13)
        if closed_start <= now:
            closed_start = local_at(1)
        make_slot(closed, closed_start)
        make_experience(4, producer2, "沼津港の競り見学と朝市めぐりツアー", (90, 120, 160))
        make_experience(5, producer1, "下書きの体験", (180, 180, 180), publish=PublishStatus.DRAFT)
        tea_experience = make_experience(
            6, producer4, "和束の茶畑散策とほうじ茶焙煎体験", (90, 160, 90),
            price_adult=3800, price_child=1900,
            description="冬の茶畑を歩いて栽培の工夫を聞き、茶葉を焙じてほうじ茶を作ります。出来たての香りをその場で味わえます。")
        tea_slot = make_slot(tea_experience, local_at(10))
        self.reserve(tea_slot, buyer2, 2, 0)
        make_slot(tea_experience, local_at(24))
        fish_experience = make_experience(
            7, producer2, "漁師に教わる駿河湾の魚さばきと漁師飯教室", (90, 140, 180),
            price_adult=4500, price_child=2500,
            description="沼津の魚を自分でさばき、漁師飯を作ります。魚の選び方から食べ方まで教わる港の一日です。")
        make_slot(fish_experience, local_at(8), capacity=8)
        make_slot(fish_experience, local_at(22), capacity=8)
        berry_experience = make_experience(
            8, producer5, "南房総の旬野菜と完熟いちご収穫・農園ランチ体験", (180, 110, 90),
            price_adult=3200, price_child=1600,
            description="旬の野菜と完熟いちごを自分の手で収穫します。畑の恵みを使った農園ランチも楽しめます。")
        make_slot(berry_experience, local_at(6), capacity=12)
        make_slot(berry_experience, local_at(20), capacity=12)

        # ---- 求人8件（公開の7件はカバー写真 job-1〜7、下書きは画像なし）----
        def make_job(producer, title, publish=PublishStatus.PUBLIC, photo=None, **extra):
            fields = dict(
                term_type=Job.TermType.SHORT, pay_unit=Job.PayUnit.DAILY, pay_amount=10000, work_hours="8:00〜15:00",
                work_place=f"{producer.business_name}（{producer.city}）", slots=3,
                description=f"{title}を募集しています。", requirements=["18歳以上の方"],
                belongings=["汚れてもよい服装", "長靴"], notes=["昼食は各自でご用意ください。"],
                inexperienced_ok=True, prefecture=producer.prefecture, publish_status=publish)
            fields.update(extra)
            if photo is not None:
                fields["cover_image"] = self.save_image(producer.user, (150, 170, 120), f"job-{photo}")
            return Job.objects.create(producer=producer, title=title, **fields)

        def work_date(job, days, needed_count=2):
            return JobWorkDate.objects.create(job=job, work_date=today + timedelta(days=days),
                                              needed_count=needed_count)

        def apply(job, user, application_status, work_dates=()):
            decided = application_status in (JobApplication.Status.HIRED, JobApplication.Status.REJECTED)
            application = JobApplication.objects.create(
                job=job, user=user, status=application_status, message="よろしくお願いします。", answers=[],
                decided_at=now if decided else None)
            for date in work_dates:
                ApplicationWorkDate.objects.create(application=application, work_date=date)

        picking = make_job(producer1, "安曇野りんごの選果・箱詰めスタッフ", photo=1, period_start=today - timedelta(days=7),
                           period_end=today + timedelta(days=30))
        day1, day2 = work_date(picking, 7), work_date(picking, 8)
        work_date(picking, 14)
        apply(picking, buyer1, JobApplication.Status.APPLIED, [day1, day2])
        apply(picking, buyer2, JobApplication.Status.HIRED, [day1])
        ended = make_job(producer1, "春の田植え・苗運びサポート", photo=2, term_type=Job.TermType.ONE_DAY,
                         period_start=today - timedelta(days=30), period_end=today - timedelta(days=1))
        work_date(ended, -3)
        filled = make_job(producer2, "沼津ひものの箱詰め・発送準備スタッフ", photo=3, slots=1,
                          pay_unit=Job.PayUnit.HOURLY, pay_amount=1200)
        filled_day = work_date(filled, 5)
        apply(filled, applicant, JobApplication.Status.HIRED, [filled_day])
        make_job(producer2, "水産加工の正社員（長期）", photo=4, term_type=Job.TermType.LONG,
                 pay_unit=Job.PayUnit.MONTHLY, pay_amount=230000, work_hours="6:00〜15:00（休憩1時間）", slots=2,
                 inexperienced_ok=False)
        make_job(producer1, "下書きの求人", publish=PublishStatus.DRAFT)
        tea_job = make_job(
            producer4, "和束の茶葉選別・袋詰めスタッフ", photo=5, term_type=Job.TermType.ONE_DAY,
            pay_unit=Job.PayUnit.HOURLY, pay_amount=1450, work_hours="8:30〜16:30（休憩1時間）", slots=4,
            period_start=today - timedelta(days=3), period_end=today + timedelta(days=35),
            description="製茶場で茶葉を選別し、袋詰めと出荷準備を手伝う一日のお仕事です。初めての方には道具の使い方から教えます。")
        work_date(tea_job, 9, 3)
        work_date(tea_job, 16, 3)
        berry_job = make_job(
            producer5, "朝どれ野菜・完熟いちごの収穫とパック詰めスタッフ", photo=6,
            pay_unit=Job.PayUnit.DAILY, pay_amount=9500, work_hours="7:30〜14:30", slots=3,
            period_start=today - timedelta(days=5), period_end=today + timedelta(days=40),
            description="南房総の畑で収穫し、いちごを傷めないようパックに詰めます。朝の短い時間から参加できます。")
        for days in (6, 13, 20):
            work_date(berry_job, days)
        ranch_job = make_job(
            producer6, "阿蘇の放牧牛・平飼い鶏の飼育サポート", photo=7,
            pay_unit=Job.PayUnit.HOURLY, pay_amount=1400, work_hours="7:00〜12:00", slots=2,
            period_start=today - timedelta(days=5), period_end=today + timedelta(days=45),
            description="牧草地への移動と鶏舎の世話を手伝う仕事です。動物との接し方はスタッフが一緒に説明します。")
        work_date(ranch_job, 11)
        work_date(ranch_job, 18)

    # ------------------------------------------------------------------
    # 部品
    # ------------------------------------------------------------------
    def save_image(self, user, color, *names):
        """写真（なければダミー画像）を images/{ユーザーID}/seed-NNN.jpg に保存し、キーを返す

        本人が画像キーとして送り直せる場所に置く。names は marche/seed_images/ のファイル名（拡張子なし）の候補。
        """
        self.image_count += 1
        return default_storage.save(f"images/{user.id}/seed-{self.image_count:03d}.jpg",
                                    ContentFile(seed_image(names, color)))

    def make_producer(self, number, user, business_name, genre, city, production_items, intro, color, **extra):
        fields = dict(approval_status=Producer.ApprovalStatus.APPROVED, publish_status=PublishStatus.PUBLIC)
        fields.update(extra)
        producer = Producer.objects.create(
            user=user, business_name=business_name, representative_name=f"{user.last_name} {user.first_name}",
            genre=genre, prefecture_id=user.prefecture_id, city=city, production_items=production_items, intro=intro,
            profile_image=self.save_image(user, color, f"producer-{number}-profile"),
            cover_image=self.save_image(user, tuple(min(255, c + 50) for c in color), f"producer-{number}-cover"),
            **fields)
        # 農園の写真は、専用の写真（producer-N-farm）がなければカバーと同じものを使う
        ProducerImage.objects.create(
            producer=producer, sort_order=0,
            image=self.save_image(user, tuple(max(0, c - 30) for c in color), f"producer-{number}-farm",
                                  f"producer-{number}-cover"))
        ProducerApplication.objects.create(
            producer=producer, status=ProducerApplication.Status.APPROVED, application_reason="直販を始めたいため",
            submitted_at=fields["approved_at"] - timedelta(days=2), reviewed_at=fields["approved_at"])
        return producer

    def shipping(self, producer, zone, fee, threshold, lead_time):
        return ShippingSetting.objects.create(producer=producer, temperature_zone=zone, shipping_fee=fee,
                                              free_shipping_threshold=threshold, lead_time_text=lead_time)

    def make_order(self, user, payment_status, days_ago, boxes, payment_method="card", ordered_at=None, ship_to=None):
        """注文・箱・明細を作る。boxes は (生産者, 温度帯, 箱の状態, [(商品, 数量)], 箱のそのほかの項目) の並び

        金額は注文APIと同じ数え方（明細は割引後の価格、送料は箱ごと、送料無料ライン以上なら0円）。
        user が None ならゲストの注文。ship_to はデモ購入者ごとの配送先。
        """
        self.order_count += 1
        number = self.order_count
        fields = dict(
            order_no=f"{ORDER_PREFIX}{number:04d}", user=user, payment_status=payment_status,
            payment_method=payment_method, access_token_hash=hashlib.sha256(f"seed-{number}".encode()).hexdigest(),
            ship_name="佐藤 花子", ship_postal_code="150-0001", ship_prefecture="東京都", ship_city="渋谷区",
            ship_address_line1="神宮前1-2-3", ship_phone="09011110001", items_total=0, shipping_total=0,
            grand_total=0, tax_8_amount=0, tax_10_amount=0,
            ordered_at=ordered_at or timezone.now() - timedelta(days=days_ago))
        if user is None:
            fields.update(guest_email="guest@example.com", guest_name="田中 一郎", guest_phone="09033330001",
                          ship_name="田中 一郎")
        if ship_to is not None:
            fields.update(ship_to)
        order = Order.objects.create(**fields)
        items_total = shipping_total = 0
        tax_lines = []
        for producer, zone, shipment_status, lines, extra in boxes:
            extra = dict(extra)
            refunded = extra.pop("refunded", False)
            setting = producer.shipping_settings.get(temperature_zone=zone)
            box_total = sum(product.sale_price * quantity for product, quantity in lines)
            free = setting.free_shipping_threshold is not None and box_total >= setting.free_shipping_threshold
            fee = 0 if free else setting.shipping_fee
            shipment = OrderShipment.objects.create(order=order, producer=producer, temperature_zone=zone,
                                                    shipping_fee=fee, status=shipment_status, **extra)
            if refunded:
                shipment.refunded_amount = box_total + fee
                shipment.save(update_fields=["refunded_amount"])
            for product, quantity in lines:
                subtotal = product.sale_price * quantity
                OrderItem.objects.create(
                    shipment=shipment, product=product, product_name=product.name, unit_price=product.price,
                    discount_rate=product.discount_rate, paid_unit_price=product.sale_price, quantity=quantity,
                    tax_rate=product.tax_rate, subtotal=subtotal)
                tax_lines.append((product.tax_rate, subtotal))
            items_total += box_total
            shipping_total += fee
        order.items_total, order.shipping_total = items_total, shipping_total
        order.grand_total = items_total + shipping_total
        order.tax_8_amount, order.tax_10_amount = tax_amounts(tax_lines, shipping_total)
        order.save(update_fields=["items_total", "shipping_total", "grand_total", "tax_8_amount", "tax_10_amount"])
        return order

    def reserve(self, slot, user, adult_count, child_count, status=Reservation.Status.CONFIRMED):
        """予約を作り、日程の予約人数も増やす"""
        self.reservation_count += 1
        experience = slot.experience
        total = experience.price_adult * adult_count + (experience.price_child or 0) * child_count
        Reservation.objects.create(
            reservation_no=f"{RESERVATION_PREFIX}{self.reservation_count:04d}", slot=slot, user=user,
            adult_count=adult_count, child_count=child_count, infant_count=0,
            representative_name=f"{user.last_name} {user.first_name}", phone=user.phone, total_amount=total,
            status=status, policy_agreed_at=timezone.now())
        slot.reserved_count += adult_count + child_count
        slot.save(update_fields=["reserved_count"])
