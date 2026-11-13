import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 体験申込者一覧取得API GET /api/v1/dashboard/experiences/:experienceId/applications
//
// どの experienceId でも体験1（蜜入りりんごの収穫体験とアップルパイづくり）の予約を created_at の新しい順で返す
// status: 'applied' が新着（未確認）の申込。枠1（予約16人）と枠2（予約3人）の全予約（キャンセル含む）
//
// 退会済み会員の予約は user の氏名と representativeName / phone / message が null になる:
//   user: { id: 9, lastName: null, firstName: null, isActive: false }
//
// 自分の体験ではない・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の体験が見つかりません。' }
const slot1 = {
  id: 1,
  startAt: `${daysFromNow(10)}T10:00:00+09:00`,
  durationMin: 180,
  status: 'open',
};

const slot2 = {
  id: 2,
  startAt: `${daysFromNow(17)}T10:00:00+09:00`,
  durationMin: 180,
  status: 'open',
};

const dashboardExperienceApplicationsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences/:experienceId/applications',
  status: 200,
  body: {
    items: [
      {
        id: 57,
        reservationNo: 'RSV-000057',
        slot: slot1,
        user: { id: 6, lastName: '松本', firstName: '隼', isActive: true },
        adultCount: 3,
        childCount: 0,
        infantCount: 0,
        representativeName: '松本 隼',
        phone: '090-6666-1234',
        message: '友人3人で参加します。車で伺う予定です。',
        totalAmount: 10500,
        status: 'applied',
        policyAgreedAt: hoursFromNow(-3),
        createdAt: hoursFromNow(-3),
      },
      {
        id: 56,
        reservationNo: 'RSV-000056',
        slot: slot1,
        user: { id: 5, lastName: '高橋', firstName: 'ゆい', isActive: true },
        adultCount: 2,
        childCount: 1,
        infantCount: 0,
        representativeName: '高橋 ゆい',
        phone: '080-5555-2345',
        message: '子どもが小学2年生です。アップルパイづくりを楽しみにしています。',
        totalAmount: 9000,
        status: 'applied',
        policyAgreedAt: hoursFromNow(-20),
        createdAt: hoursFromNow(-20),
      },
      {
        id: 55,
        reservationNo: 'RSV-000055',
        slot: slot2,
        user: { id: 8, lastName: '伊藤', firstName: '誠', isActive: true },
        adultCount: 2,
        childCount: 1,
        infantCount: 0,
        representativeName: '伊藤 誠',
        phone: '090-8888-3456',
        message: null,
        totalAmount: 9000,
        status: 'confirmed',
        policyAgreedAt: hoursFromNow(-24 * 2),
        createdAt: hoursFromNow(-24 * 2),
      },
      {
        id: 54,
        reservationNo: 'RSV-000054',
        slot: slot1,
        user: { id: 7, lastName: '森', firstName: 'さくら', isActive: true },
        adultCount: 2,
        childCount: 0,
        infantCount: 0,
        representativeName: '森 さくら',
        phone: '070-7777-4567',
        message: null,
        totalAmount: 7000,
        status: 'canceled',
        policyAgreedAt: hoursFromNow(-24 * 4),
        createdAt: hoursFromNow(-24 * 4),
      },
      {
        id: 53,
        reservationNo: 'RSV-000053',
        slot: slot1,
        user: { id: 4, lastName: '鈴木', firstName: '美咲', isActive: true },
        adultCount: 2,
        childCount: 2,
        infantCount: 0,
        representativeName: '鈴木 美咲',
        phone: '080-4444-5678',
        message: 'りんごアレルギーはありません。よろしくお願いします。',
        totalAmount: 11000,
        status: 'confirmed',
        policyAgreedAt: hoursFromNow(-24 * 6),
        createdAt: hoursFromNow(-24 * 6),
      },
      {
        id: 52,
        reservationNo: 'RSV-000052',
        slot: slot1,
        user: { id: 3, lastName: '田中', firstName: '一郎', isActive: true },
        adultCount: 2,
        childCount: 0,
        infantCount: 0,
        representativeName: '田中 一郎',
        phone: '090-3333-6789',
        message: null,
        totalAmount: 7000,
        status: 'confirmed',
        policyAgreedAt: hoursFromNow(-24 * 9),
        createdAt: hoursFromNow(-24 * 9),
      },
      {
        id: 51,
        reservationNo: 'RSV-000051',
        slot: slot1,
        user: { id: 2, lastName: '佐藤', firstName: '花子', isActive: true },
        // 予約代表者は会員本人と同一とは限らない（ここでは夫の名前で予約）
        adultCount: 2,
        childCount: 2,
        infantCount: 0,
        representativeName: '佐藤 大輔',
        phone: '080-2222-7890',
        message: '家族4人で参加します。',
        totalAmount: 11000,
        status: 'confirmed',
        policyAgreedAt: hoursFromNow(-24 * 12),
        createdAt: hoursFromNow(-24 * 12),
      },
    ],
    total: 7,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { dashboardExperienceApplicationsList };
