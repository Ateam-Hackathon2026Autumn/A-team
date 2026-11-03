import type { RestMock } from '../../types';
import type { Cart } from '../../../types/cart';
import { productSamples } from './get_api_v1_products';

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
const cartSnapshot = {
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

const storageKey = 'tsunagaru-marche.mock-cart.v1';
let revision = 1;

function restoreCart(): Cart | null {
  try {
    const saved: unknown = JSON.parse(window.sessionStorage.getItem(storageKey) ?? 'null');
    if (typeof saved !== 'object' || saved === null || !('items' in saved) || !Array.isArray(saved.items)
      || !('revision' in saved) || !Number.isSafeInteger(saved.revision) || Number(saved.revision) < 1) return null;
    const ids = new Set<number>();
    const productIds = new Set<number>();
    const items: Cart['items'] = [];
    const entries: unknown[] = saved.items;
    for (const item of entries) {
      if (typeof item !== 'object' || item === null
        || !('id' in item) || typeof item.id !== 'number' || !Number.isSafeInteger(item.id) || item.id < 1
        || !('productId' in item) || typeof item.productId !== 'number' || !Number.isSafeInteger(item.productId) || item.productId < 1
        || !('quantity' in item) || typeof item.quantity !== 'number' || !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 10
        || ids.has(item.id) || productIds.has(item.productId)) return null;
      ids.add(item.id);
      productIds.add(item.productId);
      items.push({ id: item.id, productId: item.productId, quantity: item.quantity,
        productName: null, unitPrice: null, subtotal: null, purchasable: false, unavailableReason: null });
    }
    revision = Number(saved.revision);
    return { items, itemsTotal: 0, canCheckout: false, quoteToken: '' };
  } catch {
    // 保存領域を利用できない場合や破損時も、メモリー上でデモを利用できる。
    return null;
  }
}

export const mockCartBody: Cart = restoreCart() ?? structuredClone(cartSnapshot.body);

// GET・追加・数量変更・削除で、同じカートと最新の商品情報を使用する。
export function refreshMockCart(changed = false): Cart {
  for (const item of mockCartBody.items) {
    const product = productSamples.find((p) => p.id === item.productId);
    item.productName = product?.name ?? null;
    item.unitPrice = product?.salePrice ?? null;
    item.subtotal = product ? product.salePrice * item.quantity : null;
    item.purchasable = Boolean(product && product.stock >= item.quantity);
    item.unavailableReason = !product ? 'PRODUCT_UNAVAILABLE' : !item.purchasable ? 'INSUFFICIENT_STOCK' : null;
  }
  mockCartBody.itemsTotal = mockCartBody.items.reduce((sum, item) => sum + (item.subtotal ?? 0), 0);
  mockCartBody.canCheckout = mockCartBody.items.length > 0 && mockCartBody.items.every((item) => item.purchasable);
  if (changed) revision += 1;
  mockCartBody.quoteToken = `mock-quote-token-cart-v${revision}`;
  try {
    // 金額や購入可否は保存値を信用せず、商品データから毎回計算する。
    window.sessionStorage.setItem(storageKey, JSON.stringify({
      items: mockCartBody.items.map(({ id, productId, quantity }) => ({ id, productId, quantity })),
      revision,
    }));
  } catch {
    // 保存に失敗しても、実行中のカート操作は継続する。
  }
  return mockCartBody;
}

export function resetMockCart(): Cart {
  Object.assign(mockCartBody, structuredClone(cartSnapshot.body));
  return refreshMockCart(true);
}

const cart: RestMock = {
  ...cartSnapshot,
  handler: () => ({ status: 200, body: refreshMockCart() }),
};

export { cart };
