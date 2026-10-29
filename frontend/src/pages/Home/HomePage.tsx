import { useMemo, useState } from "react";
import { Link } from "react-router";
import "./HomePage.css";

type ProducerTab = "featured" | "newcomer";
type Category = "すべて" | "野菜" | "果物" | "米" | "魚介";
type Sort = "recommended" | "low" | "high";

type Product = {
  id: number;
  name: string;
  producer: string;
  category: Exclude<Category, "すべて">;
  price: number;
  icon: string;
  tone: string;
  label: string;
};

// 画面検証用の架空データです。担当BのAPI作成後に置き換えます。
const products: Product[] = [
  { id: 1, name: "朝採れ完熟トマト", producer: "みどり農園 / 千葉県", category: "野菜", price: 1280, icon: "🍅", tone: "rose", label: "旬の野菜" },
  { id: 2, name: "季節のりんごセット", producer: "山あい果樹園 / 長野県", category: "果物", price: 2380, icon: "🍎", tone: "gold", label: "産地直送" },
  { id: 3, name: "新米こしひかり 2kg", producer: "たんぼの家 / 新潟県", category: "米", price: 1980, icon: "🌾", tone: "", label: "新米" },
  { id: 4, name: "水揚げ直送のお魚セット", producer: "青い港水産 / 宮城県", category: "魚介", price: 3200, icon: "🐟", tone: "blue", label: "漁師直送" },
  { id: 5, name: "カラフルにんじん", producer: "陽だまり農場 / 北海道", category: "野菜", price: 950, icon: "🥕", tone: "gold", label: "新規就農者" },
  { id: 6, name: "もぎたてみかん 3kg", producer: "海風みかん園 / 愛媛県", category: "果物", price: 2480, icon: "🍊", tone: "rose", label: "農家直送" },
];
const producerSamples = {
  featured: [
    { icon: "🍓", name: "いちごの丘農園", region: "栃木県", info: "春のいちごを大切に育てています", tag: "体験受付中" },
    { icon: "🌽", name: "おひさまファーム", region: "北海道", info: "自然の恵みを、畑からまっすぐ", tag: "担い手募集中" },
    { icon: "🐟", name: "なぎさ水産", region: "宮城県", info: "海の暮らしと旬のおいしさをお届け", tag: "漁業体験" },
  ],
  newcomer: [
    { icon: "🥬", name: "はじまり農園", region: "千葉県", info: "就農2年目。小さな畑から一歩ずつ", tag: "新規就農者" },
    { icon: "🍊", name: "わかば果樹園", region: "愛媛県", info: "地域の果樹を次の世代へ", tag: "新規就農者" },
    { icon: "🌻", name: "みらい畑", region: "長野県", info: "食べることから農業を身近に", tag: "新規就農者" },
  ],
};

