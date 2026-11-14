import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 【生産者】求人登録API POST /api/v1/dashboard/jobs
//
// 新しい求人（id 5）を下書きで登録した結果を返す
// 本来は ETag ヘッダーも返る（更新時の If-Match に使う）がモックでは返さない
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 入力不正（status: 400）:
//   { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。', details: { title: ['タイトルを入力してください。'] } }
// 公開に必要な項目が足りない（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '公開に必要な項目が不足しています。' }
const dashboardJobCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/jobs',
  status: 201,
  body: {
    id: 5,
    producerId: 1,
    publishStatus: 'draft',
    createdAt: hoursFromNow(0),
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardJobCreate };
