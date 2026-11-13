import type { RestMock } from '../../types';
import { daysFromNow } from '../../helpers';

// 求人詳細取得API GET /api/v1/jobs/{jobId}
//
// どの jobId でも求人1（りんごの収穫・選果スタッフ）を返す
// workDates は今日以降の勤務日（満員も含む）。応募時は選んだ id を workDateIds に入れて送る
// applicationQuestions は現状の仕様では常に空配列
//
// 存在しない・非公開の場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '求人が見つかりません。' }
const jobDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/jobs/:jobId',
  status: 200,
  body: {
    id: 1,
    title: 'りんごの収穫・選果スタッフ',
    producer: { id: 1, businessName: '山本農園', genre: 'agriculture' },
    prefectureId: 20,
    prefectureName: '長野県',
    areaId: 4,
    termType: 'short',
    payUnit: 'hourly',
    payAmount: 1200,
    periodStart: daysFromNow(-14),
    periodEnd: daysFromNow(30),
    workHours: '8:00〜15:00',
    workPlace: '長野県安曇野市 山本農園 りんご園・選果場',
    slots: 5,
    inexperiencedOk: true,
    coverImageUrl: 'https://picsum.photos/seed/job-1/800/600',
    isAcceptingApplications: true,
    description:
      '収穫最盛期のりんご園で、ふじの収穫と選果（大きさ・色づきの仕分け）をお手伝いいただきます。\n' +
      '未経験の方にも、はさみの使い方から丁寧にお教えします。住み込み可（個室・食事付き）です。',
    requirements: ['18歳以上の方', '3日以上勤務できる方', '屋外での立ち仕事に抵抗のない方'],
    belongings: ['汚れてもよい服装', '長靴', '帽子', '飲み物'],
    notes: ['雨天時は選果場での作業になります。', '住み込みを希望される方は応募メッセージでお知らせください。'],
    workDates: {
      items: [
        { id: 1, workDate: daysFromNow(5), neededCount: 5, remainingCount: 5, isSelectable: true },
        { id: 2, workDate: daysFromNow(6), neededCount: 5, remainingCount: 5, isSelectable: true },
        { id: 3, workDate: daysFromNow(12), neededCount: 5, remainingCount: 5, isSelectable: true },
        { id: 4, workDate: daysFromNow(13), neededCount: 5, remainingCount: 5, isSelectable: true },
        { id: 5, workDate: daysFromNow(26), neededCount: 3, remainingCount: 3, isSelectable: true },
        { id: 6, workDate: daysFromNow(34), neededCount: 3, remainingCount: 3, isSelectable: true },
      ],
      total: 6,
      page: 1,
      pageSize: 20,
      totalPages: 1,
    },
    applicationQuestions: [],
  },
};

export { jobDetail };
