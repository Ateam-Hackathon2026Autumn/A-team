import type { RestMock } from '../../types';
import { daysFromNow } from '../../helpers';

// 求人一覧取得API（エリア・ジャンル絞り込み・生産者指定） GET /api/v1/jobs
//
// クエリ（page / pageSize / areaId / prefectureId / producerId / genre）による絞り込みはモックでは行わない
// areaId は 北海道1 / 東北2 / 関東3 / 中部4 / 近畿5 / 中国・四国6 / 九州・沖縄7
// periodStart / periodEnd は募集期間（null 側は無制限）
// isAcceptingApplications が false の求人も一覧には表示する（応募ボタンだけ押せなくする）
//
// 該当なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
const jobsList: RestMock = {
  method: 'GET',
  path: '/api/v1/jobs',
  status: 200,
  body: {
    items: [
      {
        id: 4,
        title: '酪農スタッフ（将来の独立支援あり）',
        producer: { id: 3, businessName: '北の丘ファーム', genre: 'livestock' },
        prefectureId: 1,
        prefectureName: '北海道',
        areaId: 1,
        termType: 'long',
        payUnit: 'monthly',
        payAmount: 240000,
        periodStart: null,
        periodEnd: null,
        workHours: '週5日シフト制',
        workPlace: '北海道十勝郡 北の丘ファーム',
        slots: 1,
        inexperiencedOk: true,
        coverImageUrl: 'https://picsum.photos/seed/job-4/800/600',
        isAcceptingApplications: true,
      },
      {
        id: 3,
        title: '干物の加工・出荷のお手伝い',
        producer: { id: 2, businessName: '海風水産', genre: 'fishery' },
        prefectureId: 22,
        prefectureName: '静岡県',
        areaId: 4,
        termType: 'one_day',
        payUnit: 'hourly',
        payAmount: 1150,
        periodStart: daysFromNow(-7),
        periodEnd: daysFromNow(10),
        workHours: '6:00〜12:00',
        workPlace: '静岡県沼津市 海風水産 加工場',
        slots: 2,
        inexperiencedOk: true,
        coverImageUrl: 'https://picsum.photos/seed/job-3/800/600',
        isAcceptingApplications: true,
      },
      {
        id: 2,
        title: '冬の剪定作業補助',
        producer: { id: 1, businessName: '山本農園', genre: 'agriculture' },
        prefectureId: 20,
        prefectureName: '長野県',
        areaId: 4,
        termType: 'long',
        payUnit: 'daily',
        payAmount: 9500,
        periodStart: daysFromNow(-3),
        periodEnd: daysFromNow(30),
        workHours: '8:30〜16:30',
        workPlace: '長野県安曇野市 山本農園 りんご園',
        slots: 2,
        inexperiencedOk: false,
        coverImageUrl: 'https://picsum.photos/seed/job-2/800/600',
        isAcceptingApplications: true,
      },
      {
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
      },
    ],
    total: 4,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { jobsList };
