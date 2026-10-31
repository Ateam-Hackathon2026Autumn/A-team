import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useAtomValue } from "jotai";
import { loginStatusAtom } from "../stores/userAtom";

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

// 画面検証用の架空データです。バックエンドAPI作成後に置き換えます。
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

const pageWidth = "mx-auto max-w-[1200px] px-5 sm:px-8";
const sectionClass = "py-10 sm:py-14";
const headingClass = "text-2xl font-bold leading-relaxed sm:text-3xl";
const eyebrowClass = "mb-2 text-xs font-bold tracking-[0.18em] text-marche-green";
const badgeClass = "inline-block rounded-full bg-marche-sage px-3 py-1 text-xs text-marche-green";

const pillClass = "min-h-11 rounded-full border border-marche-line bg-white px-4 py-2 " + "text-sm text-marche-ink " + "aria-pressed:border-marche-green aria-pressed:bg-marche-green " + "aria-pressed:text-white";

const toneClasses: Record<string, string> = {
  rose: "bg-rose-100",
  gold: "bg-amber-100",
  blue: "bg-sky-100",
};

export default function HomePage() {
  const loginStatus = useAtomValue(loginStatusAtom);
  const isGuest = loginStatus === "loggedOut";
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

  const toggleFavorite = (id: number) => setFavorites((prev) => (prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]));

  return (
    <>
      <section className="relative overflow-hidden bg-marche-green text-white">
        <div className={`${pageWidth} relative grid gap-8 py-14 lg:grid-cols-2 lg:items-center lg:py-20`}>
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-white/80">FROM THE FIELD TO YOUR LIFE</p>

            <h1 className="mt-5 text-4xl font-bold leading-snug sm:text-5xl">
              つくる人と、
              <br />
              つながる暮らし。
            </h1>

            <p className="mt-6 text-sm leading-8 text-white/90">
              おいしい出会い。新しい体験。未来につながる仕事。
              <br />
              生産者と、あなたの「やってみたい」を結ぶ場所。
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <a href="#products" className="inline-flex min-h-12 items-center rounded-full bg-marche-ivory px-6 py-3 text-sm font-bold text-marche-green">
                旬の食材を探す →
              </a>
              {isGuest && (
                <Link to="/signup" className="inline-flex min-h-12 items-center rounded-full border border-white px-6 py-3 text-sm font-bold text-white">
                  はじめての方はこちら
                </Link>
              )}
            </div>
          </div>

          <div aria-hidden="true" className="flex flex-wrap items-center justify-center gap-5 rounded-[40px] bg-white/10 p-8 text-6xl sm:text-7xl">
            <span>🍅</span>
            <span>🥕</span>
            <span>🌽</span>
            <span>🍇</span>
            <span>🍃</span>
          </div>

          <p className="text-xs text-white/80 lg:col-span-2">写真・商品情報はサンプルです</p>
        </div>
      </section>

      <div className={pageWidth}>
        <section className={sectionClass}>
          <p className={eyebrowClass}>FIND YOUR WAY</p>
          <h2 className={headingClass}>つながり方を見つける</h2>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["#products", "🧺", "買う", "生産者から届く、産地の味を楽しもう"],
              ["#experiences", "🌱", "体験する", "農業・漁業の現場で、新しい発見を"],
              ["#jobs", "🤝", "働く", "地域とつながる、一日からのお仕事"],
              ["#learn", "📖", "学ぶ", "生産者のこだわりや想いを知る"],
            ].map(([href, icon, title, description]) => (
              <a key={href} href={href} className="rounded-2xl border border-marche-line bg-white p-6 transition-colors hover:bg-marche-sage">
                <span aria-hidden="true" className="text-4xl">
                  {icon}
                </span>
                <h3 className="mt-3 text-lg font-bold">{title}</h3>
                <p className="mt-2 text-sm text-marche-muted">{description}</p>
              </a>
            ))}
          </div>
        </section>

        <section id="producers" className={sectionClass}>
          <p className={eyebrowClass}>MEET THE PRODUCERS</p>
          <h2 className={headingClass}>つくる人を知る</h2>
          <p className="mt-2 text-sm text-marche-muted">サンプルの生産者をご紹介</p>

          <div role="group" aria-label="生産者の表示切り替え" className="mt-5 flex flex-wrap gap-2">
            <button type="button" aria-pressed={producerTab === "featured"} className={pillClass} onClick={() => setProducerTab("featured")}>
              注目の生産者
            </button>
            <button type="button" aria-pressed={producerTab === "newcomer"} className={pillClass} onClick={() => setProducerTab("newcomer")}>
              新規就農者
            </button>
          </div>

          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {producerSamples[producerTab].map((person) => (
              <article key={person.name} className="overflow-hidden rounded-2xl border border-marche-line bg-white">
                <div aria-hidden="true" className="grid h-44 place-items-center bg-marche-sage text-7xl">
                  {person.icon}
                </div>
                <div className="p-5">
                  <span className={badgeClass}>{person.tag}</span>
                  <h3 className="mt-3 text-lg font-bold">{person.name}</h3>
                  <p className="text-xs text-marche-muted">{person.region}</p>
                  <p className="mt-3 text-sm text-marche-muted">{person.info}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="products" className={sectionClass}>
          <p className={eyebrowClass}>FRESH FROM THE PRODUCERS</p>
          <h2 className={headingClass}>旬のおすすめ商品</h2>
          <p className="mt-2 text-sm text-marche-muted">商品ページは今後の実装予定です</p>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
            <div role="group" aria-label="商品カテゴリー" className="flex flex-wrap gap-2">
              {(["すべて", "野菜", "果物", "米", "魚介"] as Category[]).map((value) => (
                <button key={value} type="button" className={pillClass} aria-pressed={value === category} onClick={() => setCategory(value)}>
                  {value}
                </button>
              ))}
            </div>

            <label className="flex items-center gap-2 text-sm">
              並び替え
              <select value={sort} onChange={(event) => setSort(event.target.value as Sort)} className="min-h-11 rounded-lg border border-marche-line bg-white px-3">
                <option value="recommended">おすすめ順</option>
                <option value="low">価格が安い順</option>
                <option value="high">価格が高い順</option>
              </select>
            </label>
          </div>

          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {visibleProducts.map((product) => (
              <article key={product.id} className="relative overflow-hidden rounded-2xl border border-marche-line bg-white">
                <div aria-hidden="true" className={`grid h-48 place-items-center text-7xl ${toneClasses[product.tone] ?? "bg-marche-sage"}`}>
                  {product.icon}
                </div>

                <button
                  type="button"
                  aria-pressed={favorites.includes(product.id)}
                  aria-label={`${product.name}を${favorites.includes(product.id) ? "お気に入りから解除" : "お気に入りに追加"}（デモのみ）`}
                  onClick={() => toggleFavorite(product.id)}
                  className="absolute top-3 right-3 grid size-11 place-items-center rounded-full border-0 bg-white text-2xl text-marche-green shadow-sm"
                >
                  {favorites.includes(product.id) ? "♥" : "♡"}
                </button>

                <div className="p-5">
                  <span className={badgeClass}>{product.label}</span>
                  <h3 className="mt-3 text-lg font-bold">{product.name}</h3>
                  <p className="text-xs text-marche-muted">{product.producer}</p>
                  <p className="mt-3 text-xl font-bold text-marche-green">
                    ¥{product.price.toLocaleString("ja-JP")}
                    <span className="ml-2 text-xs font-normal text-marche-muted">税込・参考価格</span>
                  </p>
                </div>
              </article>
            ))}
          </div>

          <p className="mt-4 text-xs text-marche-muted">※ 商品データ・価格・お気に入りの状態は画面確認用です。 お気に入りは再読み込みで消えます。</p>
        </section>

        {[
          {
            id: "experiences",
            eyebrow: "EXPERIENCE THE LOCAL LIFE",
            title: "産地で体験する",
            items: [
              ["🍇", "収穫体験", "ぶどうの収穫を体験", "長野県 · 家族でも参加できる農園体験"],
              ["🛶", "漁業体験", "港で学ぶ、海のお仕事", "宮城県 · 地元の漁師と学ぶ一日"],
            ],
          },
          {
            id: "jobs",
            eyebrow: "WORK WITH PRODUCERS",
            title: "産地で働く",
            items: [
              ["🍎", "短期のお仕事", "りんごの収穫サポート", "青森県 · 未経験歓迎の農作業"],
              ["🌾", "季節のお手伝い", "お米の袋詰め・発送", "新潟県 · 地元で食を支えるお仕事"],
            ],
          },
        ].map(({ id, eyebrow, title, items }) => (
          <section key={id} id={id} className={sectionClass}>
            <p className={eyebrowClass}>{eyebrow}</p>
            <h2 className={headingClass}>{title}</h2>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {items.map(([icon, tag, name, description]) => (
                <article key={name} className="flex gap-4 rounded-2xl border border-marche-line bg-white p-5">
                  <span aria-hidden="true" className="text-4xl">
                    {icon}
                  </span>
                  <div>
                    <span className={badgeClass}>{tag}</span>
                    <h3 className="mt-2 text-lg font-bold">{name}</h3>
                    <p className="mt-2 text-sm text-marche-muted">{description}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}

        <section id="learn" className="my-10 grid gap-6 rounded-3xl bg-marche-sage p-6 sm:p-10 md:grid-cols-[1.5fr_1fr]">
          <div>
            <p className={eyebrowClass}>THE STORY BEHIND FOOD</p>
            <h2 className={headingClass}>
              食べものの向こうに、
              <br />
              つくる人の物語。
            </h2>
            <p className="mt-5 text-sm leading-8 text-marche-muted">どんな場所で、どんな思いで育てているのか。 産地の景色を知ると、いつもの食卓が少し豊かになる。</p>
            <a href="#producers" className="mt-5 inline-flex min-h-12 items-center rounded-full bg-marche-green px-6 py-3 text-sm font-bold text-white">
              生産者に出会う →
            </a>
          </div>
          <div aria-hidden="true" className="grid place-items-center text-8xl">
            🌿
          </div>
        </section>
        {isGuest && (
          <section aria-label="生産者の方へ" className="my-10 flex flex-wrap items-center justify-between gap-6 rounded-3xl border border-marche-line p-6 sm:p-10">
            <div>
              <p className={eyebrowClass}>FOR PRODUCERS</p>
              <h2 className={headingClass}>あなたの産地の魅力を届けませんか？</h2>
              <p className="mt-3 text-sm text-marche-muted">商品・体験・お仕事。届け方を広げる第一歩はこちらから。</p>
            </div>
            <Link to="/signup?purpose=producer" className="inline-flex min-h-12 items-center rounded-full bg-marche-green px-6 py-3 text-sm font-bold text-white">
              生産者としてはじめる →
            </Link>
          </section>
        )}
      </div>
    </>
  );
}
