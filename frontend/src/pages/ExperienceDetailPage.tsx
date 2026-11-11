import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { getExperience } from "../api/experienceApi";
import { ContentImage, ContentPage, ContentSection, ContentStatus, dateLabel, timeLabel, yen, linkClass, panelClass, textLinkClass } from "../components/ui/ContentPage";
import { usePublicContent } from "../hooks/usePublicContent";

export default function ExperienceDetailPage() {
  const { experienceId } = useParams();
  const loader = useCallback((signal: AbortSignal) => getExperience(Number(experienceId), signal), [experienceId]);
  const state = usePublicContent(loader);
  const item = state.data;
  const slots = item?.slots.items.filter((slot) => slot.remainingCapacity > 0 && new Date(slot.startAt).getTime() > Date.now()) ?? [];
  return (
    <ContentPage
      eyebrow="EXPERIENCE"
      title={item?.title ?? "体験詳細"}
    >
      <Link
        to="/experiences"
        className={textLinkClass}
      >
        ← 体験一覧
      </Link>
      <ContentStatus {...state} />
      {item && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {(item.images.length ? [...item.images].sort((a, b) => a.sortOrder - b.sortOrder) : [{ id: 0, url: item.thumbnailUrl, sortOrder: 0 }]).map((image) => (
              <ContentImage
                key={image.id}
                src={image.url}
                alt={item.title}
                className="aspect-[4/3] rounded-2xl"
              />
            ))}
          </div>
          <div className="mt-8 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <p className="text-marche-green">
                {item.familyOk && "親子参加OK ・ "}
                {item.beginnerOk && "初心者歓迎"}
              </p>
              <Link
                to={`/producers/${item.producer.id}`}
                className={textLinkClass}
              >
                案内：{item.producer.businessName} →
              </Link>
              <ContentSection
                title="体験内容"
                text={item.description}
              />
              <ContentSection
                title="開催場所"
                text={item.place}
              />
              <ContentSection
                title="参加対象"
                text={item.ageCondition}
              />
              <ContentSection
                title="当日の流れ"
                items={item.flow}
              />
              <ContentSection
                title="持ち物"
                items={item.belongings}
              />
              <ContentSection
                title="注意事項"
                items={item.notes}
              />
              <ContentSection
                title="キャンセルポリシー"
                text={item.cancelPolicy}
              />
            </div>
            <aside
              className={`${panelClass} lg:sticky lg:top-28`}
              aria-label="料金と開催日"
            >
              <p className="mt-0 text-2xl font-bold text-marche-green">
                {yen(item.priceAdult)}
                <span className="text-sm font-normal"> ／大人1名</span>
              </p>
              {item.priceChild !== null && <p>子ども：{yen(item.priceChild)} ／1名</p>}
              <h2 className="text-lg">開催日</h2>
              {item.slots.items.map((slot) => (
                <p
                  key={slot.id}
                  className="border-b border-marche-line pb-3 text-sm"
                >
                  {dateLabel(slot.startAt)}
                  <br />
                  {timeLabel(slot.startAt)}〜（{slot.durationMin}分）
                  <br />
                  残り{slot.remainingCapacity}名 ／定員{slot.capacity}名
                </p>
              ))}
              {slots.length ? (
                <Link
                  to={`/experiences/${item.id}/apply`}
                  className={linkClass}
                >
                  参加を申し込む
                </Link>
              ) : (
                <p role="status">現在申し込める開催枠はありません。</p>
              )}
              <p className="mb-0 text-xs text-marche-muted">次の画面で開催日と人数を選び、内容を確認します。</p>
            </aside>
          </div>
        </>
      )}
    </ContentPage>
  );
}
