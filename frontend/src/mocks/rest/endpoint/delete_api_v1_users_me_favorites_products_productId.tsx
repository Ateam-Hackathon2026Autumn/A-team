import type { RestMock } from '../../types';
import { deleteFavoriteProductMock } from '../store/favorites';

// 商品お気に入り解除API DELETE /api/v1/users/me/favorites/products/:productId
const myFavoriteProductDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/users/me/favorites/products/:productId',
  status: 204,
  handler: (url) => deleteFavoriteProductMock(url),
};

export { myFavoriteProductDelete };
