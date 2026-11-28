import type { Job } from '../../types/job';
import { yen } from '../ui/contentPageValues';

export const payLabel = (job: Job) =>
  `${({ hourly: '時給', daily: '日給', monthly: '月給' } as Record<string, string>)[job.payUnit] ?? job.payUnit} ${yen(job.payAmount)}`;
export const genreLabel = (genre: string) =>
  (
    ({ agriculture: '農業', fishery: '漁業', livestock: '畜産' }) as Record<
      string,
      string
    >
  )[genre] ?? genre;
export const termLabel = (term: string) =>
  (({ one_day: '1日', short: '短期', long: '長期' }) as Record<string, string>)[
    term
  ] ?? term;
