import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 【生産者】求人応募者一覧取得API GET /api/v1/dashboard/jobs/{jobId}/applications
//
// どの jobId でも求人1（りんごの収穫・選果スタッフ）の応募者を返す
// items[].etag は採用・不採用更新API の If-Match に渡す値（求人の ETag とは別）
// 退会した応募者は applicant が { id, lastName: null, firstName: null, email: null, phone: null, isActive: false } になる
//
// 応募なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 他者の求人・存在しない場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
const dashboardJobApplicationsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/jobs/:jobId/applications',
  status: 200,
  body: {
    items: [
      {
        id: 2,
        jobId: 1,
        applicant: {
          id: 6,
          lastName: '松本',
          firstName: '隼',
          email: 'matsumoto@example.com',
          phone: '090-2345-6789',
          isActive: true,
        },
        message: '長野県内に住んでいます。収穫期は週末を中心に勤務できます。',
        answers: [],
        workDates: [
          { id: 2, workDate: daysFromNow(6) },
          { id: 4, workDate: daysFromNow(13) },
        ],
        status: 'applied',
        decidedAt: null,
        createdAt: hoursFromNow(-24 * 1),
        updatedAt: hoursFromNow(-24 * 1),
        etag: '"application-2-v1"',
      },
      {
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
        status: 'applied',
        decidedAt: null,
        createdAt: hoursFromNow(-24 * 3),
        updatedAt: hoursFromNow(-24 * 3),
        etag: '"application-1-v1"',
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { dashboardJobApplicationsList };
