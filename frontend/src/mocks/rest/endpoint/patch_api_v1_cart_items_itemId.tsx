import type { RestMock } from '../../types';

// カート商品数量変更API PATCH /api/v1/cart/items/:itemId
//
// GET /api/v1/cart の状態から、明細1「安曇野ふじ」の数量を 2 に変更した後のカートを返す。
// quantity は変更後の数量（1〜99）。0 にしたい場合は削除APIを使う
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
  body: {
    items: [
      {
        id: 1,
        productId: 1,
        productName: '安曇野ふじ 家庭用 5kg',
        quantity: 2,
        unitPrice: 4800,
        subtotal: 9600,
        purchasable: true,
        unavailableReason: null,
      },
      {
        id: 2,
        productId: 6,
        productName: '沼津 あじの開き干し 10枚',
        quantity: 2,
        unitPrice: 3200,
        subtotal: 6400,
        purchasable: true,
        unavailableReason: null,
      },
    ],
    itemsTotal: 16000,
    canCheckout: true,
    quoteToken: 'mock-quote-token-cart-v3',
  },
};

export { cartItemUpdate };
