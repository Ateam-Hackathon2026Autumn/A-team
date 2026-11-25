import { producersList } from './get_api_v1_producers';
import type { ProducerSummary, ProducerProfile } from '../../../types/producer';
import type { RestMock } from '../../types';
import { isProducerFavorited } from '../store/favorites';

// 生産者プロフィール取得API GET /api/v1/producers/:producerId
//
// 生産者1「山本農園」のプロフィール（バッジ含む）。
// 商品・体験・求人はこのレスポンスに含めず、各一覧APIに producerId を指定して取得する
//
// 不存在・未承認・非公開・停止中（404）:
//   { errorCode: 'PRODUCER_NOT_FOUND', errorMsg: '生産者が見つかりません。' }
const producerProfile: RestMock = {
  method: 'GET',
  path: '/api/v1/producers/:producerId',
  status: 200,
  body: {
    id: 1,
    businessName: '山本農園',
    genre: 'agriculture',
    prefectureId: 20,
    prefectureName: '長野県',
    city: '安曇野市',
    productionItems: 'りんご・ぶどう',
    profileImageUrl: 'https://picsum.photos/seed/producer1-profile/800/600',
    coverImageUrl: 'https://picsum.photos/seed/producer1-cover/800/600',
    careerStartYear: 2015,
    foundedYear: 1962,
    acceptsExperience: true,
    recruiting: true,
    badges: ['accepts_experience', 'recruiting'],
    representativeName: '山本 健太',
    intro: '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご。三代目として減農薬栽培に取り組んでいます。',
    images: [
      { id: 1, url: 'https://picsum.photos/seed/producer1-orchard/800/600', sortOrder: 1 },
      { id: 2, url: 'https://picsum.photos/seed/producer1-harvest/800/600', sortOrder: 2 },
      { id: 3, url: 'https://picsum.photos/seed/producer1-alps/800/600', sortOrder: 3 },
    ],
    hasPublicStory: true,
    isFavorited: false,
    craft: '樹上でじっくり完熟させてから収穫しています。見た目よりも、ひと口目の甘さと香りを大切にしています。',
    reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
    goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
  },
};

export { producerProfile };

producerProfile.handler = url => {
 const id = Number(url.pathname.split('/').at(-1));
 const producer = (producersList.body as { items: ProducerSummary[] }).items.find(item => item.id === id);
 if (!producer) return { status: 404, body: { errorMsg: '生産者が見つかりません。' } };
 const isFavorited = isProducerFavorited(id);
 if (id === 1) return { status: 200, body: { ...(producerProfile.body as ProducerProfile), isFavorited } };
 const body: ProducerProfile = { ...producer, foundedYear: producer.careerStartYear, representativeName: '生産者スタッフ', intro: `${producer.prefectureName}${producer.city}で${producer.productionItems}を生産しています。産地から食卓へ、おいしさをお届けします。`, images: [], hasPublicStory: [2, 3].includes(id), isFavorited };
 return { status: 200, body };
};
