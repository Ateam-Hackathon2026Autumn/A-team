import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import {
  deleteExperience,
  getDashboardExperience,
  getDashboardExperiences,
} from '../../api/dashboardExperienceApi';
import DashboardButton from '../../components/DashboardButton';
import { PlusIcon } from '../../components/DashboardIcons';
import { userInfoAtom } from '../../stores/userAtom';
import type {
  DashboardExperienceSummary,
  ExperiencePublishStatus,
} from '../../types/dashboardExperience';
import {
  formatDateTime,
  formatYen,
  publishStatusBadgeClassNames,
  publishStatusLabels,
} from '../../utils/experienceFormat';
import { prefectureName } from '../../utils/prefectures';

const NEW_EXPERIENCE_PATH = '/dashboard/experiences/new';

// 公開状態での絞り込み（'all' は全件）
type StatusFilter = ExperiencePublishStatus | 'all';

const statusFilters: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'すべて' },
  { value: 'public', label: '公開中' },
  { value: 'private', label: '非公開' },
  { value: 'draft', label: '下書き' },
  { value: 'suspended', label: '掲載停止中' },
];

function ExperienceRowSkeleton() {
  return (
    <li className="box-border flex animate-pulse flex-col gap-3 rounded-2xl border border-solid border-marche-line bg-white p-5">
      <div className="h-4 w-64 max-w-full rounded bg-marche-canvas" />
      <div className="h-3 w-40 rounded bg-marche-canvas" />
    </li>
  );
}

function ExperienceRow({
  experience,
  isPending,
  onDelete,
}: {
  experience: DashboardExperienceSummary;
  isPending: boolean;
  onDelete: (experience: DashboardExperienceSummary) => void;
}) {
  const editPath = `/dashboard/experiences/${experience.id}/edit`;
  const participantsPath = `/dashboard/experiences/${experience.id}/participants`;
  const isSuspended = experience.publishStatus === 'suspended';

  return (
    <li className="box-border flex flex-col gap-4 rounded-2xl border border-solid border-marche-line bg-white p-5 lg:flex-row lg:items-center">
      <div className="min-w-0 flex-1">
        <p className="m-0 flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-bold ${publishStatusBadgeClassNames[experience.publishStatus]}`}
          >
            {publishStatusLabels[experience.publishStatus]}
          </span>
          <span className="text-xs text-marche-muted">
            {prefectureName(experience.prefectureId)}
          </span>
        </p>
        {isSuspended ? (
          <p className="m-0 mt-1 font-bold">{experience.title}</p>
        ) : (
          <Link
            to={editPath}
            className="mt-1 block font-bold text-marche-ink no-underline hover:underline"
          >
            {experience.title}
          </Link>
        )}
        <p className="m-0 mt-1 text-sm text-marche-muted">
          大人 {formatYen(experience.priceAdult)}
          {experience.priceChild !== null && ` ・ 子ども ${formatYen(experience.priceChild)}`}
        </p>
        <dl className="m-0 mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs">
          <div className="flex gap-1">
            <dt className="text-marche-muted">次回開催</dt>
            <dd className="m-0 font-bold">
              {experience.nextStartAt === null ? '予定なし' : formatDateTime(experience.nextStartAt)}
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-marche-muted">予約枠</dt>
            <dd className="m-0 font-bold">{experience.slotCount}件</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-marche-muted">申込</dt>
            <dd className="m-0 font-bold">{experience.applicationCount}件</dd>
          </div>
        </dl>
      </div>

      <div className="flex flex-wrap gap-2">
        {!isSuspended && (
          <DashboardButton to={editPath} variant="secondary" size="sm">
            編集・予約枠
          </DashboardButton>
        )}
        <DashboardButton to={participantsPath} variant="secondary" size="sm">
          申込者を見る
        </DashboardButton>
        {!isSuspended && (
          <DashboardButton
            variant="danger"
            size="sm"
            disabled={isPending}
            onClick={() => onDelete(experience)}
          >
            {isPending ? '削除中…' : '削除'}
          </DashboardButton>
        )}
      </div>
    </li>
  );
}

