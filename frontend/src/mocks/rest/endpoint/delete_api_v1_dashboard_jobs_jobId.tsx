import type { RestMock } from '../../types';

// 【生産者】求人削除API DELETE /api/v1/dashboard/jobs/{jobId}
//
// 論理削除に成功すると 204（本文なし）
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 選考中・採用済みなどの応募が残っている（status: 409）:
//   { errorCode: 'ACTIVE_APPLICATIONS_EXIST', errorMsg: '対応中の応募があるため削除できません。' }
// 他者の求人・削除済み（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
// 他の人が先に更新していた（status: 412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '求人が更新されています。再読み込みしてください。' }
const dashboardJobDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 204,
};

export { dashboardJobDelete };
