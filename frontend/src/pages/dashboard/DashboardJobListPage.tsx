import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import { deleteJob, getDashboardJob, getDashboardJobs } from '../../api/dashboardJobApi';
import DashboardButton from '../../components/DashboardButton';
import { PlusIcon } from '../../components/DashboardIcons';
import { userInfoAtom } from '../../stores/userAtom';
import type { DashboardJobSummary, JobPublishStatus } from '../../types/dashboardJob';
import { formatDateTime } from '../../utils/experienceFormat';
import { publishStatusBadgeClassNames, publishStatusLabels } from '../../utils/jobFormat';

const NEW_JOB_PATH = '/dashboard/jobs/new';

// 公開状態での絞り込み（'all' は全件）
type StatusFilter = JobPublishStatus | 'all';

const statusFilters: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'すべて' },
  { value: 'public', label: '公開中' },
  { value: 'private', label: '非公開' },
  { value: 'draft', label: '下書き' },
  { value: 'suspended', label: '掲載停止中' },
];

function JobRowSkeleton() {
  return (
    <li className="box-border flex animate-pulse flex-col gap-3 rounded-2xl border border-solid border-marche-line bg-white p-5">
      <div className="h-4 w-64 max-w-full rounded bg-marche-canvas" />
      <div className="h-3 w-40 rounded bg-marche-canvas" />
    </li>
  );
}

function JobRow({
  job,
  isPending,
  onDelete,
}: {
  job: DashboardJobSummary;
  isPending: boolean;
  onDelete: (job: DashboardJobSummary) => void;
}) {
  const editPath = `/dashboard/jobs/${job.id}/edit`;
  const applicantsPath = `/dashboard/jobs/${job.id}/applicants`;
  const isSuspended = job.publishStatus === 'suspended';

  return (
    <li className="box-border flex flex-col gap-4 rounded-2xl border border-solid border-marche-line bg-white p-5 lg:flex-row lg:items-center">
      <div className="min-w-0 flex-1">
        <p className="m-0 flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-bold ${publishStatusBadgeClassNames[job.publishStatus]}`}
          >
            {publishStatusLabels[job.publishStatus]}
          </span>
          <span className="text-xs text-marche-muted">更新 {formatDateTime(job.updatedAt)}</span>
        </p>
        {isSuspended ? (
          <p className="m-0 mt-1 font-bold">{job.title}</p>
        ) : (
          <Link
            to={editPath}
            className="mt-1 block font-bold text-marche-ink no-underline hover:underline"
          >
            {job.title}
          </Link>
        )}
        <dl className="m-0 mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs">
          <div className="flex gap-1">
            <dt className="text-marche-muted">応募</dt>
            <dd className="m-0 font-bold">{job.applicationCount}件</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-marche-muted">採用</dt>
            <dd className="m-0 font-bold">
              {job.hiredCount} / {job.slots}人
            </dd>
          </div>
        </dl>
      </div>

      <div className="flex flex-wrap gap-2">
        {!isSuspended && (
          <DashboardButton to={editPath} variant="secondary" size="sm">
            編集
          </DashboardButton>
        )}
        <DashboardButton to={applicantsPath} variant="secondary" size="sm">
          応募者を見る
        </DashboardButton>
        {!isSuspended && (
          <DashboardButton
            variant="danger"
            size="sm"
            disabled={isPending}
            onClick={() => onDelete(job)}
          >
            {isPending ? '削除中…' : '削除'}
          </DashboardButton>
        )}
      </div>
    </li>
  );
}

