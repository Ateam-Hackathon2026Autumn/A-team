// 生産者管理画面の求人（/api/v1/dashboard/jobs 以下）の型
// 実API（backend/api/serializers/dashboard/jobs.py）のレスポンスをキャメルケースにしたもの
type JobPublishStatus = 'draft' | 'public' | 'private' | 'suspended';
type JobWritableStatus = Exclude<JobPublishStatus, 'suspended'>;
type JobTermType = 'one_day' | 'short' | 'long';
type JobPayUnit = 'hourly' | 'daily' | 'monthly';
type JobApplicationStatus = 'applied' | 'screening' | 'hired' | 'rejected' | 'withdrawn' | 'completed';
// 生産者が変更できる応募の状態（completed は長期の求人で採用済みの応募だけ）
type JobDecisionStatus = 'screening' | 'hired' | 'rejected' | 'completed';

// 一覧の1件（JobListSerializer）。応募件数・採用人数は含まれない
type DashboardJobSummary = {
  id: number;
  title: string;
  termType: JobTermType;
  payUnit: JobPayUnit;
  payAmount: number;
  periodStart: string | null;
  periodEnd: string | null;
  workHours: string;
  workPlace: string;
  slots: number;
  inexperiencedOk: boolean;
  // アップロード済み画像のキー
  coverImage: string | null;
  publishStatus: JobPublishStatus;
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

// 勤務日（採用人数は含まれない）
type JobWorkDate = {
  id: number;
  workDate: string;
  neededCount: number;
};

// 詳細（JobDetailSerializer）。登録・更新のレスポンスも同じ形
type DashboardJob = DashboardJobSummary & {
  prefectureId: number;
  description: string;
  requirements: string[] | null;
  belongings: string[] | null;
  notes: string[] | null;
  workDates: JobWorkDate[];
};

// 勤務日の入力（既存の勤務日は id を付けて送る。送らなかった勤務日は削除される）
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
  coverImage: string | null;
  publishStatus: JobWritableStatus;
  workDates: JobWorkDateInput[];
};

// 応募者一覧の1件（JobApplicationSerializer）。氏名・電話は応募データの直下に返る
type DashboardJobApplication = {
  id: number;
  userId: number;
  lastName: string;
  firstName: string;
  phone: string | null;
  // 生年月日から計算した年齢（未登録なら null）
  age: number | null;
  message: string | null;
  answers: unknown;
  // 希望した勤務日
  workDates: { id: number; workDate: string }[];
  status: JobApplicationStatus;
  decidedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

type DashboardJobApplicationList = {
  items: DashboardJobApplication[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

// 応募の状態を変えたときのレスポンス（応募者データ全体ではない）
type JobApplicationUpdateResult = {
  id: number;
  status: JobApplicationStatus;
  decidedAt: string | null;
  // 求人全体の採用済み人数と募集人数
  hiredCount: number;
  slots: number;
  // 募集人数を超えて採用したか（超えても採用はできる）
  isOverCapacity: boolean;
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
  DashboardJobApplication,
  DashboardJobApplicationList,
  JobApplicationUpdateResult,
};
