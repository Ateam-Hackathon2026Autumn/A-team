import type { RestMock } from '../../types';

// 生産者一覧取得API GET /api/v1/producers
//
// 公開中の生産者6件。並び順は sort=newest（承認日時の新しい順、既定）を想定。
// badges はサーバーが導出し、該当するものだけを次の順で返す:
//   featured（注目） / new_farmer（就業5年以内の新規就農） / new_participant（承認から30日未満の新規参加）
//   / accepts_experience（体験受け入れ中） / recruiting（担い手募集中）
//
// 該当なし（絞り込み結果0件、ページ範囲外など）:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
//
// 新規就農者だけ（?newFarmer=true）の場合は id 5・6 の2件、total: 2
const producersList: RestMock = {
  method: 'GET',
  path: '/api/v1/producers',
  status: 200,
  body: {
    items: [
      {
        id: 5,
        businessName: 'そら野菜畑',
        genre: 'agriculture',
        prefectureId: 12,
        prefectureName: '千葉県',
        city: '南房総市',
        productionItems: '野菜',
        profileImageUrl: 'https://picsum.photos/seed/producer5-profile/800/600',
        coverImageUrl: 'https://picsum.photos/seed/producer5-cover/800/600',
        careerStartYear: 2024,
        foundedYear: 2024,
        acceptsExperience: false,
        recruiting: false,
        badges: ['new_farmer', 'new_participant'],
      },
      {
        id: 6,
        businessName: 'ひだまり養鶏',
        genre: 'livestock',
        prefectureId: 3,
        prefectureName: '岩手県',
        city: '遠野市',
        productionItems: '卵',
        profileImageUrl: 'https://picsum.photos/seed/producer6-profile/800/600',
        coverImageUrl: 'https://picsum.photos/seed/producer6-cover/800/600',
        careerStartYear: 2023,
        foundedYear: 2023,
        acceptsExperience: false,
        recruiting: false,
        badges: ['new_farmer'],
      },
      {
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
        badges: ['featured', 'accepts_experience', 'recruiting'],
      },
      {
        id: 2,
        businessName: '海風水産',
        genre: 'fishery',
        prefectureId: 22,
        prefectureName: '静岡県',
        city: '沼津市',
        productionItems: '干物・鮮魚',
        profileImageUrl: 'https://picsum.photos/seed/producer2-profile/800/600',
        coverImageUrl: 'https://picsum.photos/seed/producer2-cover/800/600',
        careerStartYear: 2008,
        foundedYear: 1975,
        acceptsExperience: true,
        recruiting: true,
        badges: ['featured', 'accepts_experience', 'recruiting'],
      },
      {
        id: 3,
        businessName: '北の丘ファーム',
        genre: 'livestock',
        prefectureId: 1,
        prefectureName: '北海道',
        city: '十勝',
        productionItems: '乳製品・牛肉',
        profileImageUrl: 'https://picsum.photos/seed/producer3-profile/800/600',
        coverImageUrl: 'https://picsum.photos/seed/producer3-cover/800/600',
        careerStartYear: 2010,
        foundedYear: 1988,
        acceptsExperience: true,
        recruiting: true,
        badges: ['featured', 'accepts_experience', 'recruiting'],
      },
      {
        // 画像なし（null）の表示確認用
        id: 4,
        businessName: '棚田のこめ',
        genre: 'agriculture',
        prefectureId: 15,
        prefectureName: '新潟県',
        city: '魚沼市',
        productionItems: '米',
        profileImageUrl: 'https://picsum.photos/seed/producer4-profile/800/600',
        coverImageUrl: null,
        careerStartYear: 1998,
        foundedYear: 1950,
        acceptsExperience: false,
        recruiting: false,
        badges: ['featured'],
      },
    ],
    total: 6,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { producersList };
