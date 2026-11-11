import { Link, useSearchParams } from "react-router";
import { getJobs } from "../api/jobApi";
import JobCard from "../components/jobs/JobCard";
import Button from "../components/ui/Button";
import { areas, ContentPage, ContentStatus, EmptyContent, fieldClass, panelClass, textLinkClass } from "../components/ui/ContentPage";
import { usePublicContent } from "../hooks/usePublicContent";

export default function JobListPage() {
  const state = usePublicContent(getJobs);
  const [params, setParams] = useSearchParams();
  const update = (name: string, value: string) =>
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      if (value) next.set(name, value);
      else next.delete(name);
      return next;
    });
  const day = params.get("day") ?? "";
  const items = (state.data ?? [])
    .filter(
      (job) =>
        (!params.get("area") || job.areaId === Number(params.get("area"))) &&
        (!params.get("genre") || job.producer.genre === params.get("genre")) &&
        (!params.get("term") || job.termType === params.get("term")) &&
        (!params.get("pay") || (job.payUnit === "hourly" && job.payAmount >= Number(params.get("pay")))) &&
        (!params.get("beginner") || job.inexperiencedOk) &&
        (!params.get("producerId") || job.producer.id === Number(params.get("producerId"))) &&
        (!day || ((!job.periodStart || job.periodStart <= day) && (!job.periodEnd || day <= job.periodEnd))),
    )
    .sort((a, b) => (params.get("sort") === "slots" ? b.slots - a.slots : b.id - a.id));
  return (
    <ContentPage
      eyebrow="JOBS"
      title="1日から、農と海の仕事へ。"
      intro="はじめてのお手伝いから、これからの仕事まで。生産者と一緒に働きませんか。"
    >
      <Link
        to="/mypage/jobs"
        className={textLinkClass}
      >
        応募状況を確認 →
      </Link>
      <section
        aria-label="求人の絞り込み"
        className={`${panelClass} mt-4`}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm font-bold">
            勤務希望日
            <input
              type="date"
              className={fieldClass}
              value={day}
              onChange={(event) => update("day", event.target.value)}
            />
          </label>
          <label className="text-sm font-bold">
            地域
            <select
              className={fieldClass}
              value={params.get("area") ?? ""}
              onChange={(event) => update("area", event.target.value)}
            >
              {areas.map((area, index) => (
                <option
                  key={area}
                  value={index || ""}
                >
                  {area}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-bold">
            業種
            <select
              className={fieldClass}
              value={params.get("genre") ?? ""}
              onChange={(event) => update("genre", event.target.value)}
            >
              <option value="">すべての業種</option>
              <option value="agriculture">農業</option>
              <option value="fishery">漁業</option>
              <option value="livestock">畜産</option>
            </select>
          </label>
          <label className="text-sm font-bold">
            期間
            <select
              className={fieldClass}
              value={params.get("term") ?? ""}
              onChange={(event) => update("term", event.target.value)}
            >
              <option value="">すべての期間</option>
              <option value="one_day">1日</option>
              <option value="short">短期</option>
              <option value="long">長期</option>
            </select>
          </label>
          <label className="text-sm font-bold">
            時給
            <select
              className={fieldClass}
              value={params.get("pay") ?? ""}
              onChange={(event) => update("pay", event.target.value)}
            >
              <option value="">指定なし（日給・月給も表示）</option>
              <option value="1100">1,100円以上</option>
              <option value="1200">1,200円以上</option>
              <option value="1400">1,400円以上</option>
            </select>
          </label>
          <label className="text-sm font-bold">
            並び替え
            <select
              className={fieldClass}
              value={params.get("sort") ?? ""}
              onChange={(event) => update("sort", event.target.value)}
            >
              <option value="">掲載IDの新しい順</option>
              <option value="slots">募集人数の多い順</option>
            </select>
          </label>
        </div>
        <p className="text-xs text-marche-muted">勤務希望日は募集期間で絞り込みます。実際に応募できる日は求人詳細でご確認ください。</p>
        <div className="flex flex-wrap items-center gap-5">
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="checkbox"
              className="size-5 accent-marche-green"
              checked={Boolean(params.get("beginner"))}
              onChange={(event) => update("beginner", event.target.checked ? "1" : "")}
            />
            未経験歓迎
          </label>
          <Button
            variant="outline"
            onClick={() => setParams({})}
          >
            条件をクリア
          </Button>
        </div>
      </section>
      <ContentStatus {...state} />
      {!state.loading && !state.error && (
        <>
          <p
            role="status"
            className="my-6 font-bold"
          >
            {items.length}件のお仕事
          </p>
          {items.length ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                />
              ))}
            </div>
          ) : (
            <EmptyContent>
              <p>条件に合うお仕事がありません。</p>
              <Button
                variant="outline"
                onClick={() => setParams({})}
              >
                条件をクリア
              </Button>
            </EmptyContent>
          )}
        </>
      )}
      <aside className="mt-10 rounded-2xl bg-marche-sage p-6">
        <h2 className="font-serif text-xl">いつかは自分で、と考えている方へ</h2>
        <p>生産者の想いや日々の工夫を、ストーリーで紹介しています。</p>
        <Link
          to="/learn"
          className={textLinkClass}
        >
          就農ストーリーを読む →
        </Link>
      </aside>
    </ContentPage>
  );
}
