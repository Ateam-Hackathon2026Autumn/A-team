import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 求人応募状況取得API GET /api/v1/users/me/job-applications
//
// ログイン中の会員（山本 健太）が、ほかの生産者の求人に応募した一覧
// status: applied=応募済 / screening=選考中 / hired=採用 / rejected=不採用 / withdrawn=取下げ / completed=勤務完了
// 応募後に求人が非公開・削除になった場合は job: { id, title: null, isPublic: false } になる
//
// 応募なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 未ログインの場合（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
const myJobApplications: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me/job-applications',
  status: 200,
  body: {
    items: [
      {
        id: 4,
        job: {
          id: 3,
          title: '干物の加工・出荷のお手伝い',
          isPublic: true,
        },
        workDates: [{ id: 7, workDate: daysFromNow(12) }],
        status: 'applied',
        decidedAt: null,
        createdAt: hoursFromNow(-5),
        updatedAt: hoursFromNow(-5),
      },
      {
        id: 5,
        job: {
          id: 4,
          title: '酪農スタッフ（将来の独立支援あり）',
          isPublic: true,
        },
        workDates: [],
        status: 'screening',
        decidedAt: null,
        createdAt: hoursFromNow(-24 * 10),
        updatedAt: hoursFromNow(-24 * 2),
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { myJobApplications };
