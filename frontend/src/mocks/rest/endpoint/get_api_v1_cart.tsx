import type { RestMock } from '../../types';

// カート取得API GET /api/v1/cart
//
// 商品1「安曇野ふじ」×1 と 商品6「あじの開き干し」×2 が入っている状態。
// itemsTotal は商品小計の合計で、送料は含めない（送料は注文時に確定）
//
// カートが空:
//   { items: [], itemsTotal: 0, canCheckout: false, quoteToken: 'mock-quote-token-empty' }
//
// 購入できない明細がある場合（canCheckout: false）の明細例:
//   { id: 3, productId: 3, productName: null, quantity: 1, unitPrice: null, subtotal: null,
//     purchasable: false, unavailableReason: 'PRODUCT_UNAVAILABLE' }
const cart: RestMock = {
  method: 'GET',
  path: '/api/v1/cart',
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
    ],
    itemsTotal: 11200,
    canCheckout: true,
    quoteToken: 'mock-quote-token-cart-v1',
  },
};

export { cart };
