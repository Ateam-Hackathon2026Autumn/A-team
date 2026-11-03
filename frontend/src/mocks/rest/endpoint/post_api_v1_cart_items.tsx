import type { RestMock } from '../../types';
import { mockCartBody, refreshMockCart } from './get_api_v1_cart';
import { productSamples } from './get_api_v1_products';

// 同じタブのセッションに保存するデモカート。実際の購入・在庫更新は行わない。
const cartItemAdd: RestMock = {
  method: 'POST',
  path: '/api/v1/cart/items',
  status: 200,
  handler(_url, init) {
    let input: unknown;
    try { input = JSON.parse(String(init?.body ?? '')); }
    catch { return { status: 400, body: { errorCode: 'VALIDATION_ERROR' } }; }
    if (typeof input !== 'object' || input === null || !('productId' in input) || !('quantity' in input)) {
      return { status: 400, body: { errorCode: 'VALIDATION_ERROR' } };
    }
    const { productId, quantity } = input;
    if (typeof quantity !== 'number' || !Number.isInteger(quantity) || quantity < 1 || quantity > 10) {
      return { status: 400, body: { errorCode: 'VALIDATION_ERROR' } };
    }
    const product = productSamples.find((p) => p.id === productId);
    if (!product) return { status: 404, body: { errorCode: 'PRODUCT_NOT_FOUND' } };
    const existing = mockCartBody.items.find((item) => item.productId === productId);
    const totalQuantity = (existing?.quantity ?? 0) + quantity;
    if (totalQuantity > 10) return { status: 400, body: { errorCode: 'VALIDATION_ERROR' } };
    if (totalQuantity > product.stock) return { status: 409, body: { errorCode: 'CONFLICT' } };
    if (existing) {
      existing.quantity = totalQuantity;
      existing.subtotal = product.salePrice * totalQuantity;
    } else {
      mockCartBody.items.push({
        id: Math.max(0, ...mockCartBody.items.map((item) => item.id)) + 1,
        productId: product.id,
        productName: product.name,
        quantity,
        unitPrice: product.salePrice,
        subtotal: product.salePrice * quantity,
        purchasable: true,
        unavailableReason: null,
      });
    }
    return { status: 200, body: refreshMockCart(true) };
  },
};

export { cartItemAdd };
