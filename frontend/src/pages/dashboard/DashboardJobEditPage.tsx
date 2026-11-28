import { useEffect, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useAtomValue } from 'jotai';

import { useScrollDashboardToTop } from '../../Layouts/dashboardScroll';
import ApiError from '../../api/apiError';
import {
  getAllJobApplications,
  getDashboardJob,
  updateJob,
} from '../../api/dashboardJobApi';
import DashboardButton from '../../components/DashboardButton';
import DashboardJobForm from '../../components/DashboardJobForm';
import { useSigninRedirect } from '../../hooks/useSigninRedirect';
import { userInfoAtom } from '../../stores/userAtom';
import type { DashboardJob, JobInput } from '../../types/dashboardJob';

const JOB_LIST_PATH = '/dashboard/jobs';

// 保存中に応募が入り、希望者がいる勤務日を削除・変更しようとした（409）ときの案内
const WORK_DATE_LOCKED_MESSAGE =
  '応募者が希望している勤務日は、削除や日付の変更ができません。最新の内容を読み込み直しました。もう一度編集して保存してください。';

// 読み込んだ求人と、応募者が希望している勤務日・応募件数
type Loaded = {
  job: DashboardJob;
  lockedWorkDateIds: ReadonlySet<number>;
  applicationCount: number;
};

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function DashboardJobEditPage() {
  const scrollToTop = useScrollDashboardToTop();
  const redirectToSignin = useSigninRedirect();
  const navigate = useNavigate();
  const { jobId: jobIdParam } = useParams();
  const jobId = Number(jobIdParam);
  const isValidId = Number.isInteger(jobId) && jobId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、求人のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [loadError, setLoadError] = useState<'notFound' | 'failed' | null>(
    null,
  );
  const [notice, setNotice] = useState<string | null>(null);
  // 読み込み直すたびに増やす（フォームも作り直して最新の内容にする）
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    // 求人の詳細には応募の情報がないため、応募者一覧から希望者がいる勤務日を集める
    Promise.all([getDashboardJob(jobId), getAllJobApplications(jobId)])
      .then(([job, applications]) => {
        if (isActive) {
          setLoaded({
            job,
            lockedWorkDateIds: new Set(
              applications.flatMap((application) =>
                application.workDates.map((day) => day.id),
              ),
            ),
            applicationCount: applications.length,
          });
        }
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          redirectToSignin();
          return;
        }

        if (isActive) {
          setLoadError(
            error instanceof ApiError && error.status === 404
              ? 'notFound'
              : 'failed',
          );
        }
      });

    return () => {
      isActive = false;
    };
  }, [canManage, isValidId, jobId, reloadCount, redirectToSignin]);

  const reload = (message: string | null = null) => {
    setNotice(message);
    setLoadError(null);
    setLoaded(null);
    setReloadCount((count) => count + 1);
    scrollToTop();
  };

  const handleSubmit = async (input: JobInput) => {
    if (loaded === null) {
      return;
    }

    setNotice(null);

    // 掲載停止中の求人は公開状態を変えられないため、publishStatus を送らない
    const body: Partial<JobInput> =
      loaded.job.publishStatus === 'suspended'
        ? Object.fromEntries(
            Object.entries(input).filter(([name]) => name !== 'publishStatus'),
          )
        : input;

    try {
      await updateJob(loaded.job.id, body);
    } catch (error) {
      // 409 は、希望者がいる勤務日の削除・日付変更（読み込んだ後に応募が入った場合）か、掲載停止中の公開状態の変更
      if (
        error instanceof ApiError &&
        error.status === 409 &&
        error.errorCode !== 'CONTENT_SUSPENDED'
      ) {
        reload(WORK_DATE_LOCKED_MESSAGE);
        return;
      }

      throw error;
    }

    navigate(JOB_LIST_PATH, {
      state: { flash: `「${input.title}」を保存しました。` },
    });
  };

  const renderBody = () => {
    if (!canManage) {
      return (
        <Notice>
          求人の登録・管理は、生産者登録が承認されると使えるようになります。
        </Notice>
      );
    }

    if (!isValidId || loadError === 'notFound') {
      return (
        <Notice>
          <p className="m-0 font-bold">求人が見つかりません。</p>
          <p className="m-0 mt-1 text-marche-muted">
            削除されたか、URL が間違っている可能性があります。
          </p>
          <DashboardButton
            to={JOB_LIST_PATH}
            variant="secondary"
            className="mt-4"
          >
            求人管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    if (loadError === 'failed') {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">
            求人を読み込めませんでした。
          </p>
          <p className="m-0 mt-1 text-marche-muted">
            時間をおいて、もう一度お試しください。
          </p>
          <DashboardButton
            variant="secondary"
            onClick={() => reload()}
            className="mt-4"
          >
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (loaded === null) {
      return (
        <div aria-busy="true" className="flex flex-col gap-6">
          {Array.from({ length: 3 }, (_, i) => (
            <div
              key={i}
              className="box-border h-48 animate-pulse rounded-2xl border border-solid border-marche-line bg-white"
            />
          ))}
        </div>
      );
    }

    return (
      <DashboardJobForm
        key={reloadCount}
        job={loaded.job}
        lockedWorkDateIds={loaded.lockedWorkDateIds}
        onSubmit={handleSubmit}
        cancelTo={JOB_LIST_PATH}
      />
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
          <h1 className="m-0 font-serif text-2xl font-bold">求人編集</h1>
          {canManage && isValidId && loadError === null && (
            <DashboardButton
              to={`/dashboard/jobs/${jobId}/applicants`}
              variant="secondary"
              size="sm"
            >
              応募者を見る
              {loaded !== null && `（${loaded.applicationCount}件）`}
            </DashboardButton>
          )}
        </div>
      </header>

      {notice !== null && (
        <div
          role="status"
          className="box-border rounded-2xl border border-solid border-marche-orange/40 bg-marche-orange/15 p-4 text-sm font-bold"
        >
          {notice}
        </div>
      )}

      {renderBody()}
    </div>
  );
}

export default DashboardJobEditPage;
