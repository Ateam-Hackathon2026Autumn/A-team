import type { RestMock } from '../../types';
import type { Cart, CartShipment } from '../../../types/cart';
import type { ProductDetail } from '../../../types/publicProduct';
import { productSamples } from './get_api_v1_products';
import { productDetail } from './get_api_v1_products_productId';

// カート取得API GET /api/v1/cart
//
// 商品1「安曇野ふじ」×1 と 商品6「あじの開き干し」×2 が入っている状態。
// 実APIと同じく、shipments・shippingTotal・totalにサーバー側の見積りを返す。
//
// カートが空:
//   { items: [], shipments: [], itemsTotal: 0, shippingTotal: 0, total: 0, canCheckout: false }
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
    shipments: [],
    shippingTotal: 0,
    total: 11200,
    canCheckout: true,
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
    return { items, shipments: [], itemsTotal: 0, shippingTotal: 0, total: 0, canCheckout: false };
  } catch {
    // 保存領域を利用できない場合や破損時も、メモリー上でデモを利用できる。
    return null;
  }
}

export const mockCartBody: Cart = structuredClone(cartSnapshot.body);
let initialized = false;

// 最初のモック操作時だけ保存内容を復元する。
export function initializeMockCart(): void {
  if (initialized) return;
  initialized = true;
  const restored = restoreCart();
  if (restored) Object.assign(mockCartBody, restored);
}

// GET・追加・数量変更・削除で、同じカートと最新の商品情報を使用する。
export function refreshMockCart(changed = false): Cart {
  initializeMockCart();
  for (const item of mockCartBody.items) {
    const product = productSamples.find((p) => p.id === item.productId);
    item.productName = product?.name ?? null;
    item.unitPrice = product?.salePrice ?? null;
    item.subtotal = product ? product.salePrice * item.quantity : null;
    item.purchasable = Boolean(product && (product.stock === null || product.stock >= item.quantity));
    item.unavailableReason = !product ? 'PRODUCT_UNAVAILABLE' : !item.purchasable ? 'INSUFFICIENT_STOCK' : null;
  }
  // モックサーバー側で見積りを作る。画面はこの結果をそのまま使用する。
  const boxes = new Map<string, CartShipment>();
  for (const item of mockCartBody.items.filter(line => line.purchasable)) {
    const product = productDetail.handler!(new URL(`/api/v1/products/${item.productId}`, 'https://mock.local')).body as ProductDetail;
    const key = `${product.producer.id}:${product.shipping.temperatureZone}`;
    const box = boxes.get(key) ?? {
      producerId: product.producer.id, producerName: product.producer.businessName,
      temperatureZone: product.shipping.temperatureZone, itemIds: [], itemsTotal: 0,
      shippingFee: product.shipping.shippingFee, freeShippingThreshold: product.shipping.freeShippingThreshold,
    };
    box.itemIds.push(item.id);
    box.itemsTotal += item.subtotal ?? 0;
    boxes.set(key, box);
  }
  mockCartBody.shipments = [...boxes.values()].map(box => ({ ...box,
    shippingFee: box.freeShippingThreshold !== null && box.itemsTotal >= box.freeShippingThreshold ? 0 : box.shippingFee,
  }));
  mockCartBody.itemsTotal = mockCartBody.shipments.reduce((sum, box) => sum + box.itemsTotal, 0);
  mockCartBody.shippingTotal = mockCartBody.shipments.reduce((sum, box) => sum + box.shippingFee, 0);
  mockCartBody.total = mockCartBody.itemsTotal + mockCartBody.shippingTotal;
  mockCartBody.canCheckout = mockCartBody.items.length > 0 && mockCartBody.items.every((item) => item.purchasable);
  if (changed) revision += 1;
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
  initializeMockCart();
  Object.assign(mockCartBody, structuredClone(cartSnapshot.body));
  return refreshMockCart(true);
}

const cart: RestMock = {
  ...cartSnapshot,
  handler: () => ({ status: 200, body: refreshMockCart() }),
};

export { cart };
