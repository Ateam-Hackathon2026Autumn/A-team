import type { RestMock } from '../../types';
import { listExperiences } from '../store/dashboardExperiences';

// 体験一覧取得API GET /api/v1/dashboard/experiences?publishStatus=&page=
//
// ログイン中の生産者（山本農園）が登録した体験を created_at の新しい順で返す（20件ずつ）
// publishStatus（draft / public / private / suspended）を指定するとその状態だけに絞り込む
// slotCount は未削除の全枠数、applicationCount は全状態（キャンセル含む）の予約件数
// データは store/dashboardExperiences.tsx。登録・更新・削除・予約枠の変更がそのまま反映される
//
// 体験が0件の場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
//
// 未ログインの場合（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
//
// 生産者でない・利用停止中の場合（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: 'この操作を行う権限がありません。' }
const dashboardExperiencesList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences',
  status: 200,
  handler: (url) => listExperiences(url),
};

export { dashboardExperiencesList };
