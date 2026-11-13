import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 求人応募API POST /api/v1/jobs/{jobId}/applications
//
// ログイン中の会員（山本 健太）が求人3（海風水産・干物の加工）の勤務日7 に応募した結果を返す
// ※ 自分が所有する求人（求人1・2）への応募は本来 403 になる
// 応募は「希望日の申請」で、採用が決まるまで status は applied のまま
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// 自分の求人に応募した（status: 403）:
//   { errorCode: 'FORBIDDEN', errorMsg: 'ご自身の求人には応募できません。' }
// 応募済み（status: 409）:
//   { errorCode: 'ALREADY_APPLIED', errorMsg: 'この求人には応募済みです。' }
// 募集終了・枠が埋まった（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '選択した勤務日は募集を締め切りました。' }
const jobApply: RestMock = {
  method: 'POST',
  path: '/api/v1/jobs/:jobId/applications',
  status: 201,
  body: {
    id: 4,
    jobId: 3,
    workDateIds: [7],
    message: '早朝の作業も大丈夫です。干物づくりを体験してみたいです。',
    answers: [],
    status: 'applied',
    decidedAt: null,
    createdAt: hoursFromNow(0),
  },
};

export { jobApply };
