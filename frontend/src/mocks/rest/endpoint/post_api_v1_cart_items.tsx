import type { RestMock } from '../../types';

// カート商品追加API POST /api/v1/cart/items
//
// GET /api/v1/cart の状態に、商品2「シャインマスカット」を1つ追加した後のカートを返す。
// 同じ商品を追加した場合は既存の数量に加算される（新規追加・加算どちらも 200）
//
// 商品が存在しない・公開対象外（404）:
//   { errorCode: 'PRODUCT_NOT_FOUND', errorMsg: '商品が見つかりません。' }
//
// 在庫不足など購入できない（409）:
//   { errorCode: 'CONFLICT', errorMsg: '在庫が不足しているため、カートに追加できません。' }
//
// カートが他で更新されていた（412）:
//   { errorCode: 'CART_CHANGED', errorMsg: 'カートの内容が変更されました。もう一度ご確認ください。' }
const cartItemAdd: RestMock = {
  method: 'POST',
  path: '/api/v1/cart/items',
  status: 200,
  body: {
    items: [
      {
        id: 1,
        productId: 1,
        productName: '安曇野ふじ 家庭用 5kg',
        quantity: 1,
        unitPrice: 4800,
        subtotal: 4800,
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
      {
        id: 3,
        productId: 2,
        productName: 'シャインマスカット 2房',
        quantity: 1,
        unitPrice: 5400,
        subtotal: 5400,
        purchasable: true,
        unavailableReason: null,
      },
    ],
    itemsTotal: 16600,
    canCheckout: true,
    quoteToken: 'mock-quote-token-cart-v2',
  },
};

export { cartItemAdd };