function DashboardExperienceListPage() {
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、体験のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const location = useLocation();
  const navigate = useNavigate();
  // 登録画面などから戻ってきたときのお知らせ
  const [flash] = useState<string | null>(
    (location.state as { flash?: string } | null)?.flash ?? null,
  );

  // 再読み込みでお知らせが再表示されないよう、履歴の state を消す
  useEffect(() => {
    if (location.state !== null) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  const [experiences, setExperiences] = useState<DashboardExperienceSummary[] | null>(null);
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

    async function fetchExperiences() {
      try {
        const data = await getDashboardExperiences(
          page,
          statusFilter === 'all' ? undefined : statusFilter,
        );

        if (!isActive) {
          return;
        }

        // 削除などで今のページが総ページ数を超えた（空になった）ら、最後のページへ戻る
        if (data.items.length === 0 && page > 1 && page > data.totalPages) {
          setExperiences(null);
          setPage(Math.max(1, data.totalPages));
          return;
        }

        setExperiences(data.items);
        setTotal(data.total);
        setTotalPages(data.totalPages);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setHasLoadError(true);
        }
      }
    }

    fetchExperiences();

    return () => {
      isActive = false;
    };
  }, [canManage, page, statusFilter, reloadCount]);

  const reload = () => {
    setHasLoadError(false);
    setExperiences(null);
    setReloadCount((count) => count + 1);
  };

  const changePage = (nextPage: number) => {
    setActionError(null);
    setExperiences(null);
    setPage(nextPage);
  };

  const changeFilter = (filter: StatusFilter) => {
    setActionError(null);
    setNotice(null);
    setExperiences(null);
    setPage(1);
    setStatusFilter(filter);
  };

  const handleDelete = async (experience: DashboardExperienceSummary) => {
    if (
      !window.confirm(
        `「${experience.title}」を削除します。予約枠も含めて元に戻せません。よろしいですか？`,
      )
    ) {
      return;
    }

    setActionError(null);
    setNotice(null);
    setPendingId(experience.id);

    try {
      // 削除の If-Match に体験の ETag が必要（一覧には含まれないため詳細から取る）
      const { etag } = await getDashboardExperience(experience.id);
      await deleteExperience(experience.id, etag);

      setNotice(`「${experience.title}」を削除しました。`);
      // 取り直すまでの間も削除した体験が残らないよう、先に一覧から外す
      setExperiences(
        (current) => current?.filter(({ id }) => id !== experience.id) ?? null,
      );
      // 総件数・総ページ数を合わせるため一覧を取り直す
      setReloadCount((count) => count + 1);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError && error.status === 409) {
        setActionError(
          `「${experience.title}」は申込中・確定の予約が残っているため削除できません。予約が終わってから削除するか、非公開にしてください。`,
        );
      } else if (error instanceof ApiError && (error.status === 404 || error.status === 412)) {
        setActionError(
          '他の画面で体験が更新・削除されていたため、最新の内容を読み込み直しました。',
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

  if (!canManage) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="m-0 font-serif text-2xl font-bold">体験管理</h1>
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          体験の登録・管理は、生産者登録が承認されると使えるようになります。
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="m-0 font-serif text-2xl font-bold">
          体験管理
          {experiences !== null && (
            <span className="ml-2 text-sm font-normal text-marche-muted">{total}件</span>
          )}
        </h1>
        <DashboardButton to={NEW_EXPERIENCE_PATH}>
          <PlusIcon className="size-4" />
          体験を登録
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
          <p className="m-0 font-bold text-marche-red">体験の一覧を読み込めませんでした。</p>
          <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
          <DashboardButton variant="secondary" onClick={reload} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      ) : experiences === null ? (
        <ul aria-busy="true" className="m-0 flex list-none flex-col gap-3 p-0">
          {Array.from({ length: 3 }, (_, i) => (
            <ExperienceRowSkeleton key={i} />
          ))}
        </ul>
      ) : experiences.length === 0 ? (
        <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-8 text-center">
          {statusFilter === 'all' ? (
            <>
              <p className="m-0 font-bold">まだ体験がありません</p>
              <p className="m-0 mt-1 text-sm text-marche-muted">
                収穫体験や農作業体験など、最初の体験を登録しましょう。
              </p>
              <DashboardButton to={NEW_EXPERIENCE_PATH} className="mt-4">
                <PlusIcon className="size-4" />
                体験を登録
              </DashboardButton>
            </>
          ) : (
            <p className="m-0 text-sm text-marche-muted">該当する体験はありません。</p>
          )}
        </div>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {experiences.map((experience) => (
            <ExperienceRow
              key={experience.id}
              experience={experience}
              isPending={pendingId === experience.id}
              onDelete={handleDelete}
            />
          ))}
        </ul>
      )}

      {!hasLoadError && experiences !== null && totalPages > 1 && (
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

export default DashboardExperienceListPage;
