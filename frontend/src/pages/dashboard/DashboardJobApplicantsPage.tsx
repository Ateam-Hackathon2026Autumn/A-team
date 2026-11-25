import { useEffect, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import {
  getDashboardJob,
  getJobApplications,
  updateJobApplication,
} from '../../api/dashboardJobApi';
import DashboardButton from '../../components/DashboardButton';
import { controlClassName } from '../../components/DashboardFormParts';
import { useSigninRedirect } from '../../hooks/useSigninRedirect';
import { userInfoAtom } from '../../stores/userAtom';
import type {
  DashboardJob,
  DashboardJobApplication,
  JobApplicationStatus,
  JobDecisionStatus,
  JobTermType,
} from '../../types/dashboardJob';
import { formatDateTime } from '../../utils/experienceFormat';
import {
  applicationStatusBadgeClassNames,
  applicationStatusLabels,
  formatDate,
  formatPay,
} from '../../utils/jobFormat';

const JOB_LIST_PATH = '/dashboard/jobs';

const statusOptions: JobApplicationStatus[] = [
  'applied',
  'screening',
  'hired',
  'rejected',
  'withdrawn',
  'completed',
];

const actionLabels: Record<JobDecisionStatus, string> = {
  screening: '選考中にする',
  hired: '採用する',
  rejected: '不採用にする',
  completed: '勤務完了にする',
};

// 状態ごとに選べる操作（applied → 選考中・採用・不採用、screening → 採用・不採用、長期の hired → 勤務完了）
function actionsFor(status: JobApplicationStatus, termType: JobTermType | null): JobDecisionStatus[] {
  if (status === 'applied') {
    return ['screening', 'hired', 'rejected'];
  }

  if (status === 'screening') {
    return ['hired', 'rejected'];
  }

  return status === 'hired' && termType === 'long' ? ['completed'] : [];
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function applicantName(application: DashboardJobApplication): string {
  const name = `${application.lastName} ${application.firstName}`.trim();

  return name === '' ? '（氏名未登録）' : name;
}

// 採用人数と募集人数（見出し用）
type Capacity = { hiredCount: number; slots: number };

// 確認ダイアログの文言（採用・不採用は取り消せない）
function confirmMessage(
  application: DashboardJobApplication,
  status: JobDecisionStatus,
  capacity: Capacity | null,
): string {
  const name = applicantName(application);

  if (status === 'hired') {
    // 募集人数を超えても採用はできるため、超える場合は確認で知らせる
    const isFull = capacity !== null && capacity.hiredCount >= capacity.slots;

    return (
      `${name}さんを採用します。` +
      (isFull ? `\n募集人数（${capacity.slots}人）を超えての採用になります。` : '') +
      '\n採用・不採用は応募者に通知され、後から取り消せません。よろしいですか？'
    );
  }

  if (status === 'rejected') {
    return `${name}さんを不採用にします。\n応募者に通知され、後から取り消せません。よろしいですか？`;
  }

  if (status === 'completed') {
    return `${name}さんの勤務を完了にします。後から戻せません。よろしいですか？`;
  }

  return `${name}さんを選考中にします。よろしいですか？`;
}

function ApplicationRow({
  application,
  termType,
  isPending,
  disabledActions,
  onDecide,
}: {
  application: DashboardJobApplication;
  // 求人を読み込めていないときは null（勤務完了の操作は出さない）
  termType: JobTermType | null;
  isPending: boolean;
  disabledActions: boolean;
  onDecide: (application: DashboardJobApplication, status: JobDecisionStatus) => void;
}) {
  const actions = actionsFor(application.status, termType);
  const isClosed = ['rejected', 'withdrawn'].includes(application.status);

  return (
    <li
      className={`box-border flex flex-col gap-3 rounded-2xl border border-solid border-marche-line p-5 ${isClosed ? 'bg-marche-canvas' : 'bg-white'}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-bold ${applicationStatusBadgeClassNames[application.status]}`}
        >
          {applicationStatusLabels[application.status]}
        </span>
        <span className="text-xs text-marche-muted">応募 {formatDateTime(application.createdAt)}</span>
        {application.decidedAt !== null && (
          <span className="text-xs text-marche-muted">決定 {formatDateTime(application.decidedAt)}</span>
        )}
      </div>

      <div className="min-w-0">
        <p className="m-0 font-bold">
          {applicantName(application)}
          {application.age !== null && (
            <span className="ml-2 text-sm font-normal text-marche-muted">{application.age}歳</span>
          )}
        </p>
        {application.phone !== null && application.phone !== '' && (
          <p className="m-0 mt-1 text-sm">
            <a
              href={`tel:${application.phone}`}
              className="text-marche-green no-underline hover:underline"
            >
              {application.phone}
            </a>
          </p>
        )}
      </div>

      <div className="text-sm">
        <p className="m-0 text-xs font-bold text-marche-muted">希望日</p>
        {application.workDates.length === 0 ? (
          <p className="m-0 mt-1">日程は相談（勤務日の指定なし）</p>
        ) : (
          <ul className="m-0 mt-1 flex list-none flex-wrap gap-2 p-0">
            {application.workDates.map((day) => (
              <li key={day.id} className="rounded-full bg-marche-sage px-3 py-1 text-xs font-bold">
                {formatDate(day.workDate)}
              </li>
            ))}
          </ul>
        )}
      </div>

      {application.message !== null && application.message !== '' && (
        <p className="m-0 whitespace-pre-wrap rounded-xl bg-marche-canvas p-3 text-sm">
          {application.message}
        </p>
      )}

      {actions.length > 0 && (
        <div className="flex flex-wrap gap-2 border-0 border-t border-solid border-marche-line pt-3">
          {actions.map((status) => (
            <DashboardButton
              key={status}
              size="sm"
              variant={status === 'rejected' ? 'danger' : status === 'screening' ? 'secondary' : 'primary'}
              disabled={isPending || disabledActions}
              onClick={() => onDecide(application, status)}
            >
              {isPending ? '更新中…' : actionLabels[status]}
            </DashboardButton>
          ))}
        </div>
      )}
    </li>
  );
}

function DashboardJobApplicantsPage() {
  const redirectToSignin = useSigninRedirect();
  const { jobId: jobIdParam } = useParams();
  const jobId = Number(jobIdParam);
  const isValidId = Number.isInteger(jobId) && jobId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、求人のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [job, setJob] = useState<DashboardJob | null>(null);
  const [capacity, setCapacity] = useState<Capacity | null>(null);
  const [applications, setApplications] = useState<DashboardJobApplication[] | null>(null);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<JobApplicationStatus | ''>('');
  const [loadError, setLoadError] = useState<'notFound' | 'failed' | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // 求人名と採用人数（見出し用）。採用人数には勤務完了も含む
  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    getDashboardJob(jobId)
      .then((data) => {
        if (isActive) {
          setJob(data);
          setCapacity({ hiredCount: data.hiredCount, slots: data.slots });
        }
      })
      .catch(() => {});

    return () => {
      isActive = false;
    };
  }, [canManage, isValidId, jobId, reloadCount]);

  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    getJobApplications(jobId, {
      page,
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
          redirectToSignin();
          return;
        }

        if (isActive) {
          setLoadError(error instanceof ApiError && error.status === 404 ? 'notFound' : 'failed');
        }
      });

    return () => {
      isActive = false;
    };
  }, [canManage, isValidId, jobId, page, statusFilter, reloadCount]);

  const reload = () => {
    setLoadError(null);
    setApplications(null);
    setReloadCount((count) => count + 1);
  };

  const changeFilter = (value: JobApplicationStatus | '') => {
    setActionError(null);
    setNotice(null);
    setApplications(null);
    setPage(1);
    setStatusFilter(value);
  };

  const changePage = (nextPage: number) => {
    setActionError(null);
    setApplications(null);
    setPage(nextPage);
  };

  const handleDecide = async (application: DashboardJobApplication, status: JobDecisionStatus) => {
    if (!window.confirm(confirmMessage(application, status, capacity))) {
      return;
    }

    setActionError(null);
    setNotice(null);
    setPendingId(application.id);

    try {
      // レスポンスは更新結果だけなので、表示中の応募データに状態と決定日時を反映する
      const result = await updateJobApplication(jobId, application.id, status);

      setApplications(
        (current) =>
          current?.filter((item) => statusFilter === '' || item.id !== result.id || result.status === statusFilter).map((item) =>
            item.id === result.id ? { ...item, status: result.status, decidedAt: result.decidedAt } : item,
          ) ?? null,
      );
      if (statusFilter !== '' && result.status !== statusFilter) setTotal((count) => Math.max(0, count - 1));
      const success = `${applicantName(application)}さんを「${applicationStatusLabels[result.status]}」にしました。`;
      setNotice(success);
      getDashboardJob(jobId)
        .then((currentJob) => {
          setCapacity({ hiredCount: currentJob.hiredCount, slots: currentJob.slots });
          setNotice(success + (currentJob.hiredCount > currentJob.slots
            ? `採用人数（${currentJob.hiredCount}人）が募集人数（${currentJob.slots}人）を超えています。`
            : ''));
        })
        .catch(() => {});
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        redirectToSignin();
        return;
      }

      // 404（応募が見つからない）・409（今の状態からは変えられない）は、他の画面で先に変わっている
      if (error instanceof ApiError && (error.status === 404 || error.status === 409)) {
        setActionError(
          'この応募は他の画面で状態が変わっていたため、最新の内容を読み込み直しました。もう一度確認してください。',
        );
        reload();
      } else if (error instanceof ApiError) {
        setActionError(error.message);
      } else {
        setActionError('通信に失敗しました。時間をおいて、もう一度お試しください。');
      }
    } finally {
      setPendingId(null);
    }
  };

  const renderBody = () => {
    if (!canManage) {
      return <Notice>求人の登録・管理は、生産者登録が承認されると使えるようになります。</Notice>;
    }

    if (!isValidId || loadError === 'notFound') {
      return (
        <Notice>
          <p className="m-0 font-bold">求人が見つかりません。</p>
          <p className="m-0 mt-1 text-marche-muted">削除されたか、URL が間違っている可能性があります。</p>
          <DashboardButton to={JOB_LIST_PATH} variant="secondary" className="mt-4">
            求人管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    return (
      <>
        {job !== null && (
          <dl className="m-0 box-border grid grid-cols-2 gap-3 rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-marche-muted">報酬</dt>
              <dd className="m-0 font-bold">{formatPay(job.payUnit, job.payAmount)}</dd>
            </div>
            <div>
              <dt className="text-xs text-marche-muted">採用 / 募集</dt>
              <dd
                className={`m-0 font-bold ${capacity !== null && capacity.hiredCount > capacity.slots ? 'text-marche-red' : ''}`}
              >
                {capacity === null ? '—' : `${capacity.hiredCount} / ${capacity.slots}人`}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-marche-muted">勤務日</dt>
              <dd className="m-0 font-bold">
                {job.workDates.length === 0 ? '指定なし' : `${job.workDates.length}日`}
              </dd>
            </div>
          </dl>
        )}

        <label className="flex min-w-0 max-w-xs flex-col gap-1 text-xs font-bold">
          状態
          <select
            value={statusFilter}
            onChange={(event) => changeFilter(event.target.value as JobApplicationStatus | '')}
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

        {notice !== null && (
          <p
            role="status"
            className="m-0 box-border rounded-2xl border border-solid border-marche-green/30 bg-marche-sage p-4 text-sm font-bold text-marche-green"
          >
            {notice}
          </p>
        )}

        {actionError !== null && (
          <p
            role="alert"
            className="m-0 box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-4 text-sm font-bold text-marche-red"
          >
            {actionError}
          </p>
        )}

        {loadError === 'failed' ? (
          <div
            role="alert"
            className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
          >
            <p className="m-0 font-bold text-marche-red">応募者を読み込めませんでした。</p>
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
                className="box-border h-36 animate-pulse rounded-2xl border border-solid border-marche-line bg-white"
              />
            ))}
          </ul>
        ) : applications.length === 0 ? (
          <Notice>
            <p className="m-0 text-center text-marche-muted">
              {statusFilter === '' ? 'まだ応募はありません。' : '条件に合う応募はありません。'}
            </p>
          </Notice>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {applications.map((application) => (
              <ApplicationRow
                key={application.id}
                application={application}
                termType={job?.termType ?? null}
                isPending={pendingId === application.id}
                disabledActions={pendingId !== null}
                onDecide={handleDecide}
              />
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
          to={JOB_LIST_PATH}
          className="text-sm font-bold text-marche-green no-underline hover:underline"
        >
          ← 求人管理に戻る
        </Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="m-0 font-serif text-2xl font-bold">
            求人応募者一覧
            {applications !== null && loadError === null && (
              <span className="ml-2 text-sm font-normal text-marche-muted">{total}件</span>
            )}
          </h1>
          {canManage && isValidId && loadError === null && job !== null && (
            <DashboardButton to={`/dashboard/jobs/${jobId}/edit`} variant="secondary" size="sm">
              求人を編集
            </DashboardButton>
          )}
        </div>
        {job !== null && <p className="m-0 mt-1 text-sm text-marche-muted">{job.title}</p>}
        <p className="m-0 mt-2 text-xs text-marche-muted">
          連絡先は採用の連絡のためだけに使ってください。採用・不採用は応募者に通知され、後から取り消せません。
        </p>
      </header>

      {renderBody()}
    </div>
  );
}

export default DashboardJobApplicantsPage;
