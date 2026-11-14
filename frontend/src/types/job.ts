import type { PageResult } from './experience';
export type Job = {
  id: number; title: string; producer: { id: number; businessName: string; genre: string };
  areaId: number; prefectureName: string; termType: string; payUnit: string; payAmount: number;
  periodStart: string | null; periodEnd: string | null; workHours: string; workPlace: string;
  slots: number; inexperiencedOk: boolean; coverImageUrl: string | null; isAcceptingApplications: boolean;
};
export type JobDetail = Job & {
  description: string; requirements: string[]; belongings: string[]; notes: string[];
  workDates: PageResult<{ id: number; workDate: string; remainingCount: number; isSelectable: boolean }>;
};
export type JobApplication = {
  id: number; job: { id: number; title: string | null; isPublic: boolean };
  workDates: { id: number; workDate: string }[]; status: string; createdAt: string;
};
export type JobInput = { workDateIds: number[]; message: string; answers: never[] };
