import { useCallback } from 'react';
import { Link, useParams } from 'react-router';
import { getStory } from '../api/storyApi';
import { getProducts } from '../api/productApi';
import ProductCard from '../components/products/ProductCard';
import { ContentImage, ContentPage, ContentSection, ContentStatus, dateLabel, panelClass, textLinkClass } from '../components/ui/ContentPage';
import { usePublicContent } from '../hooks/usePublicContent';
export default function StoryDetailPage() {
  const { storyId } = useParams();
  const loader = useCallback((signal: AbortSignal) => getStory(Number(storyId), signal), [storyId]);
  const state = usePublicContent(loader);
  const story = state.data;
  return <ContentPage eyebrow="STORY" title={story?.title ?? 'ストーリー詳細'}>
    <Link to="/learn" className={textLinkClass}>← 記事一覧</Link><ContentStatus {...state} notFoundTo="/learn" />
    {story && <article className="mx-auto mt-5 max-w-4xl">
      <ContentImage src={story.producer.coverImageUrl} alt={story.producer.businessName} className="aspect-[16/9] rounded-2xl" />
      <div className="mx-auto max-w-2xl"><p className="mt-6 text-sm font-bold text-marche-green">{story.category.name}</p><p>{story.producer.businessName} ／ {story.producer.prefectureName} {story.producer.city}</p><p className="text-xs text-marche-muted">更新：{dateLabel(story.updatedAt)}</p>
        <ContentSection title="この仕事を選んだ理由" text={story.reason} />
        <ContentSection title="栽培・生産で大切にしていること" text={story.method} />
        <ContentSection title="ものができるまで" text={story.process} />
        <ContentSection title="環境への取り組み" text={story.environment} />
        <ContentSection title="これからの目標" text={story.goal} />
        <aside className={panelClass}><h2 className="font-serif text-xl">{story.producer.businessName}とつながる</h2><div className="flex flex-wrap gap-x-6 gap-y-2"><Link to={`/producers/${story.producerId}`} className={textLinkClass}>プロフィールを見る →</Link>{story.producer.acceptsExperience && <Link to={`/experiences?producerId=${story.producerId}`} className={textLinkClass}>体験に参加する →</Link>}{story.producer.recruiting && <Link to={`/jobs?producerId=${story.producerId}`} className={textLinkClass}>お仕事を見る →</Link>}</div></aside>
        <RelatedProducts key={story.producerId} producerId={story.producerId} />
      </div>
    </article>}
  </ContentPage>;
}

function RelatedProducts({ producerId }: { producerId: number }) {
  const loader = useCallback((signal: AbortSignal) => getProducts({ producerId, pageSize: 3 }, signal), [producerId]);
  const state = usePublicContent(loader);
  return <section className="mt-10"><h2 className="font-serif text-xl">この生産者の商品</h2><ContentStatus {...state} />{state.data && (state.data.items.length ? <div className="grid gap-4 sm:grid-cols-2">{state.data.items.map(product => <ProductCard key={product.id} product={product} />)}</div> : <p>現在公開中の商品はありません。</p>)}</section>;
}
