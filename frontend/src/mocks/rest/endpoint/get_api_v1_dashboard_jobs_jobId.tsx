import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 【生産者】求人詳細取得API GET /api/v1/dashboard/jobs/{jobId}
//
// どの jobId でも求人1（りんごの収穫・選果スタッフ）の編集用データを返す
// workDates は過去日も含む全勤務日。hiredCount は採用済み人数、remainingCount は残り枠
// 本来は ETag ヘッダーも返る（更新・削除時の If-Match に使う）がモックでは返さない
//
// 他者の求人・存在しない場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
const dashboardJobDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    title: 'りんごの収穫・選果スタッフ',
    prefectureId: 20,
    termType: 'short',
    payUnit: 'hourly',
    payAmount: 1200,
    periodStart: daysFromNow(-14),
    periodEnd: daysFromNow(30),
    workHours: '8:00〜15:00',
    workPlace: '長野県安曇野市 山本農園 りんご園・選果場',
    slots: 5,
    description:
      '収穫最盛期のりんご園で、ふじの収穫と選果（大きさ・色づきの仕分け）をお手伝いいただきます。\n' +
      '未経験の方にも、はさみの使い方から丁寧にお教えします。住み込み可（個室・食事付き）です。',
    requirements: ['18歳以上の方', '3日以上勤務できる方', '屋外での立ち仕事に抵抗のない方'],
    belongings: ['汚れてもよい服装', '長靴', '帽子', '飲み物'],
    notes: ['雨天時は選果場での作業になります。', '住み込みを希望される方は応募メッセージでお知らせください。'],
    inexperiencedOk: true,
    coverImageKey: 'jobs/job-1-cover.jpg',
    publishStatus: 'public',
    workDates: [
      { id: 1, workDate: daysFromNow(5), neededCount: 5, hiredCount: 0, remainingCount: 5 },
      { id: 2, workDate: daysFromNow(6), neededCount: 5, hiredCount: 0, remainingCount: 5 },
      { id: 3, workDate: daysFromNow(12), neededCount: 5, hiredCount: 0, remainingCount: 5 },
      { id: 4, workDate: daysFromNow(13), neededCount: 5, hiredCount: 0, remainingCount: 5 },
      { id: 5, workDate: daysFromNow(26), neededCount: 3, hiredCount: 0, remainingCount: 3 },
      { id: 6, workDate: daysFromNow(34), neededCount: 3, hiredCount: 0, remainingCount: 3 },
    ],
    applicationCount: 2,
    hiredCount: 0,
    createdAt: hoursFromNow(-24 * 14),
    updatedAt: hoursFromNow(-24 * 1),
  },
};

export { dashboardJobDetail };
