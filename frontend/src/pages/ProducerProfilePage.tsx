import { useCallback } from "react";
import { Link, useParams } from "react-router";
import ApiError from "../api/apiError";
import { getProducer } from "../api/producerApi";
import { getProducts } from "../api/productApi";
import { getExperiences } from "../api/experienceApi";
import { getJobs } from "../api/jobApi";
import { contentJson } from "../api/publicContentApi";
import type { Story } from "../types/story";
import { usePublicContent } from "../hooks/usePublicContent";
import { ContentPage, ContentStatus, ContentImage, EmptyContent, panelClass, textLinkClass } from "../components/ui/ContentPage";
import ProductCard from "../components/products/ProductCard";
import ExperienceCard from "../components/experiences/ExperienceCard";
import JobCard from "../components/jobs/JobCard";
import { producerGenres, producerBadges } from "../components/producers/ProducerSummaryCard";
import Button from "../components/ui/Button";

export default function ProducerProfilePage() {
  const { producerId } = useParams();
  const loader = useCallback(
    async (signal: AbortSignal) => {
      if (!producerId || !/^[1-9]\d*$/.test(producerId) || !Number.isSafeInteger(Number(producerId))) throw new ApiError(404, "生産者が見つかりません。");
      return getProducer(Number(producerId), signal);
    },
    [producerId],
  );
  const state = usePublicContent(loader);
  const producer = state.data;
  const relatedLoader = useCallback(
    async (signal: AbortSignal) => {
      if (!producer) return null;
      const results = await Promise.allSettled([getProducts({ producerId: producer.id, pageSize: 6 }, signal), getExperiences(signal, { producerId: producer.id }), getJobs(signal, { producerId: producer.id }), producer.hasPublicStory ? contentJson<Story>(`/api/v1/producers/${producer.id}/story`, signal) : Promise.resolve(null)]);
      return { products: results[0], experiences: results[1], jobs: results[2], story: results[3] };
    },
    [producer],
  );
  const related = usePublicContent(relatedLoader);
  return (
    <ContentPage
      eyebrow="PRODUCER"
      title={producer?.businessName ?? "生産者プロフィール"}
    >
      <Link
        to="/producers"
        className={textLinkClass}
      >
        ← 生産者一覧へ
      </Link>
      <ContentStatus
        {...state}
        notFoundTo="/producers"
      />
      {producer && (
        <>
          <ContentImage
            src={producer.coverImageUrl}
            alt={`${producer.businessName}の風景`}
            className="mt-6 aspect-[16/7] rounded-2xl"
          />
          <section className={`${panelClass} my-6`}>
            <div className="flex flex-wrap items-center gap-5">
              <ContentImage
                src={producer.profileImageUrl}
                alt={producer.representativeName}
                className="size-24 shrink-0 rounded-full"
              />
              <div>
                <p className="m-0 text-sm text-marche-muted">
                  {producerGenres[producer.genre] ?? producer.genre} · {producer.prefectureName} {producer.city}
                </p>
                <h2 className="mb-1 mt-2 font-serif text-2xl">{producer.businessName}</h2>
                <p className="m-0">
                  {producer.representativeName} · {producer.productionItems}
                </p>
              </div>
            </div>
            <div className="my-5 flex flex-wrap gap-2">
              {producer.badges.map((badge) => (
                <span
                  key={badge}
                  className="rounded-full bg-marche-sage px-3 py-1 text-xs font-bold text-marche-green"
                >
                  {producerBadges[badge] ?? badge}
                </span>
              ))}
            </div>
            <p className="whitespace-pre-line">{producer.intro}</p>
            {(producer.foundedYear !== null || producer.careerStartYear !== null) &&
              <p className="text-sm text-marche-muted">
                {[
                  producer.foundedYear !== null ? `創業 ${producer.foundedYear}年` : null,
                  producer.careerStartYear !== null ? `${producer.careerStartYear}年から生産に従事` : null,
                ].filter(Boolean).join(" · ")}
              </p>}
            <Button
              disabled
              variant="outline"
            >
              お気に入り登録（準備中）
            </Button>
          </section>
          <nav
            aria-label="生産者のコンテンツ"
            className="flex flex-wrap gap-5"
          >
            {[
              ["producer-products", "商品"],
              ["producer-experiences", "体験"],
              ["producer-jobs", "求人"],
              ["producer-story", "ストーリー"],
            ].map(([id, text]) => (
              <a
                key={id}
                href={`#${id}`}
                className={textLinkClass}
              >
                {text}
              </a>
            ))}
          </nav>
          <ContentStatus {...related} />
          <section
            id="producer-products"
            className="my-10"
          >
            <h2 className="font-serif text-2xl">この生産者の商品</h2>
            {related.data?.products.status === "fulfilled" ? (
              related.data.products.value.items.length ? (
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {related.data.products.value.items.map((product) => (
                    <ProductCard
                      key={product.id}
                      product={product}
                    />
                  ))}
                </div>
              ) : (
                <EmptyContent>現在販売中の商品はありません。</EmptyContent>
              )
            ) : (
              related.data && (
                <p role="alert">
                  商品を取得できませんでした。
                  <Button
                    variant="outline"
                    onClick={related.retry}
                  >
                    再読み込み
                  </Button>
                </p>
              )
            )}
          </section>
          <section
            id="producer-experiences"
            className="my-10"
          >
            <h2 className="font-serif text-2xl">産地で体験する</h2>
            {related.data?.experiences.status === "fulfilled" ? (
              related.data.experiences.value.length ? (
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {related.data.experiences.value.map((experience) => (
                      <ExperienceCard
                        key={experience.id}
                        experience={experience}
                      />
                    ))}
                </div>
              ) : (
                <EmptyContent>現在受け付けている体験はありません。</EmptyContent>
              )
            ) : (
              related.data && (
                <p role="alert">
                  体験を取得できませんでした。
                  <Button
                    variant="outline"
                    onClick={related.retry}
                  >
                    再読み込み
                  </Button>
                </p>
              )
            )}
          </section>
          <section
            id="producer-jobs"
            className="my-10"
          >
            <h2 className="font-serif text-2xl">一緒に働く</h2>
            {related.data?.jobs.status === "fulfilled" ? (
              related.data.jobs.value.length ? (
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {related.data.jobs.value.map((job) => (
                      <JobCard
                        key={job.id}
                        job={job}
                      />
                    ))}
                </div>
              ) : (
                <EmptyContent>現在募集中のお仕事はありません。</EmptyContent>
              )
            ) : (
              related.data && (
                <p role="alert">
                  求人を取得できませんでした。
                  <Button
                    variant="outline"
                    onClick={related.retry}
                  >
                    再読み込み
                  </Button>
                </p>
              )
            )}
          </section>
          <section
            id="producer-story"
            className={`${panelClass} my-10`}
          >
            <p className="text-xs font-bold tracking-widest text-marche-green">STORY</p>
            <h2 className="font-serif text-2xl">つくる人の想いを知る</h2>
            {related.data?.story.status === "fulfilled" ? (
              related.data.story.value ? (
                <>
                  <h3 className="font-serif text-xl">{related.data.story.value.title}</h3>
                  <Link
                    to={`/learn/${related.data.story.value.id}`}
                    className={textLinkClass}
                  >
                    ストーリーを読む →
                  </Link>
                </>
              ) : (
                <p>ストーリーは準備中です。</p>
              )
            ) : (
              related.data && (
                <p role="alert">
                  ストーリーを取得できませんでした。
                  <Button
                    variant="outline"
                    onClick={related.retry}
                  >
                    再読み込み
                  </Button>
                </p>
              )
            )}
          </section>
        </>
      )}
    </ContentPage>
  );
}
