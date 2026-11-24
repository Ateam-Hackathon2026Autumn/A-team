// Run from frontend: node scripts/verify-consumer-review.cjs
// API transport is replaced: this script never sends a real order or payment.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const result = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    });
    module._compile(result.outputText, filename);
  };
}
const source = name => require(path.join(__dirname, '../src', name));
const envPath = require.resolve('../src/config/env.tsx');
require.cache[envPath] = { id: envPath, filename: envPath, loaded: true, exports: { USE_MOCK: false, VITE_API_URL: '' } };
const calls = [];
const cart = {
  items: [{ id: 1, productId: 1, productName: 'サーバーの見積り', quantity: 1, unitPrice: 10000, subtotal: 10000, purchasable: true, unavailableReason: null }],
  shipments: [{ producerId: 7, producerName: '見積り生産者', temperatureZone: 'normal', itemIds: [1], itemsTotal: 10000, shippingFee: 2345, freeShippingThreshold: null }],
  itemsTotal: 10000, shippingTotal: 2345, total: 12345, canCheckout: true,
};
const json = body => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
global.fetch = async (url, init = {}) => {
  calls.push({ url, init });
  if (url === '/api/v1/auth/csrf') return json({ csrfToken: 'test-csrf' });
  if (url === '/api/v1/cart') return json(cart);
  if (url === '/api/v1/orders') return json({ id: 123, checkoutUrl: 'https://checkout.stripe.com/c/pay/test-session', paymentStatus: 'pending' });
  const parsed = new URL(url, 'https://test.local');
  const page = Number(parsed.searchParams.get('page') ?? 1);
  if (parsed.pathname === '/api/v1/users/me/orders') return json({ items: [], total: 0, page, pageSize: 20, totalPages: 0 });
  return json({ items: [{ id: page, producer: { id: 7 } }], total: 2, page, pageSize: 20, totalPages: 2 });
};
async function main() {
  const { createConsumerOrder, getConsumerOrders } = source('api/consumerOrderApi.ts');
  const input = {
    shippingAddress: { lastName: 'Test', firstName: 'User', postalCode: '123-4567', prefecture: '東京都', city: 'テスト市', addressLine1: '1-2-3', addressLine2: '', phone: '09012345678' },
    paymentMethod: 'card', expectedGrandTotal: cart.total, quoteToken: 'must-not-be-sent',
  };
  const receipt = await createConsumerOrder(input, 'test-key');
  assert.equal(receipt.checkoutUrl, 'https://checkout.stripe.com/c/pay/test-session');
  let request = calls.find(call => call.url === '/api/v1/orders');
  const body = JSON.parse(request.init.body);
  assert.deepEqual(Object.keys(body).sort(), ['expectedGrandTotal', 'paymentMethod', 'shippingAddress']);
  assert.equal(body.expectedGrandTotal, cart.total);
  assert.equal(request.init.headers.get('X-CSRFToken'), 'test-csrf');
  calls.length = 0;
  await createConsumerOrder({ addressId: 9, paymentMethod: 'card', expectedGrandTotal: cart.total }, 'address-key');
  assert.deepEqual(JSON.parse(calls.find(call => call.url === '/api/v1/orders').init.body), { addressId: 9, paymentMethod: 'card', expectedGrandTotal: cart.total });
  calls.length = 0;
  await getConsumerOrders({ paymentStatus: 'paid', page: 2 });
  assert.equal(calls.length, 1, 'Fetch one order page, not all orders');
  let query = new URL(calls[0].url, 'https://test.local').searchParams;
  assert.equal(query.get('paymentStatus'), 'paid');
  assert.equal(query.get('page'), '2');
  await getConsumerOrders({ page: 1 });
  assert.equal(new URL(calls[1].url, 'https://test.local').searchParams.has('paymentStatus'), false);
  for (const [api, method, route] of [['experienceApi.ts', 'getExperiences', '/api/v1/experiences'], ['jobApi.ts', 'getJobs', '/api/v1/jobs']]) {
    calls.length = 0;
    await source(`api/${api}`)[method](undefined, { producerId: 7 });
    assert.equal(calls.length, 2);
    for (const [index, call] of calls.entries()) {
      const url = new URL(call.url, 'https://test.local');
      assert.equal(url.pathname, route);
      assert.equal(url.searchParams.get('producerId'), '7', 'Keep producer filter on subsequent pages');
      assert.equal(url.searchParams.get('page'), String(index + 1));
    }
  }
  for (const [endpoint, name] of [['get_api_v1_experiences.tsx', 'experiencesList'], ['get_api_v1_jobs.tsx', 'jobsList']]) {
    const mock = source(`mocks/rest/endpoint/${endpoint}`)[name];
    const result = mock.handler(new URL('https://test.local/list?producerId=1&pageSize=1&page=1'));
    assert.equal(result.body.items.length, 1);
    assert.equal(result.body.items[0].producer.id, 1);
    assert.equal(mock.handler(new URL('https://test.local/list?producerId=999')).body.total, 0);
  }
  const { myOrdersList } = source('mocks/rest/endpoint/get_api_v1_users_me_orders.tsx');
  const paid = myOrdersList.handler(new URL('https://test.local/list?paymentStatus=paid&pageSize=1&page=2'));
  assert.equal(paid.body.items.length, 1);
  assert.equal(paid.body.items[0].paymentStatus, 'paid');
  assert.equal(paid.body.page, 2);
  assert.equal(paid.body.total, 2);

  // Render loaded-state branches to catch contract/role/null display regressions.
  const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const { MemoryRouter } = require('react-router');
  const { Provider, createStore } = require('jotai');
  const { loginStatusAtom, userInfoAtom } = source('stores/userAtom.tsx');
  const { usersMe } = source('mocks/rest/endpoint/get_api_v1_users_me.tsx');
  const account = usersMe.body;
  let queue = [];
  source('hooks/usePublicContent.ts').usePublicContent = () => ({ data: queue.shift(), loading: false, error: '', retry() {} });
  const render = (component, data, user = account.user, loggedIn = true) => {
    queue = [...data];
    const store = createStore();
    store.set(loginStatusAtom, loggedIn ? 'loggedIn' : 'loggedOut');
    store.set(userInfoAtom, user);
    return renderToStaticMarkup(React.createElement(Provider, { store }, React.createElement(MemoryRouter, null, React.createElement(component))));
  };
  const Header = source('components/layout/Header.tsx').default;
  assert.ok(!render(Header, [], null, false).includes('利用画面の切り替え'));
  assert.ok(!render(Header, [], { ...account.user, isProducer: false, producerApplicationStatus: 'not_applied' }).includes('利用画面の切り替え'));
  assert.ok(render(Header, []).includes('利用画面の切り替え'));
  assert.ok(render(Header, [], { ...account.user, isProducer: false, producerApplicationStatus: 'pending' }).includes('利用画面の切り替え'));
  assert.ok(!render(Header, []).includes('管理者'));
  const checkout = render(source('pages/CheckoutPage.tsx').default, [cart]);
  assert.ok(checkout.includes('12,345'), 'Render the API total');
  assert.ok(checkout.includes('2,345'), 'Render the API shipping fee');
  assert.ok(checkout.includes('見積り生産者'));
  assert.ok(!checkout.includes('注文受付（準備中）'));
  const profile = render(source('pages/ProfileEditPage.tsx').default, [account]);
  assert.equal((profile.match(/maxLength="10"/gi) ?? []).length, 2);
  const producer = source('mocks/rest/endpoint/get_api_v1_producers_producerId.tsx').producerProfile.body;
  const ProducerProfile = source('pages/ProducerProfilePage.tsx').default;
  let html = render(ProducerProfile, [{ ...producer, foundedYear: null, careerStartYear: null }, null]);
  assert.ok(!html.includes('創業') && !html.includes('年から生産に従事'));
  html = render(ProducerProfile, [{ ...producer, foundedYear: 2000, careerStartYear: null }, null]);
  assert.ok(html.includes('創業 2000年') && !html.includes('年から生産に従事'));
  html = render(ProducerProfile, [{ ...producer, foundedYear: null, careerStartYear: 2010 }, null]);
  assert.ok(!html.includes('創業') && html.includes('2010年から生産に従事'));
  console.log('Consumer review checks passed: live-mode request contract, API filters/pagination, cart totals, role visibility, name limit, nullable years.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
