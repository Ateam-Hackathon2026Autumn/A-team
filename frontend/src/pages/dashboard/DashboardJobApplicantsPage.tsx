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
import { userInfoAtom } from '../../stores/userAtom';
import type {
  DashboardJob,
  DashboardJobApplication,
  JobApplicationStatus,
  JobDecisionStatus,
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

// 状態ごとに選べる操作（applied → 選考中・採用・不採用、screening → 採用・不採用）
const actionsByStatus: Partial<Record<JobApplicationStatus, JobDecisionStatus[]>> = {
  applied: ['screening', 'hired', 'rejected'],
  screening: ['hired', 'rejected'],
};

const actionLabels: Record<JobDecisionStatus, string> = {
  screening: '選考中にする',
  hired: '採用する',
  rejected: '不採用にする',
};

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function applicantName(application: DashboardJobApplication): string {
  const { applicant } = application;

  if (!applicant.isActive) {
    return '退会済みの会員';
  }

  const name = `${applicant.lastName ?? ''} ${applicant.firstName ?? ''}`.trim();

  return name === '' ? '（氏名未登録）' : name;
}

// 確認ダイアログの文言（採用・不採用は取り消せない）
function confirmMessage(application: DashboardJobApplication, status: JobDecisionStatus): string {
  const name = applicantName(application);
  const dates = application.workDates.map((day) => formatDate(day.workDate)).join('、');

  if (status === 'hired') {
    return (
      `${name}さんを採用します。` +
      (dates === '' ? '' : `\n希望日（${dates}）のすべてが採用になります。`) +
      '\n採用後は取り消せません。よろしいですか？'
    );
  }

  if (status === 'rejected') {
    return `${name}さんを不採用にします。\n不採用にした後は取り消せません。よろしいですか？`;
  }

  return `${name}さんを選考中にします。よろしいですか？`;
}

function ApplicationRow({
  application,
  isPending,
  disabledActions,
  canHire,
  onDecide,
}: {
  application: DashboardJobApplication;
  isPending: boolean;
  disabledActions: boolean;
  // 公開中の求人だけ採用できる
  canHire: boolean;
  onDecide: (application: DashboardJobApplication, status: JobDecisionStatus) => void;
}) {
  const { applicant } = application;
  const actions = actionsByStatus[application.status] ?? [];
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
        <p className="m-0 font-bold">{applicantName(application)}</p>
        {applicant.isActive && (
          <p className="m-0 mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {applicant.email !== null && (
              <a
                href={`mailto:${applicant.email}`}
                className="break-all text-marche-green no-underline hover:underline"
              >
                {applicant.email}
              </a>
            )}
            {applicant.phone !== null && (
              <a
                href={`tel:${applicant.phone}`}
                className="text-marche-green no-underline hover:underline"
              >
                {applicant.phone}
              </a>
            )}
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
              variant={status === 'hired' ? 'primary' : status === 'rejected' ? 'danger' : 'secondary'}
              disabled={
                isPending ||
                disabledActions ||
                (status === 'hired' && (!applicant.isActive || !canHire))
              }
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
  const { jobId: jobIdParam } = useParams();
  const jobId = Number(jobIdParam);
  const isValidId = Number.isInteger(jobId) && jobId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、求人のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [job, setJob] = useState<DashboardJob | null>(null);
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

  // 求人名と採用人数（見出し用）。取れなくても応募者一覧は表示する
  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    getDashboardJob(jobId)
      .then(({ data }) => {
        if (isActive) {
          setJob(data);
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
          window.location.replace('/signin');
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
    if (!window.confirm(confirmMessage(application, status))) {
      return;
    }

    setActionError(null);
    setNotice(null);
    setPendingId(application.id);

    try {
      const updated = await updateJobApplication(application, status);

      setApplications(
        (current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? null,
      );
      setNotice(`${applicantName(updated)}さんを「${applicationStatusLabels[updated.status]}」にしました。`);
      // 採用人数・残り枠を見出しに反映する
      getDashboardJob(jobId)
        .then(({ data }) => setJob(data))
        .catch(() => {});
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError && (error.status === 404 || error.status === 412)) {
        setActionError('他の画面で応募が更新されていたため、最新の内容を読み込み直しました。もう一度操作してください。');
        reload();
      } else if (error instanceof ApiError && error.errorCode === 'CAPACITY_CONFLICT') {
        setActionError(
          '募集人数または希望日の必要人数に達しているため採用できません。求人の募集人数を増やすか、ほかの応募者の選考を見直してください。',
        );
      } else if (error instanceof ApiError) {
        setActionError(error.message);
      } else {
        setActionError('通信に失敗しました。時間をおいて、もう一度お試しください。');
      }
    } finally {
      setPendingId(null);
    }
  };

  // 採用できるのは公開中の求人だけ。掲載停止中の求人は操作できない
  const isSuspended = job?.publishStatus === 'suspended';

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
          <dl className="m-0 box-border grid grid-cols-2 gap-3 rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-marche-muted">報酬</dt>
              <dd className="m-0 font-bold">{formatPay(job.payUnit, job.payAmount)}</dd>
            </div>
            <div>
              <dt className="text-xs text-marche-muted">採用</dt>
              <dd className="m-0 font-bold">
                {job.hiredCount} / {job.slots}人
              </dd>
            </div>
            <div>
              <dt className="text-xs text-marche-muted">応募</dt>
              <dd className="m-0 font-bold">{job.applicationCount}件</dd>
            </div>
            <div>
              <dt className="text-xs text-marche-muted">勤務日</dt>
              <dd className="m-0 font-bold">
                {job.workDates.length === 0 ? '指定なし' : `${job.workDates.length}日`}
              </dd>
            </div>
          </dl>
        )}

        {job !== null && job.publishStatus !== 'public' && !isSuspended && (
          <p className="m-0 box-border rounded-2xl border border-solid border-marche-orange/40 bg-marche-orange/15 p-4 text-sm">
            この求人は公開されていないため、採用できません。選考中・不採用にはできます。採用する場合は、求人を公開してください。
          </p>
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
                isPending={pendingId === application.id}
                disabledActions={pendingId !== null || isSuspended}
                canHire={job === null || job.publishStatus === 'public'}
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
          {canManage && isValidId && loadError === null && job !== null && !isSuspended && (
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
