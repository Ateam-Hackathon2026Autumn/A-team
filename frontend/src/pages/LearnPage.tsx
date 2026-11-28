import { Link, useSearchParams } from 'react-router';
import { getStories, storyLead } from '../api/storyApi';
import { producerGenres } from '../components/producers/producerLabels';
import {
  ContentImage,
  ContentPage,
  ContentStatus,
  EmptyContent,
} from '../components/ui/ContentPage';
import { textLinkClass } from '../components/ui/contentPageValues';
import { usePublicContent } from '../hooks/usePublicContent';
export default function LearnPage() {
  const state = usePublicContent(getStories);
  const [params, setParams] = useSearchParams();
  // テーマは生産者のジャンル（農業・漁業・畜産など）。ストーリーのある生産者のジャンルだけボタンにする
  const genre = params.get('genre') ?? '';
  const genres = [
    ...new Set((state.data ?? []).map((story) => story.producer.genre)),
  ].map((value) => [value, producerGenres[value] ?? value]);
  const articles = (state.data ?? []).filter(
    (story) => !genre || story.producer.genre === genre,
  );
  const featured = articles[0];
  return (
    <ContentPage
      eyebrow="STORIES"
      title="つくる人のはなし"
      intro="生産者の想いと、ものができるまで。"
    >
      <ContentStatus {...state} />
      {state.data && (
        <>
          <nav
            aria-label="ストーリーのテーマ"
            className="mb-8 flex flex-wrap gap-3"
          >
            {[['', 'すべて'], ...genres].map(([id, name]) => (
              <button
                key={id}
                type="button"
                aria-pressed={genre === id}
                onClick={() => setParams(id ? { genre: id } : {})}
                className={`min-h-11 cursor-pointer rounded-full border border-marche-green px-5 py-2 font-sans text-sm font-bold ${genre === id ? 'bg-marche-green text-white' : 'bg-white text-marche-green hover:bg-marche-sage'}`}
              >
                {name}
              </button>
            ))}
          </nav>
          {featured ? (
            <>
              <article className="overflow-hidden rounded-2xl border border-marche-line bg-white">
                <Link
                  to={`/learn/${featured.id}`}
                  aria-label={featured.producer.businessName}
                  className="group grid h-full text-marche-ink no-underline hover:bg-marche-sage/40 focus-visible:-outline-offset-3 md:grid-cols-2"
                >
                  <ContentImage
                    src={featured.producer.coverImageUrl}
                    alt={featured.producer.businessName}
                    className="aspect-[4/3] h-full"
                  />
                  <div className="p-6 sm:p-10">
                    <p className="text-sm font-bold text-marche-green">
                      特集 ・{' '}
                      {producerGenres[featured.producer.genre] ??
                        featured.producer.genre}
                    </p>
                    <h2 className="font-serif text-2xl leading-relaxed group-hover:underline">
                      {featured.producer.businessName}
                    </h2>
                    <p className="line-clamp-4 whitespace-pre-line">
                      {storyLead(featured)}
                    </p>
                    <p className="text-sm text-marche-muted">
                      {featured.producer.prefectureName}{' '}
                      {featured.producer.city}
                    </p>
                    <span className={textLinkClass}>ストーリーを読む →</span>
                  </div>
                </Link>
              </article>
              {articles.length > 1 && (
                <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {articles.slice(1).map((story) => (
                    <article
                      key={story.id}
                      className="overflow-hidden rounded-2xl border border-marche-line bg-white"
                    >
                      <Link
                        to={`/learn/${story.id}`}
                        aria-label={story.producer.businessName}
                        className="group block h-full p-5 text-marche-ink no-underline hover:bg-marche-sage/40 focus-visible:-outline-offset-3 sm:p-8"
                      >
                        <ContentImage
                          src={story.producer.coverImageUrl}
                          alt={story.producer.businessName}
                          className="aspect-[4/3] rounded-xl"
                        />
                        <p className="text-sm text-marche-green">
                          {producerGenres[story.producer.genre] ??
                            story.producer.genre}
                        </p>
                        <h2 className="font-serif text-xl">
                          <span className={textLinkClass}>
                            {story.producer.businessName}
                          </span>
                        </h2>
                        <p className="line-clamp-3">{storyLead(story)}</p>
                      </Link>
                    </article>
                  ))}
                </div>
              )}
            </>
          ) : (
            <EmptyContent>
              <p>このテーマの記事は準備中です。</p>
              <button
                type="button"
                onClick={() => setParams({})}
                className={`${textLinkClass} cursor-pointer border-0 bg-transparent font-sans`}
              >
                すべての記事を見る
              </button>
            </EmptyContent>
          )}
          <aside className="mt-10 rounded-2xl bg-marche-sage p-6">
            <h2 className="font-serif text-xl">つくる人と、つながろう。</h2>
            <p>生産者のプロフィールで、商品や体験、お仕事を探せます。</p>
            <Link to="/producers" className={textLinkClass}>
              生産者の一覧を見る →
            </Link>
          </aside>
        </>
      )}
    </ContentPage>
  );
}
