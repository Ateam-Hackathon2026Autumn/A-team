import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 【生産者】応募者の採用・不採用更新API PATCH /api/v1/dashboard/jobs/{jobId}/applications/{applicationId}
//
// 応募1（高橋 ゆい）を採用（hired）にした結果を返す
// リクエストの status は screening（選考中）/ hired（採用）/ rejected（不採用）のどれか
// 不採用にした結果を見たい場合は status を 'rejected' に書き換える。screening のときは decidedAt を null にする
// 返ってきた etag が次の更新の If-Match になる
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 採用枠が埋まっている（status: 409）:
//   { errorCode: 'CAPACITY_CONFLICT', errorMsg: '募集人数に達しているため採用できません。' }
// 採用・不採用が決まった後に変更しようとした（status: 409）:
//   { errorCode: 'INVALID_TRANSITION', errorMsg: 'この応募の状態は変更できません。' }
// 他の人が先に更新していた（status: 412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '応募が更新されています。再読み込みしてください。' }
const dashboardJobApplicationUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/jobs/:jobId/applications/:applicationId',
  status: 200,
  body: {
    id: 1,
    jobId: 1,
    applicant: {
      id: 5,
      lastName: '高橋',
      firstName: 'ゆい',
      email: 'takahashi@example.com',
      phone: '080-3456-7890',
      isActive: true,
    },
    message: '週末に家庭菜園をしています。りんご農家の仕事を間近で学びたいです。体力には自信があります。',
    answers: [],
    workDates: [
      { id: 1, workDate: daysFromNow(5) },
      { id: 2, workDate: daysFromNow(6) },
      { id: 3, workDate: daysFromNow(12) },
    ],
    status: 'hired',
    decidedAt: hoursFromNow(0),
    createdAt: hoursFromNow(-24 * 3),
    updatedAt: hoursFromNow(0),
    etag: '"application-1-v2"',
  },
};

export { dashboardJobApplicationUpdate };
