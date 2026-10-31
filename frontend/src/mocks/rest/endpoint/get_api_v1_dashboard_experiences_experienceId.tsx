import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 体験詳細取得API GET /api/v1/dashboard/experiences/:experienceId
//
// 編集画面用に全項目と画像（S3 キーと表示用 URL）を返す。予約枠は予約枠一覧取得APIで取得する
//
// 自分の体験ではない・存在しない・削除済みの場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '対象の体験が見つかりません。' }
const dashboardExperienceDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/experiences/:experienceId',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    title: '蜜入りりんごの収穫体験とアップルパイづくり',
    prefectureId: 20,
    description:
      '北アルプスのふもと、安曇野の山本農園で蜜入りりんご「サンふじ」の収穫を体験できます。\n収穫したりんごを使って、農園のキッチンでアップルパイづくりにも挑戦します。焼きたてのパイはその場で味わえるほか、お土産としてお持ち帰りいただけます。',
    place: '長野県 安曇野市（山本農園）',
    priceAdult: 3500,
    priceChild: 2000,
    ageCondition: '小学生以上',
    familyOk: true,
    beginnerOk: true,
    flow: [
      '10:00 集合・農園の紹介',
      '10:20 りんごの収穫体験',
      '11:30 アップルパイづくり',
      '12:30 試食・休憩',
      '13:00 解散',
    ],
    belongings: ['汚れてもよい服装', '軍手', '飲み物', 'エプロン'],
    notes: [
      '雨天の場合は収穫を中止し、アップルパイづくりのみ行います。',
      '駐車場は農園内に10台分あります。',
    ],
    cancelPolicy:
      '開催日の3日前まではキャンセル無料です。2日前〜前日は参加費の50%、当日は100%のキャンセル料がかかります。',
    publishStatus: 'public',
    images: [
      {
        id: 1,
        imageKey: 'experiences/1/apple-harvest.jpg',
        url: 'https://picsum.photos/seed/exp1-harvest/800/600',
        sortOrder: 0,
      },
      {
        id: 2,
        imageKey: 'experiences/1/apple-pie.jpg',
        url: 'https://picsum.photos/seed/exp1-pie/800/600',
        sortOrder: 1,
      },
      {
        id: 3,
        imageKey: 'experiences/1/orchard.jpg',
        url: 'https://picsum.photos/seed/exp1-orchard/800/600',
        sortOrder: 2,
      },
    ],
    createdAt: hoursFromNow(-24 * 30),
    updatedAt: hoursFromNow(-3),
  },
};

export { dashboardExperienceDetail };
