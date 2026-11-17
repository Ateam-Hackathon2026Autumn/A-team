import { useEffect, useState, type ReactNode } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import { getDashboardExperience, updateExperience } from '../../api/dashboardExperienceApi';
import DashboardButton from '../../components/DashboardButton';
import DashboardExperienceForm from '../../components/DashboardExperienceForm';
import DashboardExperienceSlots from '../../components/DashboardExperienceSlots';
import { userInfoAtom } from '../../stores/userAtom';
import type { DashboardExperience, ExperienceInput } from '../../types/dashboardExperience';

const EXPERIENCE_LIST_PATH = '/dashboard/experiences';

// 他の画面で先に更新されていた（412）ときの案内
const STALE_MESSAGE =
  '他の画面で体験が更新されていたため、最新の内容を読み込み直しました。もう一度編集して保存してください。';

// 予約枠の変更後、体験の内容が他の画面で更新されていたときの案内
const CHANGED_ELSEWHERE_MESSAGE =
  '他の画面で体験の内容が更新されています。このまま保存すると最新の内容を読み込み直すため、入力内容を控えてから保存してください。';

// 予約枠の変更では更新日時（updatedAt）だけが変わる。それ以外が同じなら同じ内容とみなす
function hasSameContent(a: DashboardExperience, b: DashboardExperience): boolean {
  const { updatedAt: _a, ...restA } = a;
  const { updatedAt: _b, ...restB } = b;

  return JSON.stringify(restA) === JSON.stringify(restB);
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function DashboardExperienceEditPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { experienceId: experienceIdParam } = useParams();
  const experienceId = Number(experienceIdParam);
  const isValidId = Number.isInteger(experienceId) && experienceId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、体験のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  // 登録画面から来たときのお知らせ
  const [flash] = useState<string | null>(
    (location.state as { flash?: string } | null)?.flash ?? null,
  );

  // 再読み込みでお知らせが再表示されないよう、履歴の state を消す
  useEffect(() => {
    if (location.state !== null) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  const [experience, setExperience] = useState<DashboardExperience | null>(null);
  // 体験の ETag（予約枠を変えると変わるため、フォームとは別に持って取り直す）
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

    getDashboardExperience(experienceId)
      .then((result) => {
        if (isActive) {
          setExperience(result.data);
          setEtag(result.etag);
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
  }, [canManage, isValidId, experienceId, reloadCount]);

  const reload = () => {
    setLoadError(null);
    setExperience(null);
    setReloadCount((count) => count + 1);
  };

  // 予約枠を変更すると体験の ETag も変わるため、取り直す（入力中のフォームは残す）
  // ただし ETag を新しくしてよいのは、体験の内容がフォームの元にした版から変わっていないときだけ。
  // 他の画面で内容が変わっていたら古い ETag のままにし、保存時に 412 → 読み込み直しで
  // 他の人の変更を古い入力内容で上書きしないようにする。
  const refreshEtag = () => {
    const base = experience;

    getDashboardExperience(experienceId)
      .then((result) => {
        if (base !== null && hasSameContent(base, result.data)) {
          setEtag(result.etag);
          return;
        }

        setNotice(CHANGED_ELSEWHERE_MESSAGE);
      })
      .catch(() => {
        // 取り直せなくても、保存時に 412 になれば読み込み直す
      });
  };

  const handleSubmit = async (input: ExperienceInput) => {
    setNotice(null);

    try {
      await updateExperience(experienceId, input, etag);
    } catch (error) {
      if (error instanceof ApiError && error.status === 412) {
        setNotice(STALE_MESSAGE);
        reload();
        window.scrollTo({ top: 0 });
        return;
      }

      // 409（予約があるため変更できない項目）などはフォームに表示する
      throw error;
    }

    navigate(EXPERIENCE_LIST_PATH, {
      state: { flash: `「${input.title}」を保存しました。` },
    });
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

    if (loadError === 'failed') {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">体験を読み込めませんでした。</p>
          <p className="m-0 mt-1 text-marche-muted">時間をおいて、もう一度お試しください。</p>
          <DashboardButton variant="secondary" onClick={reload} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (experience === null) {
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
    if (experience.publishStatus === 'suspended') {
      return (
        <Notice>
          <p className="m-0 font-bold">この体験は運営により掲載停止中のため、編集できません。</p>
          <p className="m-0 mt-1 text-marche-muted">くわしくは運営にお問い合わせください。</p>
          <DashboardButton to={EXPERIENCE_LIST_PATH} variant="secondary" className="mt-4">
            体験管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    return (
      <>
        <DashboardExperienceSlots experienceId={experience.id} onChanged={refreshEtag} />
        <DashboardExperienceForm
          key={reloadCount}
          experience={experience}
          onSubmit={handleSubmit}
          cancelTo={EXPERIENCE_LIST_PATH}
        />
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
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="m-0 font-serif text-2xl font-bold">体験編集</h1>
          {canManage && isValidId && loadError === null && (
            <DashboardButton
              to={`/dashboard/experiences/${experienceId}/participants`}
              variant="secondary"
              size="sm"
            >
              申込者を見る
            </DashboardButton>
          )}
        </div>
      </header>

      {flash !== null && (
        <p
          role="status"
          className="m-0 box-border rounded-2xl border border-solid border-marche-green/30 bg-marche-sage p-4 text-sm font-bold text-marche-green"
        >
          {flash}
        </p>
      )}

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

export default DashboardExperienceEditPage;
