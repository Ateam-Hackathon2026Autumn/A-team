import type { RestMock } from '../../types';
import { mockCartBody, refreshMockCart } from './get_api_v1_cart';
import { productSamples } from './get_api_v1_products';

// カート商品数量変更API PATCH /api/v1/cart/items/:itemId
//
// 指定した明細の数量を変更した後のカートを返す。
// quantity は変更後の数量（1〜10）。0 にしたい場合は削除APIを使う
//
// 明細が存在しない・他人の明細（404）:
//   { errorCode: 'CART_ITEM_NOT_FOUND', errorMsg: 'カートの商品が見つかりません。' }
//
// 在庫不足など（409）:
//   { errorCode: 'CONFLICT', errorMsg: '在庫が不足しているため、数量を変更できません。' }
//
// カートが他で更新されていた（412）:
//   { errorCode: 'CART_CHANGED', errorMsg: 'カートの内容が変更されました。もう一度ご確認ください。' }
const cartItemUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/cart/items/:itemId',
  status: 200,
  handler(url, init) {
    const itemId = Number(url.pathname.split('/').at(-1));
    const item = mockCartBody.items.find((line) => line.id === itemId);
    if (!item) return { status: 404, body: { errorCode: 'CART_ITEM_NOT_FOUND' } };
    let input: unknown;
    try { input = JSON.parse(String(init?.body ?? '')); }
    catch { return { status: 400, body: { errorCode: 'VALIDATION_ERROR' } }; }
    if (typeof input !== 'object' || input === null || !('quantity' in input)
      || typeof input.quantity !== 'number' || !Number.isInteger(input.quantity) || input.quantity < 1 || input.quantity > 10) {
      return { status: 400, body: { errorCode: 'VALIDATION_ERROR' } };
    }
    const product = productSamples.find((p) => p.id === item.productId);
    if (!product || product.stock < input.quantity) return { status: 409, body: { errorCode: 'CONFLICT' } };
    item.quantity = input.quantity;
    return { status: 200, body: refreshMockCart(true) };
  },
};

export { cartItemUpdate };
