import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 体験申込状況取得API GET /api/v1/users/me/experience-applications
//
// ログイン中の会員（山本 健太）が、ほかの生産者の体験に申し込んだ一覧
// 申込後に体験が非公開になった場合は experience: { id, title: null, isPublic: false } になる
//
// 申込なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 未ログインの場合（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
const myExperienceApplications: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me/experience-applications',
  status: 200,
  body: {
    items: [
      {
        id: 102,
        reservationNo: 'RSV-000102',
        experience: {
          id: 4,
          title: '牧場で乳しぼり＆手づくりバター',
          isPublic: true,
        },
        slot: {
          id: 41,
          startAt: `${daysFromNow(24)}T13:00:00+09:00`,
          durationMin: 120,
          status: 'open',
        },
        adultCount: 2,
        childCount: 1,
        infantCount: 0,
        totalAmount: 7400,
        status: 'confirmed',
        createdAt: hoursFromNow(-24 * 3),
      },
      {
        id: 98,
        reservationNo: 'RSV-000098',
        experience: {
          id: 3,
          title: '定置網漁の見学と、漁師の朝ごはん',
          isPublic: true,
        },
        slot: {
          id: 31,
          startAt: `${daysFromNow(17)}T05:30:00+09:00`,
          durationMin: 240,
          status: 'open',
        },
        adultCount: 1,
        childCount: 0,
        infantCount: 0,
        totalAmount: 6000,
        status: 'applied',
        createdAt: hoursFromNow(-24 * 7),
      },
    ],
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { myExperienceApplications };
