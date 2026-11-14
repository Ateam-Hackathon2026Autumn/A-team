// 生産者管理画面の求人（/api/v1/dashboard/jobs 以下）の型
type JobPublishStatus = 'draft' | 'public' | 'private' | 'suspended';
type JobWritableStatus = Exclude<JobPublishStatus, 'suspended'>;
type JobTermType = 'one_day' | 'short' | 'long';
type JobPayUnit = 'hourly' | 'daily' | 'monthly';
type JobApplicationStatus = 'applied' | 'screening' | 'hired' | 'rejected' | 'withdrawn' | 'completed';
type JobDecisionStatus = 'screening' | 'hired' | 'rejected';
type DashboardJobSummary = {
  id: number;
  title: string;
  publishStatus: JobPublishStatus;
  slots: number;
  applicationCount: number;
  hiredCount: number;
  createdAt: string;
  updatedAt: string;
};
type DashboardJobList = {
  items: DashboardJobSummary[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
type JobWorkDate = {
  id: number;
  workDate: string;
  neededCount: number;
  hiredCount: number;
  remainingCount: number;
};
type DashboardJob = {
  id: number;
  producerId: number;
  title: string;
  prefectureId: number;
  termType: JobTermType;
  payUnit: JobPayUnit;
  payAmount: number;
  periodStart: string | null;
  periodEnd: string | null;
  workHours: string;
  workPlace: string;
  slots: number;
  description: string;
  requirements: string[] | null;
  belongings: string[] | null;
  notes: string[] | null;
  inexperiencedOk: boolean;
  coverImageKey: string | null;
  publishStatus: JobPublishStatus;
  workDates: JobWorkDate[];
  applicationCount: number;
  hiredCount: number;
  createdAt: string;
  updatedAt: string;
};
type JobWorkDateInput = {
  id?: number;
  workDate: string;
  neededCount: number;
};
type JobInput = {
  title: string;
  prefectureId: number;
  termType: JobTermType;
  payUnit: JobPayUnit;
  payAmount: number;
  periodStart: string | null;
  periodEnd: string | null;
  workHours: string;
  workPlace: string;
  slots: number;
  description: string;
  requirements: string[] | null;
  belongings: string[] | null;
  notes: string[] | null;
  inexperiencedOk: boolean;
  coverImageKey: string | null;
  publishStatus: JobWritableStatus;
  workDates: JobWorkDateInput[];
};
type JobWriteResult = {
  id: number;
  producerId: number;
  publishStatus: JobPublishStatus;
  createdAt: string;
  updatedAt: string;
};
type JobApplicant = {
  id: number;
  lastName: string | null;
  firstName: string | null;
  email: string | null;
  phone: string | null;
  isActive: boolean;
};
type DashboardJobApplication = {
  id: number;
  jobId: number;
  applicant: JobApplicant;
  message: string | null;
  answers: unknown[] | null;
  workDates: { id: number; workDate: string }[];
  status: JobApplicationStatus;
  decidedAt: string | null;
  createdAt: string;
  updatedAt: string;
  etag: string;
};
type DashboardJobApplicationList = {
  items: DashboardJobApplication[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type {
  JobPublishStatus,
  JobWritableStatus,
  JobTermType,
  JobPayUnit,
  JobApplicationStatus,
  JobDecisionStatus,
  DashboardJobSummary,
  DashboardJobList,
  JobWorkDate,
  DashboardJob,
  JobWorkDateInput,
  JobInput,
  JobWriteResult,
  JobApplicant,
  DashboardJobApplication,
  DashboardJobApplicationList
};
