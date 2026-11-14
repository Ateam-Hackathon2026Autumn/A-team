import { useEffect, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import { getDashboardJob, updateJob } from '../../api/dashboardJobApi';
import DashboardButton from '../../components/DashboardButton';
import DashboardJobForm from '../../components/DashboardJobForm';
import { userInfoAtom } from '../../stores/userAtom';
import type { DashboardJob, JobInput } from '../../types/dashboardJob';

const JOB_LIST_PATH = '/dashboard/jobs';

// 他の画面で先に更新されていた（412）ときの案内
const STALE_MESSAGE =
  '他の画面で求人が更新されていたため、最新の内容を読み込み直しました。もう一度編集して保存してください。';

// 編集中に応募が入り、募集条件を変えられなくなったときの案内
const APPLIED_MESSAGE =
  '編集中にこの求人へ応募が入ったため、募集人数と公開設定以外は変更できなくなりました。最新の内容を読み込み直しました。';

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function DashboardJobEditPage() {
  const navigate = useNavigate();
  const { jobId: jobIdParam } = useParams();
  const jobId = Number(jobIdParam);
  const isValidId = Number.isInteger(jobId) && jobId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、求人のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const [job, setJob] = useState<DashboardJob | null>(null);
  const [etag, setEtag] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<'notFound' | 'failed' | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // 読み込み直すたびに増やす（フォームも作り直して最新の内容にする）
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    if (!canManage || !isValidId) {
      return;
    }

    let isActive = true;

    getDashboardJob(jobId)
      .then((result) => {
        if (isActive) {
          setJob(result.data);
          setEtag(result.etag);
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
  }, [canManage, isValidId, jobId, reloadCount]);

  const reload = (message: string | null = null) => {
    setNotice(message);
    setLoadError(null);
    setJob(null);
    setReloadCount((count) => count + 1);
    window.scrollTo({ top: 0 });
  };

  const handleSubmit = async (input: JobInput) => {
    if (job === null) {
      return;
    }

    setNotice(null);

    // 応募がある求人は、募集人数と公開状態だけを送る（それ以外を送ると同じ値でも 409）
    const body: Partial<JobInput> =
      job.applicationCount > 0
        ? { publishStatus: input.publishStatus, slots: input.slots }
        : input;

    try {
      await updateJob(job.id, body, etag);
    } catch (error) {
      if (error instanceof ApiError && error.status === 412) {
        reload(STALE_MESSAGE);
        return;
      }

      // 読み込んだ後に応募が入った場合は、変更できる項目が変わるため読み込み直す
      if (error instanceof ApiError && error.status === 409 && job.applicationCount === 0) {
        const latest = await getDashboardJob(job.id).catch(() => null);

        if (latest !== null && latest.data.applicationCount > 0) {
          reload(APPLIED_MESSAGE);
          return;
        }
      }

      // 409（公開に必要な勤務日がない・採用済み人数より少ない など）はフォームに表示する
      throw error;
    }

    // 応募がある求人はタイトルを変えられないため、どちらの場合もフォームの値が保存後のタイトル
    navigate(JOB_LIST_PATH, { state: { flash: `「${input.title}」を保存しました。` } });
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

    if (loadError === 'failed') {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">求人を読み込めませんでした。</p>
          <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
          <DashboardButton variant="secondary" onClick={() => reload()} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (job === null) {
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

    // 運営による掲載停止中は、生産者は変更できない
    if (job.publishStatus === 'suspended') {
      return (
        <Notice>
          <p className="m-0 font-bold">この求人は運営により掲載停止中のため、編集できません。</p>
          <p className="m-0 mt-1 text-marche-muted">
            届いている応募は「応募者を見る」から確認できます。くわしくは運営にお問い合わせください。
          </p>
          <DashboardButton to={JOB_LIST_PATH} variant="secondary" className="mt-4">
            求人管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    return (
      <DashboardJobForm key={reloadCount} job={job} onSubmit={handleSubmit} cancelTo={JOB_LIST_PATH} />
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
            <DashboardButton to={`/dashboard/jobs/${jobId}/applicants`} variant="secondary" size="sm">
              応募者を見る
              {job !== null && `（${job.applicationCount}件）`}
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