export default function HomePage() {
  const [producerTab, setProducerTab] = useState<ProducerTab>("featured");
  const [category, setCategory] = useState<Category>("すべて");
  const [sort, setSort] = useState<Sort>("recommended");
  const [favorites, setFavorites] = useState<number[]>([]);

  const visibleProducts = useMemo(() => {
    const filtered = products.filter((product) => category === "すべて" || product.category === category);
    if (sort === "low") return [...filtered].sort((a, b) => a.price - b.price);
    if (sort === "high") return [...filtered].sort((a, b) => b.price - a.price);
    return filtered;
  }, [category, sort]);

  const toggleFavorite = (id: number) => setFavorites((prev) =>
    prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id],
  );

  return (
    <>
      <section className="hero" aria-labelledby="home-hero-heading">
        <div className="hero-art" aria-hidden="true">
          <div className="produce-scene"><span>🍅</span><span>🥕</span><span>🌽</span><span>🍇</span><span>🍃</span></div>
        </div>
        <div className="wrap">
          <p className="eyebrow">FROM THE FIELD TO YOUR LIFE</p>
          <h1 id="home-hero-heading">つくる人と、<br />つながる暮らし。</h1>
          <p>おいしい出会い。新しい体験。未来につながる仕事。<br />生産者と、あなたの「やってみたい」を結ぶ場所。</p>
          <div className="row">
            <a className="btn light" href="#products">旬の食材を探す →</a>
            <Link className="btn outline hero-signup" to="/signup">はじめての方はこちら</Link>
          </div>
        </div>
        <span className="hero-note">写真・商品情報はサンプルです</span>
      </section>

      <div className="wrap">
        <section className="section" aria-labelledby="home-section-guide">
          <div className="section-head"><div><p className="eyebrow">FIND YOUR WAY</p><h2 id="home-section-guide">つながり方を見つける</h2></div></div>
          <div className="four">
            {[
              { href: "#products", icon: "🧺", name: "買う", description: "生産者から届く、産地の味を楽しもう", color: "野菜・果物・魚介など" },
              { href: "#experiences", icon: "🌱", name: "体験する", description: "農業・漁業の現場で、新しい発見を", color: "収穫・ものづくり" },
              { href: "#jobs", icon: "🤝", name: "働く", description: "地域とつながる、一日からのお仕事", color: "短期・お手伝い" },
              { href: "#learn", icon: "📖", name: "学ぶ", description: "生産者のこだわりや想いを知る", color: "産地のストーリー" },
            ].map(({ href, icon, name, description, color }) =>
              <a className="entry" href={href} key={name}><span className="icon" aria-hidden="true">{icon}</span><h3>{name}</h3><p>{description}</p><b>{color} →</b></a>,
            )}
          </div>
        </section>

        <section className="section" id="producers" aria-labelledby="home-section-producers">
          <div className="section-head"><div><p className="eyebrow">MEET THE PRODUCERS</p><h2 id="home-section-producers">つくる人を知る</h2></div><span className="muted">サンプルの生産者をご紹介</span></div>
          <div className="tabs" role="tablist" aria-label="生産者の表示切り替え">
            <button className="tab" type="button" role="tab" aria-selected={producerTab === "featured"} onClick={() => setProducerTab("featured")}>注目の生産者</button>
            <button className="tab" type="button" role="tab" aria-selected={producerTab === "newcomer"} onClick={() => setProducerTab("newcomer")}>新規就農者</button>
          </div>
          <div className="home-producer-grid" role="tabpanel">
            {producerSamples[producerTab].map((person) =>
              <article className="card" key={person.name}><div className="visual producer-visual" aria-hidden="true">{person.icon}</div><div className="card-body"><span className="badge">{person.tag}</span><h3>{person.name}</h3><small>{person.region}</small><p className="home-card-description">{person.info}</p></div></article>,
            )}
          </div>
        </section>

        <section className="section" id="products" aria-labelledby="home-section-products">
          <div className="section-head"><div><p className="eyebrow">FRESH FROM THE PRODUCERS</p><h2 id="home-section-products">旬のおすすめ商品</h2></div><span className="muted">商品ページは今後の実装予定です</span></div>
          <div className="home-product-controls">
            <div className="home-category-pills" role="group" aria-label="商品カテゴリー">
              {(["すべて", "野菜", "果物", "米", "魚介"] as Category[]).map((value) =>
                <button key={value} type="button" className="tab" aria-pressed={value === category} onClick={() => setCategory(value)}>{value}</button>,
              )}
            </div>
            <label className="home-sort">並び替え <select value={sort} onChange={(event) => setSort(event.target.value as Sort)}><option value="recommended">おすすめ順</option><option value="low">価格が安い順</option><option value="high">価格が高い順</option></select></label>
          </div>
          <div className="home-product-grid">
            {visibleProducts.map((product) =>
              <article className="card" key={product.id}>
                <div className={`visual ${product.tone}`} aria-hidden="true">{product.icon}</div>
                <button className="heart" type="button" aria-pressed={favorites.includes(product.id)} aria-label={`${product.name}を${favorites.includes(product.id) ? "お気に入りから解除" : "お気に入りに追加"}（デモのみ）`} onClick={() => toggleFavorite(product.id)}>{favorites.includes(product.id) ? "♥" : "♡"}</button>
                <div className="card-body"><span className="badge">{product.label}</span><h3>{product.name}</h3><small>{product.producer}</small><p className="price">¥{product.price.toLocaleString("ja-JP")} <small>税込・参考価格</small></p></div>
              </article>,
            )}
          </div>
          <p className="home-disclaimer muted">※ 商品データ・価格・お気に入りの状態は画面確認用です。お気に入りは再読み込みで消えます。</p>
        </section>

        <section className="section" id="experiences" aria-labelledby="home-section-experiences">
          <div className="section-head"><div><p className="eyebrow">EXPERIENCE THE LOCAL LIFE</p><h2 id="home-section-experiences">産地で体験する</h2></div></div>
          <div className="two">
            <article className="mini"><span className="icon" aria-hidden="true">🍇</span><div><span className="badge">収穫体験</span><h3>ぶどうの収穫を体験</h3><p className="muted">長野県 · 家族でも参加できる農園体験</p></div></article>
            <article className="mini"><span className="icon" aria-hidden="true">🛶</span><div><span className="badge">漁業体験</span><h3>港で学ぶ、海のお仕事</h3><p className="muted">宮城県 · 地元の漁師と学ぶ一日</p></div></article>
          </div>
        </section>

        <section className="section" id="jobs" aria-labelledby="home-section-jobs">
          <div className="section-head"><div><p className="eyebrow">WORK WITH PRODUCERS</p><h2 id="home-section-jobs">産地で働く</h2></div></div>
          <div className="two">
            <article className="mini"><span className="icon" aria-hidden="true">🍎</span><div><span className="badge">短期のお仕事</span><h3>りんごの収穫サポート</h3><p className="muted">青森県 · 未経験歓迎の農作業</p></div></article>
            <article className="mini"><span className="icon" aria-hidden="true">🌾</span><div><span className="badge">季節のお手伝い</span><h3>お米の袋詰め・発送</h3><p className="muted">新潟県 · 地元で食を支えるお仕事</p></div></article>
          </div>
        </section>

        <section className="story" id="learn" aria-labelledby="home-section-learn">
          <div><p className="eyebrow">THE STORY BEHIND FOOD</p><h2 id="home-section-learn">食べものの向こうに、<br />つくる人の物語。</h2><p>どんな場所で、どんな思いで育てているのか。産地の景色を知ると、いつもの食卓が少し豊かになる。</p><a className="btn" href="#producers">生産者に出会う →</a></div>
          <div className="story-art" aria-hidden="true">🌿</div>
        </section>

        <section className="home-producer-callout" aria-label="生産者の方へ">
          <div><p className="eyebrow">FOR PRODUCERS</p><h2>あなたの産地の魅力を届けませんか？</h2><p>商品・体験・お仕事。届け方を広げる第一歩はこちらから。</p></div>
          <Link className="btn" to="/signup?purpose=producer">生産者としてはじめる →</Link>
        </section>
      </div>
    </>
  );
}
