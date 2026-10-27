import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 求人応募の取り下げAPI POST /api/v1/users/me/job-applications/:applicationId/withdraw
//
// リクエスト本文なし。取り下げ後の応募を、求人応募状況取得API（GET /api/v1/users/me/job-applications）の
// items 1件と同じ形で返す
// 取り下げできるのは applied（応募済）・screening（選考中）のときだけ
// 採用後（hired）の辞退はこの API ではなく、生産者とのチャットで連絡する
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// 自分の応募ではない・存在しない（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '応募が見つかりません。' }
// 取り下げできない状態（status: 409。hired・rejected・withdrawn・completed）:
//   { errorCode: 'CONFLICT', errorMsg: 'この応募は取り下げできません。' }
const myJobApplicationWithdraw: RestMock = {
  method: 'POST',
  path: '/api/v1/users/me/job-applications/:applicationId/withdraw',
  status: 200,
  body: {
    id: 4,
    job: {
      id: 3,
      title: '干物の加工・出荷のお手伝い',
      isPublic: true,
    },
    workDates: [{ id: 7, workDate: daysFromNow(12) }],
    status: 'withdrawn',
    decidedAt: null,
    createdAt: hoursFromNow(-5),
    updatedAt: hoursFromNow(0),
  },
};

export { myJobApplicationWithdraw };
