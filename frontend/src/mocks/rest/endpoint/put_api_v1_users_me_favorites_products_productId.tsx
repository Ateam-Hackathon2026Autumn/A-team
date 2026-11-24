import type { RestMock } from '../../types';
import { putFavoriteProductMock } from '../store/favorites';

// 商品お気に入り登録API PUT /api/v1/users/me/favorites/products/:productId
const myFavoriteProductPut: RestMock = {
  method: 'PUT',
  path: '/api/v1/users/me/favorites/products/:productId',
  status: 204,
  handler: (url, init) => putFavoriteProductMock(url, init),
};

export { myFavoriteProductPut };
