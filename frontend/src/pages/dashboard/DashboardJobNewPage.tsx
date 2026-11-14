import { Link, useNavigate } from 'react-router';
import { useAtomValue } from 'jotai';

import { createJob, newIdempotencyKey } from '../../api/dashboardJobApi';
import DashboardJobForm from '../../components/DashboardJobForm';
import { userInfoAtom } from '../../stores/userAtom';
import type { JobInput } from '../../types/dashboardJob';

const JOB_LIST_PATH = '/dashboard/jobs';

function DashboardJobNewPage() {
  const navigate = useNavigate();
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、求人のAPIは承認済みの生産者のみ使える
  const canManage = userInfo?.isProducer === true;

  const handleSubmit = async (input: JobInput) => {
    // 失敗時は ApiError のまま投げ、フォーム側でエラーを表示する
    await createJob(input, newIdempotencyKey());
    const action = input.publishStatus === 'public' ? '公開しました' : '下書きとして保存しました';

    navigate(JOB_LIST_PATH, { state: { flash: `「${input.title}」を${action}。` } });
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
        <h1 className="m-0 mt-2 font-serif text-2xl font-bold">求人登録</h1>
        <p className="m-0 mt-1 text-sm text-marche-muted">
          勤務地・報酬・仕事内容と、勤務日ごとに必要な人数を登録します。
        </p>
      </header>

      {canManage ? (
        <DashboardJobForm onSubmit={handleSubmit} cancelTo={JOB_LIST_PATH} />
      ) : (
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          求人の登録・管理は、生産者登録が承認されると使えるようになります。
        </p>
      )}
    </div>
  );
}

export default DashboardJobNewPage;
