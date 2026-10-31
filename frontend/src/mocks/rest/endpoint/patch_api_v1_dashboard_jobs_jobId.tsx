import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 【生産者】求人更新API PATCH /api/v1/dashboard/jobs/{jobId}
//
// 求人1 を更新した結果を返す（送った項目だけが変わる）
// ※ 応募が1件でもある求人は publishStatus と slots 以外を変更できない（409）
// 本来は最新の ETag ヘッダーも返るがモックでは返さない
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 応募があるのに募集条件を変えようとした（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '応募がある求人は公開状態と募集人数以外を変更できません。' }
// 採用済み人数より募集人数を減らそうとした（status: 409）:
//   { errorCode: 'CAPACITY_CONFLICT', errorMsg: '採用済みの人数より少なくはできません。' }
// 他の人が先に更新していた（status: 412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '求人が更新されています。再読み込みしてください。' }
const dashboardJobUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    publishStatus: 'public',
    createdAt: hoursFromNow(-24 * 14),
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardJobUpdate };
