import type { MyExperienceApplication } from '../../../types/experience';
import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';
import { conflict, idFromPath, notFound } from '../store/common';

// 体験申込状況取得API GET /api/v1/users/me/experience-applications
//
// ログイン中の会員（山本 健太）が、ほかの生産者の体験に申し込んだ一覧
// 申込後に体験が非公開になった場合は experience: { id, title: null, isPublic: false } になる
//
// 申込なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
// 未ログインの場合（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
const initialExperienceApplications: MyExperienceApplication[] = [
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
    cancellable: true,
    cancelDeadlineAt: `${daysFromNow(23)}T13:00:00+09:00`,
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
    cancellable: false,
    cancelDeadlineAt: `${daysFromNow(16)}T05:30:00+09:00`,
    createdAt: hoursFromNow(-24 * 7),
  },
];

let experienceApplicationsState: MyExperienceApplication[] = structuredClone(initialExperienceApplications);

export function cancelMockExperienceApplication(url: URL) {
  const applicationId = idFromPath(url, 1);
  const target = experienceApplicationsState.find((item) => item.id === applicationId);
  if (!target) {
    return notFound('予約が見つかりません。');
  }
  if (!target.cancellable || target.status !== 'confirmed') {
    return conflict(
      'CANCEL_NOT_ALLOWED',
      'キャンセルの受付期間が過ぎたか、キャンセルできない予約です。主催者にメッセージでご連絡ください。',
    );
  }
  const updated: MyExperienceApplication = {
    ...target,
    status: 'canceled',
    cancellable: false,
  };
  experienceApplicationsState = experienceApplicationsState.map((item) =>
    item.id === applicationId ? updated : item,
  );
  return { status: 200, body: updated };
}

const myExperienceApplications: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me/experience-applications',
  status: 200,
  body: {
    items: initialExperienceApplications,
    total: initialExperienceApplications.length,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
  handler: () => ({
    status: 200,
    body: {
      items: experienceApplicationsState,
      total: experienceApplicationsState.length,
      page: 1,
      pageSize: 20,
      totalPages: experienceApplicationsState.length > 0 ? 1 : 0,
    },
  }),
};

export { myExperienceApplications };
