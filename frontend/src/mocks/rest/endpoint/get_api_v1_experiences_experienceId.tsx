import type { Experience, ExperienceDetail } from '../../../types/experience';
import { experiencesList } from './get_api_v1_experiences';
import type { RestMock } from '../../types';
import { daysFromNow } from '../../helpers';

// 体験詳細取得API GET /api/v1/experiences/{experienceId}
//
// 一覧のIDに対応する詳細を返す。体験1以外の詳細は画面確認用の簡易データ。
// slots は将来の開催枠（満席も含む）。remainingCapacity = 定員 - 予約数（満席は 0）
// quoteToken は申込API（POST /api/v1/experiences/:experienceId/applications）にそのまま渡す
//
// 存在しない・非公開の場合（status: 404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '体験が見つかりません。' }
const experienceDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/experiences/:experienceId',
  status: 200,
  body: {
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
    description:
      '北アルプスのふもと、安曇野の山本農園で蜜入りの「ふじ」を収穫します。\n' +
      '収穫したりんごを使って、農園のキッチンでアップルパイを焼きましょう。三代目の園主が、減農薬でのりんごづくりについてもお話しします。',
    images: [
      { id: 1, url: 'https://picsum.photos/seed/exp1-harvest/800/600', sortOrder: 0 },
      { id: 2, url: 'https://picsum.photos/seed/exp1-pie/800/600', sortOrder: 1 },
      { id: 3, url: 'https://picsum.photos/seed/exp1-orchard/800/600', sortOrder: 2 },
    ],
    place: '長野県安曇野市 山本農園（集合：農園事務所前）',
    ageCondition: '小学生以上',
    flow: [
      '10:00 農園事務所前に集合・あいさつ',
      '10:15 りんご畑で収穫体験',
      '11:30 アップルパイづくり',
      '12:30 試食・お土産のりんごを選ぶ',
      '13:00 解散',
    ],
    belongings: ['汚れてもよい服装', '長靴または歩きやすい靴', '軍手', 'エプロン'],
    notes: ['雨天時は収穫を中止し、アップルパイづくりのみ行います。', '収穫したりんごは 1 人 2kg までお持ち帰りいただけます。'],
    cancelPolicy: '開催日の 3 日前までは無料でキャンセルできます。2 日前以降のキャンセルは参加費の 50%、当日は 100% をいただきます。',
    slots: {
      items: [
        {
          id: 1,
          startAt: `${daysFromNow(10)}T10:00:00+09:00`,
          durationMin: 180,
          capacity: 20,
          remainingCapacity: 4,
          quoteToken: 'mock-quote-token-exp1-slot1',
        },
        {
          id: 2,
          startAt: `${daysFromNow(17)}T10:00:00+09:00`,
          durationMin: 180,
          capacity: 20,
          remainingCapacity: 17,
          quoteToken: 'mock-quote-token-exp1-slot2',
        },
      ],
      total: 2,
      page: 1,
      pageSize: 20,
      totalPages: 1,
    },
  },
};

export { experienceDetail };

export function getMockExperience(id: number): ExperienceDetail | undefined {
  const item = (experiencesList.body as { items: Experience[] }).items.find(item => item.id === id);
  if (!item) return undefined;
  const original = experienceDetail.body as ExperienceDetail;
  if (id === 1) return original;
  return {
    ...original, ...item,
    description: `${item.producer.businessName}が案内する「${item.title}」の体験です。詳細の説明はデモ用のサンプルです。`,
    images: item.thumbnailUrl ? [{ id: 1, url: item.thumbnailUrl, sortOrder: 0 }] : [],
    place: `${item.prefectureName} ${item.producer.city} ${item.producer.businessName}`,
    ageCondition: item.familyOk ? '小学生以上（子どもは保護者同伴）' : '大人対象',
    flow: ['集合・体験内容の説明', '生産者と一緒に体験', '振り返り・解散'],
    belongings: ['汚れてもよい服装', '飲み物'], notes: ['天候によって内容が変更になる場合があります。'],
    slots: { items: item.nextStartAt ? [{ id: id * 10, startAt: item.nextStartAt, durationMin: 120, capacity: 10, remainingCapacity: 5, quoteToken: `mock-quote-${id}` }] : [], total: item.nextStartAt ? 1 : 0, page: 1, pageSize: 20, totalPages: 1 },
  };
}
experienceDetail.handler = url => {
  const detail = getMockExperience(Number(url.pathname.split('/').at(-1)));
  return detail ? { status: 200, body: detail } : { status: 404, body: { errorCode: 'NOT_FOUND', errorMsg: '体験が見つかりません。' } };
};
