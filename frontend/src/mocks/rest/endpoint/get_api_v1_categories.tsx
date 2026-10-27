import type { RestMock } from '../../types';

// カテゴリー一覧取得API GET /api/v1/categories
//
// 商品カテゴリーのマスタを全件返す（sortOrder 昇順）。商品0件のカテゴリーも含む
//
// マスタ0件:
//   { items: [] }
const categoriesList: RestMock = {
  method: 'GET',
  path: '/api/v1/categories',
  status: 200,
  body: {
    items: [
      { id: 1, name: '野菜', sortOrder: 1 },
      { id: 2, name: '果物', sortOrder: 2 },
      { id: 3, name: '米', sortOrder: 3 },
      { id: 4, name: 'お茶', sortOrder: 4 },
      { id: 5, name: '魚介類', sortOrder: 5 },
      { id: 6, name: '肉', sortOrder: 6 },
      { id: 7, name: 'その他', sortOrder: 7 },
    ],
  },
};

export { categoriesList };
