import type {
  ExperienceApplicationStatus,
  ExperiencePublishStatus,
  ExperienceSlotStatus,
} from '../types/experience';

// 体験の管理画面で使う表示用の変換

const yenFormatter = new Intl.NumberFormat('ja-JP');

function formatYen(amount: number): string {
  return `¥${yenFormatter.format(amount)}`;
}

// 日時は日本時間で表示する（例: 2026/11/15(日) 10:00）
const dateTimeFormatter = new Intl.DateTimeFormat('ja-JP', {
  timeZone: 'Asia/Tokyo',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  weekday: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

function formatDateTime(iso: string): string {
  const date = new Date(iso);

  if (Number.isNaN(date.getTime())) {
    return iso;
  }

  const parts = Object.fromEntries(
    dateTimeFormatter.formatToParts(date).map(({ type, value }) => [type, value]),
  );

  return `${parts.year}/${parts.month}/${parts.day}(${parts.weekday}) ${parts.hour}:${parts.minute}`;
}

// 所要時間（例: 180 → 3時間、90 → 1時間30分）
function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;

  if (hours === 0) {
    return `${rest}分`;
  }

  return rest === 0 ? `${hours}時間` : `${hours}時間${rest}分`;
}

// 日付（YYYY-MM-DD）と時刻（HH:MM）から日本時間の日時文字列を作る
function toJstDateTime(date: string, time: string): string {
  return `${date}T${time}:00+09:00`;
}

// 日時文字列を日本時間の日付・時刻（入力欄の値）に分ける
function splitJstDateTime(iso: string): { date: string; time: string } {
  const date = new Date(iso);
  const jst = new Date(date.getTime() + 9 * 60 * 60 * 1000).toISOString();

  return { date: jst.slice(0, 10), time: jst.slice(11, 16) };
}

const publishStatusLabels: Record<ExperiencePublishStatus, string> = {
  draft: '下書き',
  public: '公開中',
  private: '非公開',
  suspended: '掲載停止中',
};

const publishStatusBadgeClassNames: Record<ExperiencePublishStatus, string> = {
  draft: 'bg-marche-canvas text-marche-muted',
  public: 'bg-marche-sage text-marche-green',
  private: 'bg-marche-line text-marche-ink',
  suspended: 'bg-marche-red/10 text-marche-red',
};

const slotStatusLabels: Record<ExperienceSlotStatus, string> = {
  open: '受付中',
  closed: '受付停止',
  canceled: '中止',
};

const applicationStatusLabels: Record<ExperienceApplicationStatus, string> = {
  applied: '新着（未確認）',
  confirmed: '確定',
  canceled: 'キャンセル',
  attended: '参加済み',
};

export {
  applicationStatusLabels,
  formatDateTime,
  formatDuration,
  formatYen,
  publishStatusBadgeClassNames,
  publishStatusLabels,
  slotStatusLabels,
  splitJstDateTime,
  toJstDateTime,
};
