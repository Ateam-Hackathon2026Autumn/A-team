import { hoursFromNow } from '../../helpers';
import type { RestMock } from '../../types';
import { getFavoritesMock } from '../store/favorites';

// お気に入り一覧取得API GET /api/v1/users/me/favorites?type=product|producer
const myFavoritesList: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me/favorites',
  status: 200,
  body: {
    items: [
      {
        product: {
          id: 4,
          name: '朝どれ旬野菜セット M（8〜10品）',
          volume: '8〜10品',
          price: 2980,
          discountRate: null,
          salePrice: 2980,
          taxRate: 8,
          ratingAvg: 4.6,
          reviewCount: 41,
          stock: 15,
          isSubscription: false,
          isPreorder: false,
          thumbnailUrl: 'https://picsum.photos/seed/product4/800/600',
          isFavorited: true,
          category: { id: 1, name: '野菜', sortOrder: 1 },
          producer: {
            id: 5,
            businessName: 'そら野菜畑',
            prefectureId: 12,
            prefectureName: '千葉県',
            city: '南房総市',
          },
        },
        isPublic: true,
        favoritedAt: hoursFromNow(-24 * 2),
      },
    ],
    total: 1,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
  handler: (url) => getFavoritesMock(url),
};

export { myFavoritesList };
