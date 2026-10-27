import type { RestMock } from '../../types';
import { daysFromNow } from '../../helpers';

// 体験一覧取得API（エリア絞り込み・生産者指定） GET /api/v1/experiences
//
// クエリ（page / pageSize / areaId / prefectureId / producerId）による絞り込みはモックでは行わない
// areaId は 北海道1 / 東北2 / 関東3 / 中部4 / 近畿5 / 中国・四国6 / 九州・沖縄7
// nextStartAt は将来の開催枠のうち最も早い日時（満席も含む）。開催枠なしは null
//
// 該当なしの場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
const experiencesList: RestMock = {
  method: 'GET',
  path: '/api/v1/experiences',
  status: 200,
  body: {
    items: [
      {
        id: 4,
        title: '牧場で乳しぼり＆手づくりバター',
        prefectureId: 1,
        prefectureName: '北海道',
        areaId: 1,
        priceAdult: 2800,
        priceChild: 1800,
        familyOk: true,
        beginnerOk: true,
        thumbnailUrl: 'https://picsum.photos/seed/exp-4/800/600',
        producer: {
          id: 3,
          businessName: '北の丘ファーム',
          prefectureId: 1,
          prefectureName: '北海道',
          city: '十勝郡',
        },
        nextStartAt: `${daysFromNow(24)}T13:00:00+09:00`,
      },
      {
        id: 3,
        title: '定置網漁の見学と、漁師の朝ごはん',
        prefectureId: 22,
        prefectureName: '静岡県',
        areaId: 4,
        priceAdult: 6000,
        priceChild: null,
        familyOk: false,
        beginnerOk: true,
        thumbnailUrl: 'https://picsum.photos/seed/exp-3/800/600',
        producer: {
          id: 2,
          businessName: '海風水産',
          prefectureId: 22,
          prefectureName: '静岡県',
          city: '沼津市',
        },
        nextStartAt: `${daysFromNow(17)}T05:30:00+09:00`,
      },
      {
        id: 2,
        title: '冬の剪定見学とりんご農家の昼ごはん',
        prefectureId: 20,
        prefectureName: '長野県',
        areaId: 4,
        priceAdult: 2500,
        priceChild: null,
        familyOk: false,
        beginnerOk: true,
        thumbnailUrl: 'https://picsum.photos/seed/exp-2/800/600',
        producer: {
          id: 1,
          businessName: '山本農園',
          prefectureId: 20,
          prefectureName: '長野県',
          city: '安曇野市',
        },
        nextStartAt: `${daysFromNow(90)}T10:00:00+09:00`,
      },
      {
        id: 1,
        title: '蜜入りりんごの収穫体験とアップルパイづくり',
        prefectureId: 20,
        prefectureName: '長野県',
        areaId: 4,
        priceAdult: 3500,
        priceChild: 2000,
        familyOk: true,
        beginnerOk: true,
        thumbnailUrl: 'https://picsum.photos/seed/exp1-harvest/800/600',
        producer: {
          id: 1,
          businessName: '山本農園',
          prefectureId: 20,
          prefectureName: '長野県',
          city: '安曇野市',
        },
        nextStartAt: `${daysFromNow(10)}T10:00:00+09:00`,
      },
    ],
    total: 4,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { experiencesList };
