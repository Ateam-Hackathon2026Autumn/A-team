import type { PageResult } from './experience';
export type Job = {
  id: number;
  title: string;
  producer: { id: number; businessName: string; genre: string };
  areaId: number;
  prefectureName: string;
  termType: string;
  payUnit: string;
  payAmount: number;
  periodStart: string | null;
  periodEnd: string | null;
  workHours: string;
  workPlace: string;
  slots: number;
  inexperiencedOk: boolean;
  coverImageUrl: string | null;
  isAcceptingApplications: boolean;
};
export type JobDetail = Job & {
  description: string;
  requirements: string[] | null;
  belongings: string[] | null;
  notes: string[] | null;
  hasApplied: boolean;
  applicationQuestions: never[];
  workDates: PageResult<{
    id: number;
    workDate: string;
    neededCount: number;
    remainingCount: number;
    isSelectable: boolean;
  }>;
};
export type JobApplication = {
  id: number;
  job: { id: number; title: string | null; isPublic: boolean };
  workDates: { id: number; workDate: string }[];
  status: string;
  createdAt: string;
};
export type JobInput = {
  workDateIds: number[];
  message: string | null;
  answers: never[];
  requirementsConfirmed: boolean;
};
export type JobReceipt = {
  id: number;
  jobId: number;
  workDateIds: number[];
  message: string | null;
  answers: never[];
  status: 'applied';
  decidedAt: string | null;
  createdAt: string;
};
