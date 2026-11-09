import { Link, useNavigate } from 'react-router';
import { useAtomValue } from 'jotai';

import { createExperience, newIdempotencyKey } from '../../api/dashboardExperienceApi';
import DashboardExperienceForm from '../../components/DashboardExperienceForm';
import { userInfoAtom } from '../../stores/userAtom';
import type { ExperienceInput } from '../../types/experience';

const EXPERIENCE_LIST_PATH = '/dashboard/experiences';

function DashboardExperienceNewPage() {
  const navigate = useNavigate();
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、体験のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const handleSubmit = async (input: ExperienceInput) => {
    // 失敗時は ApiError のまま投げ、フォーム側でエラーを表示する
    const { data } = await createExperience(input, newIdempotencyKey());
    const action = input.publishStatus === 'public' ? '公開しました' : '下書きとして保存しました';

    // 予約枠は体験の登録後に追加するため、編集画面の予約枠へ進む
    navigate(`/dashboard/experiences/${data.id}/edit`, {
      state: {
        flash: `「${input.title}」を${action}。続けて「予約枠」から開催日時と定員を追加してください。`,
      },
    });
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
        <h1 className="m-0 font-serif mt-2 text-2xl font-bold">体験登録</h1>
        <p className="m-0 mt-1 text-sm text-marche-muted">
          体験の内容を登録したあと、開催日時と定員（予約枠）を追加します。
        </p>
      </header>

      {canManage ? (
        <DashboardExperienceForm onSubmit={handleSubmit} cancelTo={EXPERIENCE_LIST_PATH} />
      ) : (
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          体験の登録・管理は、生産者登録が承認されると使えるようになります。
        </p>
      )}
    </div>
  );
}

export default DashboardExperienceNewPage;
