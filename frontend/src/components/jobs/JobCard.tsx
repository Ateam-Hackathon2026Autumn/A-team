import { Link } from 'react-router';
import type { Job } from '../../types/job';
import { ContentImage, yen } from '../ui/ContentPage';
export const payLabel = (job: Job) => `${({ hourly: '時給', daily: '日給', monthly: '月給' } as Record<string, string>)[job.payUnit] ?? job.payUnit} ${yen(job.payAmount)}`;
export const genreLabel = (genre: string) => ({ agriculture: '農業', fishery: '漁業', livestock: '畜産' } as Record<string, string>)[genre] ?? genre;
export const termLabel = (term: string) => ({ one_day: '1日', short: '短期', long: '長期' } as Record<string, string>)[term] ?? term;
export default function JobCard({ job }: { job: Job }) {
  return <article className="overflow-hidden rounded-2xl border border-marche-line bg-white">
    <ContentImage src={job.coverImageUrl} alt={job.title} className="aspect-[4/3]" />
    <div className="p-5"><p className="m-0 text-xs font-bold text-marche-green">{termLabel(job.termType)} ・ {genreLabel(job.producer.genre)}</p>
      <h2 className="my-3 font-serif text-xl"><Link to={`/jobs/${job.id}`} className="text-marche-ink no-underline hover:underline">{job.title}</Link></h2>
      <p className="text-lg font-bold text-marche-green">{payLabel(job)}</p>
      <p className="text-sm text-marche-muted">{job.producer.businessName}<br />{job.workPlace}<br />{job.workHours} ・ 募集{job.slots}名</p>
      <div className="flex flex-wrap gap-2 text-xs">{job.inexperiencedOk && <span className="rounded-full bg-marche-sage px-3 py-1">未経験歓迎</span>}<span className="rounded-full bg-marche-sage px-3 py-1">{job.isAcceptingApplications ? '募集中' : '募集終了'}</span></div>
    </div>
  </article>;
}
