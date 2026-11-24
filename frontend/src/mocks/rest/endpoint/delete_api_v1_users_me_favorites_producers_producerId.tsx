import type { RestMock } from '../../types';
import { deleteFavoriteProducerMock } from '../store/favorites';

// 生産者お気に入り解除API DELETE /api/v1/users/me/favorites/producers/:producerId
const myFavoriteProducerDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/users/me/favorites/producers/:producerId',
  status: 204,
  handler: (url) => deleteFavoriteProducerMock(url),
};

export { myFavoriteProducerDelete };
