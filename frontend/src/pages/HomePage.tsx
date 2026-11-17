import { useCallback, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useAtomValue } from "jotai";
import { loginStatusAtom } from "../stores/userAtom";
import { getCategories, getProducts } from "../api/productApi";
import { getProducers } from "../api/producerApi";
import { getExperiences } from "../api/experienceApi";
import { getJobs } from "../api/jobApi";
import { getStories } from "../api/storyApi";
import { usePublicContent } from "../hooks/usePublicContent";
import { USE_MOCK } from "../config/env";
import ProductCard from "../components/products/ProductCard";
import ExperienceCard from "../components/experiences/ExperienceCard";
import JobCard from "../components/jobs/JobCard";
import { ContentImage, ContentStatus, fieldClass, linkClass, textLinkClass } from "../components/ui/ContentPage";
import type { ProductSort } from "../types/publicProduct";

const pageWidth = "mx-auto max-w-[1200px] px-5 sm:px-8";
const gridClass = "mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3";
const pillClass = "min-h-11 cursor-pointer rounded-full border border-marche-line bg-white px-4 py-2 font-sans text-sm text-marche-ink aria-pressed:border-marche-green aria-pressed:bg-marche-green aria-pressed:text-white";

export default function HomePage() {
  const isGuest = useAtomValue(loginStatusAtom) === "loggedOut";
  return <>
    <section className="overflow-hidden bg-marche-green text-white">
      <div className={`${pageWidth} grid gap-8 py-14 lg:grid-cols-2 lg:items-center lg:py-20`}>
        <div><p className="m-0 text-xs font-bold tracking-[0.18em] text-white/80">FROM THE FIELD TO YOUR LIFE</p>
          <h1 className="mb-0 mt-5 font-serif text-4xl font-bold leading-snug sm:text-5xl">つくる人と、<br />つながる暮らし。</h1>
          <p className="mb-0 mt-6 text-sm leading-8 text-white/90">おいしい出会い。新しい体験。未来につながる仕事。<br />生産者と、あなたの「やってみたい」を結ぶ場所。</p>
          <div className="mt-7 flex flex-wrap gap-3"><Link to="/products" className="inline-flex min-h-12 items-center rounded-full bg-marche-ivory px-6 py-3 text-sm font-bold text-marche-green no-underline">旬の食材を探す →</Link><Link to="/experiences" className="inline-flex min-h-12 items-center rounded-full border border-white px-6 py-3 text-sm font-bold text-white no-underline">体験を探す →</Link>{isGuest && <Link to="/signup" className="inline-flex min-h-12 items-center px-3 text-sm font-bold text-white">はじめての方はこちら</Link>}</div>
        </div>
        <div aria-hidden="true" className="flex flex-wrap items-center justify-center gap-5 rounded-[40px] bg-white/10 p-8 text-6xl sm:text-7xl"><span>🍅</span><span>🥕</span><span>🌽</span><span>🍇</span><span>🍃</span></div>
      </div>
    </section>
    <div className={pageWidth}>
      {USE_MOCK && <p className="mt-6 rounded-xl bg-marche-sage px-4 py-3 text-sm text-marche-muted">デモ表示：掲載情報は開発用モックです。実際の予約・応募・決済は行いません。</p>}
      <section className="py-10 sm:py-14"><p className="text-xs font-bold tracking-[0.18em] text-marche-green">FIND YOUR WAY</p><h2 className="font-serif text-2xl sm:text-3xl">つながり方を見つける</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[
          ["/products", "🧺", "買う", "生産者から届く、産地の味を楽しもう"],
          ["/experiences", "🌱", "体験する", "農業・漁業の現場で、新しい発見を"],
          ["/jobs", "🤝", "働く", "地域とつながる、一日からのお仕事"],
          ["/learn", "📖", "学ぶ", "生産者のこだわりや想いを知る"],
        ].map(([to, icon, title, description]) => <Link key={to} to={to} className="rounded-2xl border border-marche-line bg-white p-6 text-inherit no-underline transition-colors hover:bg-marche-sage"><span aria-hidden="true" className="text-4xl">{icon}</span><h3 className="mb-0 mt-3 text-lg font-bold">{title}</h3><p className="mb-0 mt-2 text-sm text-marche-muted">{description}</p></Link>)}</div>
      </section>
      <HomeProducers />
      <HomeProducts />
      <HomeExperiences />
      <HomeJobs />
      <HomeStories />
      {isGuest && <section aria-label="生産者の方へ" className="my-10 flex flex-wrap items-center justify-between gap-6 rounded-3xl border border-marche-line p-6 sm:p-10"><div><p className="text-xs font-bold tracking-[0.18em] text-marche-green">FOR PRODUCERS</p><h2 className="font-serif text-2xl sm:text-3xl">あなたの産地の魅力を届けませんか？</h2><p className="text-sm text-marche-muted">商品・体験・お仕事。届け方を広げる第一歩はこちらから。</p></div><Link to="/signup?purpose=producer" className={linkClass}>生産者としてはじめる →</Link></section>}
    </div>
  </>;
}

function HomeSection({ id, eyebrow, title, to, children }: { id: string; eyebrow: string; title: string; to: string; children: ReactNode }) {
  return <section id={id} className="border-t border-marche-line py-10 sm:py-14"><p className="mb-2 text-xs font-bold tracking-[0.18em] text-marche-green">{eyebrow}</p><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="m-0 font-serif text-2xl font-bold leading-relaxed sm:text-3xl">{title}</h2><Link to={to} className={textLinkClass}>一覧を見る →</Link></div>{children}</section>;
}

