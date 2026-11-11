import { Link, useSearchParams } from 'react-router';
import { getStories } from '../api/storyApi';
import { ContentImage, ContentPage, ContentStatus, EmptyContent, panelClass, textLinkClass } from '../components/ui/ContentPage';
import { usePublicContent } from '../hooks/usePublicContent';
export default function LearnPage() {
  const state = usePublicContent(getStories);
  const [params, setParams] = useSearchParams();
  const category = params.get('category') ?? '';
  const categories = [...new Map((state.data ?? []).map(story => [String(story.category.id), story.category.name])).entries()];
  const articles = (state.data ?? []).filter(story => !category || String(story.category.id) === category);
  const featured = articles[0];
  return <ContentPage eyebrow="STORIES" title="つくる人のはなし" intro="生産者の想いと、ものができるまで。">
    <ContentStatus {...state} />
    {state.data && <>
      <nav aria-label="ストーリーのテーマ" className="mb-8 flex flex-wrap gap-3">{[['', 'すべて'], ...categories].map(([id, name]) => <button key={id} type="button" aria-pressed={category === id} onClick={() => setParams(id ? { category: id } : {})} className={`min-h-11 cursor-pointer rounded-full border border-marche-green px-5 py-2 font-sans text-sm font-bold ${category === id ? 'bg-marche-green text-white' : 'bg-white text-marche-green hover:bg-marche-sage'}`}>{name}</button>)}</nav>
      {featured ? <>
        <article className="grid overflow-hidden rounded-2xl border border-marche-line bg-white md:grid-cols-2"><ContentImage src={featured.producer.coverImageUrl} alt={featured.producer.businessName} className="aspect-[4/3] h-full" /><div className="p-6 sm:p-10"><p className="text-sm font-bold text-marche-green">特集 ・ {featured.category.name}</p><h2 className="font-serif text-2xl leading-relaxed"><Link to={`/learn/${featured.id}`} className="text-marche-ink no-underline hover:underline">{featured.title}</Link></h2><p>{featured.reason ?? featured.method}</p><p className="text-sm text-marche-muted">{featured.producer.businessName} ・ {featured.producer.prefectureName}</p><Link to={`/learn/${featured.id}`} className={textLinkClass}>ストーリーを読む →</Link></div></article>
        {articles.length > 1 && <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{articles.slice(1).map(story => <article key={story.id} className={panelClass}><ContentImage src={story.producer.coverImageUrl} alt={story.producer.businessName} className="aspect-[4/3] rounded-xl" /><p className="text-sm text-marche-green">{story.category.name}</p><h2 className="font-serif text-xl"><Link to={`/learn/${story.id}`} className={textLinkClass}>{story.title}</Link></h2><p>{story.producer.businessName}</p></article>)}</div>}
      </> : <EmptyContent><p>このテーマの記事は準備中です。</p><button type="button" onClick={() => setParams({})} className={`${textLinkClass} cursor-pointer border-0 bg-transparent font-sans`}>すべての記事を見る</button></EmptyContent>}
      <aside className="mt-10 rounded-2xl bg-marche-sage p-6"><h2 className="font-serif text-xl">つくる人と、つながろう。</h2><p>生産者のプロフィールで、商品や体験、お仕事を探せます。</p><Link to="/producers" className={textLinkClass}>生産者の一覧を見る →</Link></aside>
    </>}
  </ContentPage>;
}
