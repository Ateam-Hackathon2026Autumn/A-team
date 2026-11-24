import type { RestMock } from '../../types';
import { putFavoriteProducerMock } from '../store/favorites';

// 生産者お気に入り登録API PUT /api/v1/users/me/favorites/producers/:producerId
const myFavoriteProducerPut: RestMock = {
  method: 'PUT',
  path: '/api/v1/users/me/favorites/producers/:producerId',
  status: 204,
  handler: (url, init) => putFavoriteProducerMock(url, init),
};

export { myFavoriteProducerPut };
