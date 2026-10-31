import { useEffect, useState, type ComponentType } from 'react';
import { Link } from 'react-router';
import { useAtomValue } from 'jotai';

import { getDashboardSummary } from '../../api/dashboardApi';
import DashboardButton from '../../components/DashboardButton';
import {
  ChevronRightIcon,
  ExperienceIcon,
  JobIcon,
  PlusIcon,
  ProductIcon,
  SalesIcon,
} from '../../components/DashboardIcons';
import { userInfoAtom } from '../../stores/userAtom';
import type { DashboardSummary } from '../../types/dashboard';

type StatCard = {
  label: string;
  value: string;
  note: string;
  icon: ComponentType<{ className?: string }>;
  // 押したときの遷移先（なしの場合はリンクにしない）
  to?: string;
};

type QuickAction = {
  to: string;
  label: string;
};

// 新規登録の入り口
const quickActions: QuickAction[] = [
  { to: '/dashboard/products/new', label: '商品' },
  { to: '/dashboard/experiences/new', label: '体験' },
  { to: '/dashboard/jobs/new', label: '求人' },
];

const yenFormatter = new Intl.NumberFormat('ja-JP');

function formatYen(amount: number) {
  return `¥${yenFormatter.format(amount)}`;
}

function formatCount(count: number) {
  return `${yenFormatter.format(count)}件`;
}

// 例: 2026年10月30日（木）
function formatToday(date: Date) {
  const { year, month, day, weekday } = Object.fromEntries(
    new Intl.DateTimeFormat('ja-JP', {
      timeZone: 'Asia/Tokyo',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      weekday: 'short',
    })
      .formatToParts(date)
      .map((part) => [part.type, part.value]),
  );

  return `${year}年${month}月${day}日（${weekday}）`;
}

// 例: 9:05
function formatTime(isoString: string) {
  return new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(isoString));
}

// 日本時間の時刻に合わせたあいさつ
function greetingFor(date: Date) {
  const hour = Number(
    new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Tokyo',
      hour: 'numeric',
      hourCycle: 'h23',
    }).format(date),
  );

  if (hour >= 4 && hour < 11) {
    return 'おはようございます';
  }

  if (hour >= 11 && hour < 18) {
    return 'こんにちは';
  }

  return 'こんばんは';
}

function toStatCards(summary: DashboardSummary): StatCard[] {
  return [
    {
      label: '公開中の商品',
      value: formatCount(summary.publishedProductCount),
      note: '商品の管理へ',
      icon: ProductIcon,
      to: '/dashboard/products',
    },
    {
      label: '公開中の体験',
      value: formatCount(summary.publishedExperienceCount),
      note: '体験の管理へ',
      icon: ExperienceIcon,
      to: '/dashboard/experiences',
    },
    {
      label: '公開中の求人',
      value: formatCount(summary.publishedJobCount),
      note: '求人の管理へ',
      icon: JobIcon,
      to: '/dashboard/jobs',
    },
    {
      label: '体験の申込',
      value: formatCount(summary.experienceApplicationCount),
      note: 'これまでの累計',
      icon: ExperienceIcon,
      to: '/dashboard/experiences',
    },
    {
      label: '求人の応募',
      value: formatCount(summary.jobApplicationCount),
      note: 'これまでの累計',
      icon: JobIcon,
      to: '/dashboard/jobs',
    },
    {
      label: '売上（累計・税込）',
      value: formatYen(summary.sales.netAmount),
      note: `返金 ${formatYen(summary.sales.refundedAmount)} を除く`,
      icon: SalesIcon,
    },
  ];
}

function StatCardItem({ card }: { card: StatCard }) {
  const { label, value, note, icon: CardIcon, to } = card;

  const content = (
    <>
      <div className="flex items-center gap-2 text-sm font-bold text-marche-muted">
        <CardIcon className="size-4" />
        {label}
      </div>
      <p className="mt-2 text-xl font-bold tracking-tight sm:text-2xl">{value}</p>
      <p className="mt-1 flex items-center gap-1 text-xs text-marche-muted">
        {note}
        {to !== undefined && <ChevronRightIcon className="size-3.5" />}
      </p>
    </>
  );

  const className =
    'block rounded-2xl border border-marche-line bg-white p-4 transition-colors sm:p-5';

  if (to === undefined) {
    return <div className={className}>{content}</div>;
  }

  return (
    <Link to={to} className={`${className} hover:border-marche-green`}>
      {content}
    </Link>
  );
}

function StatCardSkeleton() {
  return (
    <div className="h-[118px] animate-pulse rounded-2xl border border-marche-line bg-white p-4 sm:p-5">
      <div className="h-4 w-24 rounded bg-marche-canvas" />
      <div className="mt-3 h-7 w-20 rounded bg-marche-canvas" />
      <div className="mt-2 h-3 w-16 rounded bg-marche-canvas" />
    </div>
  );
}

function DashboardHomePage() {
  const userInfo = useAtomValue(userInfoAtom);

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [hasError, setHasError] = useState(false);
  // 再読み込みボタンで値を変えて、集計を取り直す
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    // 画面を離れた後に結果が返ってきても state を更新しない
    let isActive = true;

    async function fetchSummary() {
      try {
        const data = await getDashboardSummary();

        if (isActive) {
          setSummary(data);
        }
      } catch {
        if (isActive) {
          setHasError(true);
        }
      }
    }

    fetchSummary();

    return () => {
      isActive = false;
    };
  }, [reloadCount]);

  const handleReload = () => {
    setHasError(false);
    setSummary(null);
    setReloadCount((count) => count + 1);
  };

  const now = new Date();

  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm text-marche-muted">{formatToday(now)}</p>
        <h1 className="mt-1 text-2xl font-bold">
          {greetingFor(now)}
          {userInfo !== null && `、${userInfo.lastName}さん`}
        </h1>
      </header>

      <section aria-labelledby="dashboard-summary-heading">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="dashboard-summary-heading" className="text-lg font-bold">
            いまの状況
          </h2>
          {summary !== null && (
            <p className="text-xs text-marche-muted">
              {formatTime(summary.asOf)} 時点
            </p>
          )}
        </div>

        {hasError ? (
          <div
            role="alert"
            className="mt-4 rounded-2xl border border-marche-red/30 bg-white p-5 text-sm"
          >
            <p className="font-bold text-marche-red">
              集計を読み込めませんでした。
            </p>
            <p className="mt-1 text-marche-muted">
              時間をおいて、もう一度お試しください。
            </p>
            <DashboardButton
              variant="secondary"
              onClick={handleReload}
              className="mt-4"
            >
              再読み込み
            </DashboardButton>
          </div>
        ) : (
          <div
            aria-busy={summary === null}
            className="mt-4 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3"
          >
            {summary === null
              ? Array.from({ length: 6 }, (_, i) => <StatCardSkeleton key={i} />)
              : toStatCards(summary).map((card) => (
                  <StatCardItem key={card.label} card={card} />
                ))}
          </div>
        )}
      </section>

      <section aria-labelledby="dashboard-actions-heading">
        <h2 id="dashboard-actions-heading" className="text-lg font-bold">
          新しく登録する
        </h2>
        <div className="mt-4 grid grid-cols-3 gap-3">
          {quickActions.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center justify-center gap-2 rounded-2xl border border-dashed border-marche-green/50 bg-white px-4 py-4 font-bold text-marche-green hover:bg-marche-sage hover:text-marche-green"
            >
              <PlusIcon className="size-4" />
              {label}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

export default DashboardHomePage;