function DashboardJobListPage() {
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、求人のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const location = useLocation();
  const navigate = useNavigate();
  // 登録・編集画面から戻ってきたときのお知らせ
  const [flash] = useState<string | null>(
    (location.state as { flash?: string } | null)?.flash ?? null,
  );

  // 再読み込みでお知らせが再表示されないよう、履歴の state を消す
  useEffect(() => {
    if (location.state !== null) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  const [jobs, setJobs] = useState<DashboardJobSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [hasLoadError, setHasLoadError] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!canManage) {
      return;
    }

    let isActive = true;

    getDashboardJobs(page, statusFilter === 'all' ? undefined : statusFilter)
      .then((data) => {
        if (!isActive) {
          return;
        }

        // 削除などで今のページが総ページ数を超えた（空になった）ら、最後のページへ戻る
        if (data.items.length === 0 && page > 1 && page > data.totalPages) {
          setJobs(null);
          setPage(Math.max(1, data.totalPages));
          return;
        }

        setJobs(data.items);
        setTotal(data.total);
        setTotalPages(data.totalPages);
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setHasLoadError(true);
        }
      });

    return () => {
      isActive = false;
    };
  }, [canManage, page, statusFilter, reloadCount]);

  const reload = () => {
    setHasLoadError(false);
    setJobs(null);
    setReloadCount((count) => count + 1);
  };

  const changePage = (nextPage: number) => {
    setActionError(null);
    setJobs(null);
    setPage(nextPage);
  };

  const changeFilter = (filter: StatusFilter) => {
    setActionError(null);
    setNotice(null);
    setJobs(null);
    setPage(1);
    setStatusFilter(filter);
  };

  const handleDelete = async (job: DashboardJobSummary) => {
    if (!window.confirm(`「${job.title}」を削除します。勤務日も含めて元に戻せません。よろしいですか？`)) {
      return;
    }

    setActionError(null);
    setNotice(null);
    setPendingId(job.id);

    try {
      // 削除の If-Match に求人の ETag が必要（一覧には含まれないため詳細から取る）
      const { etag } = await getDashboardJob(job.id);
      await deleteJob(job.id, etag);

      setNotice(`「${job.title}」を削除しました。`);
      // 取り直すまでの間も削除した求人が残らないよう、先に一覧から外す
      setJobs((current) => current?.filter(({ id }) => id !== job.id) ?? null);
      // 総件数・総ページ数を合わせるため一覧を取り直す
      setReloadCount((count) => count + 1);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError && error.status === 409) {
        setActionError(
          `「${job.title}」は新着・選考中・採用の応募が残っているため削除できません。選考を終えるか、非公開にしてください。`,
        );
      } else if (error instanceof ApiError && (error.status === 404 || error.status === 412)) {
        setActionError('他の画面で求人が更新・削除されていたため、最新の内容を読み込み直しました。');
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

  if (!canManage) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="m-0 font-serif text-2xl font-bold">求人管理</h1>
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          求人の登録・管理は、生産者登録が承認されると使えるようになります。
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="m-0 font-serif text-2xl font-bold">
          求人管理
          {jobs !== null && (
            <span className="ml-2 text-sm font-normal text-marche-muted">{total}件</span>
          )}
        </h1>
        <DashboardButton to={NEW_JOB_PATH}>
          <PlusIcon className="size-4" />
          求人を登録
        </DashboardButton>
      </header>

      <div role="group" aria-label="公開状態で絞り込み" className="flex flex-wrap gap-2">
        {statusFilters.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            aria-pressed={statusFilter === value}
            onClick={() => changeFilter(value)}
            className={`box-border cursor-pointer rounded-full border border-solid px-4 py-1.5 text-xs font-bold font-[inherit] ${statusFilter === value ? 'border-marche-green bg-marche-green text-white' : 'border-marche-line bg-white text-marche-ink hover:bg-marche-canvas'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {flash !== null && (
        <p
          role="status"
          className="m-0 box-border rounded-2xl border border-solid border-marche-green/30 bg-marche-sage p-4 text-sm font-bold text-marche-green"
        >
          {flash}
        </p>
      )}

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

      {hasLoadError ? (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">求人の一覧を読み込めませんでした。</p>
          <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
          <DashboardButton variant="secondary" onClick={reload} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      ) : jobs === null ? (
        <ul aria-busy="true" className="m-0 flex list-none flex-col gap-3 p-0">
          {Array.from({ length: 3 }, (_, i) => (
            <JobRowSkeleton key={i} />
          ))}
        </ul>
      ) : jobs.length === 0 ? (
        <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-8 text-center">
          {statusFilter === 'all' ? (
            <>
              <p className="m-0 font-bold">まだ求人がありません</p>
              <p className="m-0 mt-1 text-sm text-marche-muted">
                収穫や出荷のお手伝いなど、最初の求人を登録しましょう。
              </p>
              <DashboardButton to={NEW_JOB_PATH} className="mt-4">
                <PlusIcon className="size-4" />
                求人を登録
              </DashboardButton>
            </>
          ) : (
            <p className="m-0 text-sm text-marche-muted">該当する求人はありません。</p>
          )}
        </div>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {jobs.map((job) => (
            <JobRow key={job.id} job={job} isPending={pendingId === job.id} onDelete={handleDelete} />
          ))}
        </ul>
      )}

      {!hasLoadError && jobs !== null && totalPages > 1 && (
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
    </div>
  );
}

export default DashboardJobListPage;
