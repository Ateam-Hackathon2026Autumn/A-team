import { Link } from 'react-router';
import type { Job } from '../../types/job';
import { ContentImage } from '../ui/ContentPage';
import { payLabel, genreLabel, termLabel } from './jobCardLabels';
export default function JobCard({ job }: { job: Job }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-marche-line bg-white">
      <Link
        to={`/jobs/${job.id}`}
        aria-label={job.title}
        className="group block h-full text-marche-ink no-underline hover:bg-marche-sage/40 focus-visible:-outline-offset-3"
      >
        <ContentImage
          src={job.coverImageUrl}
          alt={job.title}
          className="aspect-[4/3]"
        />
        <div className="p-5">
          <p className="m-0 text-xs font-bold text-marche-green">
            {termLabel(job.termType)} ・ {genreLabel(job.producer.genre)}
          </p>
          <h2 className="my-3 font-serif text-xl group-hover:underline">
            {job.title}
          </h2>
          <p className="text-lg font-bold text-marche-green">{payLabel(job)}</p>
          <p className="text-sm text-marche-muted">
            {job.producer.businessName}
            <br />
            {job.workPlace}
            <br />
            {job.workHours} ・ 募集{job.slots}名
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            {job.inexperiencedOk && (
              <span className="rounded-full bg-marche-sage px-3 py-1">
                未経験歓迎
              </span>
            )}
            <span className="rounded-full bg-marche-sage px-3 py-1">
              {job.isAcceptingApplications ? '募集中' : '募集終了'}
            </span>
          </div>
        </div>
      </Link>
    </article>
  );
}