function HomeProducers() {
  const state = usePublicContent(getProducers);
  const [tab, setTab] = useState("featured");
  const producers = state.data?.filter(producer => producer.badges.includes(tab === "featured" ? "featured" : "new_farmer")).slice(0, 3);
  return <HomeSection id="producers" eyebrow="MEET THE PRODUCERS" title="つくる人を知る" to="/producers">
    <div role="group" aria-label="生産者の表示切り替え" className="my-5 flex flex-wrap gap-2"><button type="button" aria-pressed={tab === "featured"} className={pillClass} onClick={() => setTab("featured")}>注目の生産者</button><button type="button" aria-pressed={tab === "newcomer"} className={pillClass} onClick={() => setTab("newcomer")}>新規就農者</button></div>
    <ContentStatus {...state} />
    {producers && (producers.length ? <div className={gridClass}>{producers.map(producer => <article key={producer.id} className="overflow-hidden rounded-2xl border border-marche-line bg-white"><Link to={`/producers/${producer.id}`} className="block h-full text-inherit no-underline hover:bg-marche-sage"><ContentImage src={producer.coverImageUrl ?? producer.profileImageUrl} alt={producer.businessName} className="aspect-[4/3]" /><div className="p-5"><p className="text-xs font-bold text-marche-green">{tab === "featured" ? "注目の生産者" : "新規就農者"}</p><h3 className="mt-2 text-lg">{producer.businessName}</h3><p className="text-sm text-marche-muted">{producer.prefectureName} {producer.city} ／ {producer.productionItems}</p></div></Link></article>)}</div> : <p className="mt-5 text-marche-muted">現在紹介できる生産者はいません。</p>)}
  </HomeSection>;
}

function HomeProducts() {
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<ProductSort>("popular");
  const categories = usePublicContent(getCategories);
  const loader = useCallback((signal: AbortSignal) => getProducts({ categoryId: category ? Number(category) : undefined, sort, pageSize: 6 }, signal), [category, sort]);
  const state = usePublicContent(loader);
  return <HomeSection id="products" eyebrow="FRESH FROM THE PRODUCERS" title="旬のおすすめ商品" to="/products">
    <div className="my-5 flex flex-wrap items-end justify-between gap-4"><div role="group" aria-label="商品カテゴリー" className="flex flex-wrap gap-2"><button type="button" aria-pressed={!category} className={pillClass} onClick={() => setCategory("")}>すべて</button>{categories.data?.items.map(item => <button key={item.id} type="button" aria-pressed={category === String(item.id)} className={pillClass} onClick={() => setCategory(String(item.id))}>{item.name}</button>)}</div><label className="text-sm font-bold">並び替え<select className={fieldClass} value={sort} onChange={event => setSort(event.target.value as ProductSort)}><option value="popular">おすすめ順</option><option value="price_asc">価格が安い順</option><option value="price_desc">価格が高い順</option></select></label></div>
    <ContentStatus {...categories} /><ContentStatus {...state} />
    {state.data && (state.data.items.length ? <div className={gridClass}>{state.data.items.map(product => <ProductCard key={product.id} product={product} />)}</div> : <p className="mt-5 text-marche-muted">このカテゴリの商品は現在ありません。</p>)}
  </HomeSection>;
}

function HomeExperiences() {
  const state = usePublicContent(getExperiences);
  const items = state.data?.filter(item => item.nextStartAt && new Date(item.nextStartAt).getTime() > Date.now()).sort((a, b) => (a.nextStartAt ?? '').localeCompare(b.nextStartAt ?? '')).slice(0, 3);
  return <HomeSection id="experiences" eyebrow="EXPERIENCE THE LOCAL LIFE" title="産地で体験する" to="/experiences"><ContentStatus {...state} />{items && (items.length ? <div className={gridClass}>{items.map(item => <ExperienceCard key={item.id} experience={item} />)}</div> : <p className="mt-5 text-marche-muted">近日開催の体験は現在ありません。</p>)}</HomeSection>;
}

function HomeJobs() {
  const state = usePublicContent(getJobs);
  const jobs = state.data?.filter(job => job.isAcceptingApplications).sort((a, b) => b.id - a.id).slice(0, 3);
  return <HomeSection id="jobs" eyebrow="WORK WITH PRODUCERS" title="産地で働く" to="/jobs"><ContentStatus {...state} />{jobs && (jobs.length ? <div className={gridClass}>{jobs.map(job => <JobCard key={job.id} job={job} />)}</div> : <p className="mt-5 text-marche-muted">現在募集中のお仕事はありません。</p>)}</HomeSection>;
}

function HomeStories() {
  const state = usePublicContent(getStories);
  const story = state.data?.[0];
  return <HomeSection id="learn" eyebrow="THE STORY BEHIND FOOD" title="つくる人の物語" to="/learn"><ContentStatus {...state} />{state.data && (story ? <article className="mt-6 grid overflow-hidden rounded-3xl bg-marche-sage md:grid-cols-2"><ContentImage src={story.producer.coverImageUrl} alt={story.producer.businessName} className="aspect-[4/3] h-full" /><div className="p-6 sm:p-10"><p className="text-sm font-bold text-marche-green">{story.category.name}</p><h3 className="font-serif text-2xl leading-relaxed"><Link to={`/learn/${story.id}`} className="text-inherit no-underline hover:underline">{story.title}</Link></h3><p>{story.reason ?? story.method}</p><p className="text-sm text-marche-muted">{story.producer.businessName} ／ {story.producer.prefectureName}</p><Link to={`/learn/${story.id}`} className={textLinkClass}>ストーリーを読む →</Link></div></article> : <p className="mt-5 text-marche-muted">公開中のストーリーは現在ありません。</p>)}</HomeSection>;
}
