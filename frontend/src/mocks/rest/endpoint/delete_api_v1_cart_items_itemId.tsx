import type { RestMock } from '../../types';

// カート商品削除API DELETE /api/v1/cart/items/:itemId
//
// 成功時は 204 で本文なし。削除後のカートは GET /api/v1/cart で取り直す
//
// 明細が存在しない・他人の明細（404）:
//   { errorCode: 'CART_ITEM_NOT_FOUND', errorMsg: 'カートの商品が見つかりません。' }
//
// カートが他で更新されていた（412）:
//   { errorCode: 'CART_CHANGED', errorMsg: 'カートの内容が変更されました。もう一度ご確認ください。' }
const cartItemDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/cart/items/:itemId',
  status: 204,
};

export { cartItemDelete };
