import { useEffect, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import {
  getDashboardExperience,
  getExperienceApplications,
  getExperienceSlots,
} from '../../api/dashboardExperienceApi';
import DashboardButton from '../../components/DashboardButton';
import { controlClassName } from '../../components/DashboardFormParts';
import { userInfoAtom } from '../../stores/userAtom';
import type {
  ExperienceApplication,
  ExperienceApplicationStatus,
  ExperienceSlot,
} from '../../types/experience';
import {
  applicationStatusLabels,
  formatDateTime,
  formatYen,
} from '../../utils/experienceFormat';

const EXPERIENCE_LIST_PATH = '/dashboard/experiences';

const applicationStatusBadgeClassNames: Record<ExperienceApplicationStatus, string> = {
  applied: 'bg-marche-orange/20 text-marche-ink',
  confirmed: 'bg-marche-sage text-marche-green',
  canceled: 'bg-marche-line text-marche-muted',
  attended: 'bg-marche-green text-white',
};

const statusOptions: ExperienceApplicationStatus[] = ['applied', 'confirmed', 'attended', 'canceled'];

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

// 参加人数（例: 3人（大人2・子ども1））
function formatPeople(application: ExperienceApplication): string {
  const parts = [`大人${application.adultCount}`];

  if (application.childCount > 0) {
    parts.push(`子ども${application.childCount}`);
  }

  if (application.infantCount > 0) {
    parts.push(`未就学児${application.infantCount}`);
  }

  const total = application.adultCount + application.childCount + application.infantCount;

  return `${total}人（${parts.join('・')}）`;
}

function ApplicationRow({ application }: { application: ExperienceApplication }) {
  const { user } = application;
  const isWithdrawn = !user.isActive;
  const memberName =
    user.lastName === null && user.firstName === null
      ? null
      : `${user.lastName ?? ''} ${user.firstName ?? ''}`.trim();
  const isCanceled = application.status === 'canceled';

  return (
    <li
      className={`box-border flex flex-col gap-3 rounded-2xl border border-solid border-marche-line p-5 ${isCanceled ? 'bg-marche-canvas' : 'bg-white'}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-bold ${applicationStatusBadgeClassNames[application.status]}`}
        >
          {applicationStatusLabels[application.status]}
        </span>
        <span className="text-xs text-marche-muted">予約番号 {application.reservationNo}</span>
        <span className="text-xs text-marche-muted">
          申込 {formatDateTime(application.createdAt)}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div className="min-w-0">
          <p className="m-0 font-bold">
            {isWithdrawn ? '退会済みの会員' : (application.representativeName ?? memberName ?? '—')}
            {!isWithdrawn &&
              memberName !== null &&
              application.representativeName !== null &&
              application.representativeName !== memberName && (
                <span className="ml-2 text-xs font-normal text-marche-muted">
                  （会員：{memberName}）
                </span>
              )}
          </p>
          <p className="m-0 mt-1 text-sm">
            {formatDateTime(application.slot.startAt)} の回 ・ {formatPeople(application)}
          </p>
          {application.phone !== null && (
            <p className="m-0 mt-1 text-sm">
              電話：
              <a
                href={`tel:${application.phone}`}
                className="text-marche-green no-underline hover:underline"
              >
                {application.phone}
              </a>
            </p>
          )}
        </div>
        <p className="m-0 text-left text-lg font-bold sm:text-right">
          {formatYen(application.totalAmount)}
          <span className="block text-xs font-normal text-marche-muted">合計（税込）</span>
        </p>
      </div>

      {application.message !== null && (
        <p className="m-0 whitespace-pre-wrap rounded-xl bg-marche-canvas p-3 text-sm">
          {application.message}
        </p>
      )}
    </li>
  );
}

function DashboardExperienceParticipantsPage() {
  const { experienceId: experienceIdParam } = useParams();
  const experienceId = Number(experienceIdParam);
  const isValidId = Number.isInteger(experienceId) && experienceId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、体験のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [title, setTitle] = useState<string | null>(null);
  const [slots, setSlots] = useState<ExperienceSlot[]>([]);
  const [applications, setApplications] = useState<ExperienceApplication[] | null>(null);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [slotFilter, setSlotFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<ExperienceApplicationStatus | ''>('');
  const [loadError, setLoadError] = useState<'notFound' | 'failed' | null>(null);
  const [reloadCount, setReloadCount] = useState(0);

  // 体験名と予約枠（絞り込みの選択肢）。取れなくても申込者一覧は表示する
  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    getDashboardExperience(experienceId)
      .then(({ data }) => {
        if (isActive) {
          setTitle(data.title);
        }
      })
      .catch(() => {});

    getExperienceSlots(experienceId)
      .then((data) => {
        if (isActive) {
          setSlots(data.items);
        }
      })
      .catch(() => {});

    return () => {
      isActive = false;
    };
  }, [canManage, isValidId, experienceId]);

  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    getExperienceApplications(experienceId, {
      page,
      slotId: slotFilter === '' ? undefined : Number(slotFilter),
      status: statusFilter === '' ? undefined : statusFilter,
    })
      .then((data) => {
        if (isActive) {
          setApplications(data.items);
          setTotal(data.total);
          setTotalPages(data.totalPages);
        }
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setLoadError(
            error instanceof ApiError && error.status === 404 ? 'notFound' : 'failed',
          );
        }
      });

    return () => {
      isActive = false;
    };
  }, [canManage, isValidId, experienceId, page, slotFilter, statusFilter, reloadCount]);

  const reload = () => {
    setLoadError(null);
    setApplications(null);
    setReloadCount((count) => count + 1);
  };

  const changeFilter = (change: () => void) => {
    setApplications(null);
    setPage(1);
    change();
  };

  const changePage = (nextPage: number) => {
    setApplications(null);
    setPage(nextPage);
  };

  const renderBody = () => {
    if (!canManage) {
      return (
        <Notice>体験の登録・管理は、生産者登録が承認されると使えるようになります。</Notice>
      );
    }

    if (!isValidId || loadError === 'notFound') {
      return (
        <Notice>
          <p className="m-0 font-bold">体験が見つかりません。</p>
          <p className="m-0 mt-1 text-marche-muted">
            削除されたか、URL が間違っている可能性があります。
          </p>
          <DashboardButton to={EXPERIENCE_LIST_PATH} variant="secondary" className="mt-4">
            体験管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    return (
      <>
        <div className="flex flex-wrap gap-3">
          <label className="flex min-w-0 flex-col gap-1 text-xs font-bold">
            予約枠
            <select
              value={slotFilter}
              onChange={(event) => {
                const value = event.target.value;
                changeFilter(() => setSlotFilter(value));
              }}
              className={`${controlClassName} border-marche-line text-sm font-normal`}
            >
              <option value="">すべての回</option>
              {slots.map((slot) => (
                <option key={slot.id} value={slot.id}>
                  {formatDateTime(slot.startAt)}（予約 {slot.reservedCount}/{slot.capacity}人）
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-xs font-bold">
            状態
            <select
              value={statusFilter}
              onChange={(event) => {
                const value = event.target.value as ExperienceApplicationStatus | '';
                changeFilter(() => setStatusFilter(value));
              }}
              className={`${controlClassName} border-marche-line text-sm font-normal`}
            >
              <option value="">すべて</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {applicationStatusLabels[status]}
                </option>
              ))}
            </select>
          </label>
        </div>

        {loadError === 'failed' ? (
          <div
            role="alert"
            className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
          >
            <p className="m-0 font-bold text-marche-red">申込者を読み込めませんでした。</p>
            <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
            <DashboardButton variant="secondary" onClick={reload} className="mt-4">
              再読み込み
            </DashboardButton>
          </div>
        ) : applications === null ? (
          <ul aria-busy="true" className="m-0 flex list-none flex-col gap-3 p-0">
            {Array.from({ length: 3 }, (_, i) => (
              <li
                key={i}
                className="box-border h-28 animate-pulse rounded-2xl border border-solid border-marche-line bg-white"
              />
            ))}
          </ul>
        ) : applications.length === 0 ? (
          <Notice>
            <p className="m-0 text-center text-marche-muted">
              {slotFilter === '' && statusFilter === ''
                ? 'まだ申込はありません。'
                : '条件に合う申込はありません。'}
            </p>
          </Notice>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {applications.map((application) => (
              <ApplicationRow key={application.id} application={application} />
            ))}
          </ul>
        )}

        {loadError === null && applications !== null && totalPages > 1 && (
          <nav aria-label="ページ移動" className="flex items-center justify-center gap-4">
            <DashboardButton
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => changePage(page - 1)}
            >
              前へ
            </DashboardButton>
            <span className="text-sm text-marche-muted">
              {page} / {totalPages}
            </span>
            <DashboardButton
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => changePage(page + 1)}
            >
              次へ
            </DashboardButton>
          </nav>
        )}
      </>
    );
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <header>
        <Link
          to={EXPERIENCE_LIST_PATH}
          className="text-sm font-bold text-marche-green no-underline hover:underline"
        >
          ← 体験管理に戻る
        </Link>
        <h1 className="m-0 font-serif mt-2 text-2xl font-bold">
          体験申込者一覧
          {applications !== null && loadError === null && (
            <span className="ml-2 text-sm font-normal text-marche-muted">{total}件</span>
          )}
        </h1>
        {title !== null && <p className="m-0 mt-1 text-sm text-marche-muted">{title}</p>}
        <p className="m-0 mt-2 text-xs text-marche-muted">
          連絡先は体験の案内・連絡のためだけに使ってください。
        </p>
      </header>

      {renderBody()}
    </div>
  );
}

export default DashboardExperienceParticipantsPage;
