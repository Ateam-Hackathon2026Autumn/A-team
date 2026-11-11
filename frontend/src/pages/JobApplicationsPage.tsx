import { Link } from "react-router";
import { getJobApplications } from "../api/jobApi";
import { ContentPage, ContentStatus, dateLabel, EmptyContent, linkClass, panelClass, textLinkClass } from "../components/ui/ContentPage";
import { usePublicContent } from "../hooks/usePublicContent";

const labels: Record<string, string> = { applied: "応募済み", screening: "選考中", hired: "採用", rejected: "不採用", withdrawn: "取り下げ済み", completed: "勤務完了" };

export default function JobApplicationsPage() {
  const state = usePublicContent(getJobApplications);
  return (
    <ContentPage
      eyebrow="MY APPLICATIONS"
      title="求人応募状況"
      intro="応募したお仕事と選考状況を確認できます。"
    >
      <Link
        to="/jobs"
        className={textLinkClass}
      >
        お仕事を探す →
      </Link>
      <ContentStatus {...state} />
      {state.data &&
        (state.data.length ? (
          <div className="mt-6 space-y-5">
            {state.data.map((application) => (
              <article
                key={application.id}
                className={panelClass}
              >
                <span className="rounded-full bg-marche-sage px-4 py-2 text-sm font-bold text-marche-green">{labels[application.status] ?? "状況確認中"}</span>
                <h2 className="font-serif text-xl">{application.job.title ?? "公開を終了した求人"}</h2>
                <p className="text-sm text-marche-muted">応募日：{dateLabel(application.createdAt)}</p>
                <p>勤務希望日：{application.workDates.length ? application.workDates.map((day) => dateLabel(day.workDate)).join("、") : "日程調整中"}</p>
                {application.job.isPublic ? (
                  <Link
                    to={`/jobs/${application.job.id}`}
                    className={textLinkClass}
                  >
                    求人詳細を見る →
                  </Link>
                ) : (
                  <p>この求人は現在公開されていません。</p>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyContent>
            <p>応募したお仕事はまだありません。</p>
            <Link
              to="/jobs"
              className={linkClass}
            >
              お仕事を探す
            </Link>
          </EmptyContent>
        ))}
    </ContentPage>
  );
}
