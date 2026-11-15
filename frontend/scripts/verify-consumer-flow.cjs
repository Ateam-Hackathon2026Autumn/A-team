// Run: node scripts/verify-consumer-flow.cjs
// Load the pure mock handlers without adding a test-runner dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const result = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
      fileName: filename,
    });
    module._compile(result.outputText, filename);
  };
}
const source = (name) => require(path.join(__dirname, '../src', name));
const saved = new Map();
global.window = { sessionStorage: { getItem: key => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value) } };
const { refreshMockCart, resetMockCart, mockCartBody } = source('mocks/rest/endpoint/get_api_v1_cart.tsx');
const { productDetail } = source('mocks/rest/endpoint/get_api_v1_products_productId.tsx');
const { consumerShippingGroups } = source('utils/consumerCheckout.ts');
const { createDemoConsumerOrder, consumerDemoOrders } = source('mocks/rest/store/consumerOrders.ts');
const { myOrdersList } = source('mocks/rest/endpoint/get_api_v1_users_me_orders.tsx');
const { myOrderDetail } = source('mocks/rest/endpoint/get_api_v1_users_me_orders_orderId.tsx');
const { producerProfile } = source('mocks/rest/endpoint/get_api_v1_producers_producerId.tsx');
const { usersMe } = source('mocks/rest/endpoint/get_api_v1_users_me.tsx');
const { usersMeUpdate } = source('mocks/rest/endpoint/patch_api_v1_users_me.tsx');
const url = new URL('https://mock.local/api/v1/orders');
const post = (input, key = crypto.randomUUID()) => createDemoConsumerOrder(url, {
  body: JSON.stringify(input), headers: { 'Idempotency-Key': key },
});
resetMockCart();
const cart = structuredClone(refreshMockCart());
const products = cart.items.map(item => productDetail.handler(new URL(`https://mock.local/api/v1/products/${item.productId}`)).body);
const shipping = consumerShippingGroups(cart, products);
assert.equal(shipping.length, 2, 'Group by producer and temperature zone');
const input = {
  shippingAddress: { lastName: 'Test', firstName: 'User', postalCode: '123-4567', prefecture: '東京都', city: 'テスト市', addressLine1: '1-2-3', addressLine2: '', phone: '09012345678' },
  paymentMethod: 'card', quoteToken: cart.quoteToken,
  expectedGrandTotal: cart.itemsTotal + shipping.reduce((sum, box) => sum + box.shippingFee, 0),
};
assert.equal(post(null).status, 400, 'Reject malformed input');
assert.equal(post({ ...input, expectedGrandTotal: 1 }).status, 409, 'Reject changed price');
assert.equal(post({ ...input, quoteToken: 'old' }).status, 409, 'Reject stale cart');
assert.equal(consumerDemoOrders.length, 0, 'Failed requests create no orders');
const key = crypto.randomUUID();
const receipt = post(input, key);
assert.equal(receipt.status, 201);
assert.equal(receipt.body.paymentStatus, 'pending', 'Receipt never pretends payment succeeded');
assert.equal(refreshMockCart().items.length, 0, 'Accepted order clears the cart');
assert.deepEqual(post(input, key), receipt, 'Retry returns the original receipt');
assert.equal(consumerDemoOrders.length, 1, 'Retry creates no duplicate orders');
assert.equal(post({ ...input, expectedGrandTotal: 0 }, key).status, 409, 'Reject key reuse for different input');
const order = myOrderDetail.handler(new URL(`https://mock.local/api/v1/users/me/orders/${receipt.body.id}`));
assert.equal(order.status, 200);
assert.equal(order.body.grandTotal, input.expectedGrandTotal);
assert.equal(order.body.shipments.flatMap(box => box.items).reduce((sum, item) => sum + item.subtotal, 0), cart.itemsTotal);
assert.equal(myOrdersList.handler(new URL('https://mock.local/api/v1/users/me/orders')).body.items[0].id, receipt.body.id);
assert.equal(myOrderDetail.handler(new URL('https://mock.local/api/v1/users/me/orders/999999')).status, 404);
assert.equal(producerProfile.handler(new URL('https://mock.local/api/v1/producers/5')).body.id, 5);
assert.equal(producerProfile.handler(new URL('https://mock.local/api/v1/producers/999999')).status, 404);
const updated = { ...usersMe.body.profile, lastName: '更新', firstName: '確認' };
assert.equal(usersMeUpdate.handler(url, { body: JSON.stringify(updated) }).status, 200);
assert.equal(usersMe.body.user.lastName, '更新', 'Profile changes appear in the next GET');
assert.equal(usersMeUpdate.handler(url, { body: 'null' }).status, 400);
// The tests run in an isolated process; no browser session or real order is modified.
assert.equal(mockCartBody.items.length, 0);
console.log('Consumer flow checks passed: price/stale-cart rejection, idempotency, order history/detail, producer IDs, profile updates.');
