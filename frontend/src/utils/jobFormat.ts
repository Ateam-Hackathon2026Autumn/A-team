import type {
  JobApplicationStatus,
  JobPayUnit,
  JobPublishStatus,
  JobTermType,
} from '../types/dashboardJob';

// 求人の管理画面で使う表示用の変換・上限

// API の仕様に合わせた上限（画面とモックAPIで共通に使う）
const JOB_MAX_WORK_DATES = 100;
const JOB_MAX_LIST_ITEMS = 50;
const JOB_MAX_LIST_ITEM_LENGTH = 500;

const publishStatusLabels: Record<JobPublishStatus, string> = {
  draft: '下書き',
  public: '公開中',
  private: '非公開',
  suspended: '掲載停止中',
};

const publishStatusBadgeClassNames: Record<JobPublishStatus, string> = {
  draft: 'bg-marche-canvas text-marche-muted',
  public: 'bg-marche-sage text-marche-green',
  private: 'bg-marche-line text-marche-ink',
  suspended: 'bg-marche-red/10 text-marche-red',
};

// 公開側の求人一覧（JobCard）と同じ表記にする
const termTypeLabels: Record<JobTermType, string> = {
  one_day: '1日',
  short: '短期',
  long: '長期',
};

const payUnitLabels: Record<JobPayUnit, string> = {
  hourly: '時給',
  daily: '日給',
  monthly: '月給',
};

const applicationStatusLabels: Record<JobApplicationStatus, string> = {
  applied: '新着（未対応）',
  screening: '選考中',
  hired: '採用',
  rejected: '不採用',
  withdrawn: '辞退',
  completed: '勤務完了',
};

const applicationStatusBadgeClassNames: Record<JobApplicationStatus, string> = {
  applied: 'bg-marche-orange/20 text-marche-ink',
  screening: 'bg-marche-canvas text-marche-ink',
  hired: 'bg-marche-green text-white',
  rejected: 'bg-marche-line text-marche-muted',
  withdrawn: 'bg-marche-line text-marche-muted',
  completed: 'bg-marche-sage text-marche-green',
};

const yenFormatter = new Intl.NumberFormat('ja-JP');

// 報酬（例: 時給 ¥1,200）
function formatPay(payUnit: JobPayUnit, payAmount: number): string {
  return `${payUnitLabels[payUnit]} ¥${yenFormatter.format(payAmount)}`;
}

const weekdays = ['日', '月', '火', '水', '木', '金', '土'];

// 日付（YYYY-MM-DD）を表示する（例: 2026/11/20(金)）。曜日は日付そのものから求める
function formatDate(date: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);

  if (match === null) {
    return date;
  }

  const [, year, month, day] = match;
  const weekday =
    weekdays[new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))).getUTCDay()];

  return `${year}/${month}/${day}(${weekday})`;
}

// 募集期間（例: 2026/11/01(日)〜2026/12/15(火)。指定なしは「期限なし」）
function formatPeriod(periodStart: string | null, periodEnd: string | null): string {
  if (periodStart === null && periodEnd === null) {
    return '期限なし';
  }

  const start = periodStart === null ? '' : formatDate(periodStart);
  const end = periodEnd === null ? '' : formatDate(periodEnd);

  return `${start}〜${end}`;
}

// 日本時間の今日（YYYY-MM-DD）。勤務日・募集期間の比較に使う
function todayInJapan(): string {
  return new Date(Date.now() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

export {
  JOB_MAX_LIST_ITEMS,
  JOB_MAX_LIST_ITEM_LENGTH,
  JOB_MAX_WORK_DATES,
  applicationStatusBadgeClassNames,
  applicationStatusLabels,
  formatDate,
  formatPay,
  formatPeriod,
  payUnitLabels,
  publishStatusBadgeClassNames,
  publishStatusLabels,
  termTypeLabels,
  todayInJapan,
};
