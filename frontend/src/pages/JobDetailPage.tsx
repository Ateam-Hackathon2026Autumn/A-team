import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { getJob } from "../api/jobApi";
import { genreLabel, payLabel, termLabel } from "../components/jobs/JobCard";
import { ContentImage, ContentPage, ContentSection, ContentStatus, dateLabel, linkClass, panelClass, textLinkClass } from "../components/ui/ContentPage";
import { usePublicContent } from "../hooks/usePublicContent";

export default function JobDetailPage() {
  const { jobId } = useParams();
  const loader = useCallback((signal: AbortSignal) => getJob(Number(jobId), signal), [jobId]);
  const state = usePublicContent(loader);
  const job = state.data;
  const selectable = job?.workDates.items.some((day) => day.isSelectable && day.remainingCount > 0);
  return (
    <ContentPage
      eyebrow="JOB"
      title={job?.title ?? "求人詳細"}
    >
      <Link
        to="/jobs"
        className={textLinkClass}
      >
        ← 求人一覧
      </Link>
      <ContentStatus {...state} notFoundTo="/jobs" />
      {job && (
        <div className="mt-5 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div>
            <ContentImage
              src={job.coverImageUrl}
              alt={job.title}
              className="aspect-[16/9] rounded-2xl"
            />
            <p className="text-sm font-bold text-marche-green">
              {termLabel(job.termType)} ・ {genreLabel(job.producer.genre)}
              {job.inexperiencedOk && " ・ 未経験歓迎"}
            </p>
            <ContentSection
              title="仕事内容"
              text={job.description}
            />
            <ContentSection
              title="応募条件"
              items={job.requirements}
            />
            <ContentSection
              title="持ち物"
              items={job.belongings}
            />
            <ContentSection
              title="注意事項"
              items={job.notes}
            />
            <section className={panelClass}>
              <h2 className="font-serif text-xl">事業者情報</h2>
              <p>{job.producer.businessName}</p>
              <Link
                className={textLinkClass}
                to={`/producers/${job.producer.id}`}
              >
                プロフィールを見る →
              </Link>
            </section>
          </div>
          <aside
            className={`${panelClass} lg:sticky lg:top-28`}
            aria-label="勤務条件"
          >
            <p className="mt-0 text-2xl font-bold text-marche-green">{payLabel(job)}</p>
            <dl className="m-0 space-y-3">
              <dt className="font-bold">募集期間</dt>
              <dd className="ml-0">
                {job.periodStart ? dateLabel(job.periodStart) : "随時"} 〜 {job.periodEnd ? dateLabel(job.periodEnd) : "終了日未定"}
              </dd>
              <dt className="font-bold">勤務時間</dt>
              <dd className="ml-0">{job.workHours}</dd>
              <dt className="font-bold">勤務地</dt>
              <dd className="ml-0">{job.workPlace}</dd>
              <dt className="font-bold">募集人数</dt>
              <dd className="ml-0">{job.slots}名</dd>
            </dl>
            <h2 className="mt-6 text-lg">応募できる勤務日</h2>
            {job.workDates.items.map((day) => (
              <p
                key={day.id}
                className="text-sm"
              >
                {dateLabel(day.workDate)} ・ {day.isSelectable && day.remainingCount > 0 ? `残り${day.remainingCount}名` : "受付終了"}
              </p>
            ))}
            {job.isAcceptingApplications && selectable ? (
              <Link
                className={linkClass}
                to={`/jobs/${job.id}/apply`}
              >
                この仕事に応募する
              </Link>
            ) : (
              <p role="status">現在応募を受け付けていません。</p>
            )}
            <p className="text-xs text-marche-muted">応募後、生産者が内容を確認します。応募時点では採用は確定しません。</p>
          </aside>
        </div>
      )}
    </ContentPage>
  );
}
