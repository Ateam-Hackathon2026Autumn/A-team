const { test } = require('node:test');
const assert = require('node:assert/strict');
const { runtime: createRuntime, json } = require('./helpers/frontend-runtime.cjs');
const runtime = (replies = []) => createRuntime({ replies });

test('global server errors handle GET only while write failures stay with callers', async () => {
  const r = runtime([json({}, 503), json({ csrfToken: 'csrf' }), json({ errorCode: 'PAYMENT_UNAVAILABLE' }, 503), json({}, 503), json({}, 503), json({}, 503), json({}, 401)]);
  const { apiFetch, setApiFailureHandler } = r.load('api/client.tsx');
  const failures = [];
  setApiFailureHandler((status, path, method) => failures.push({ status, path, method }));
  for (const method of ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'POST']) {
    await apiFetch('/api/v1/orders', { method });
  }
  assert.deepEqual(failures, [
    { status: 503, path: '/api/v1/orders', method: 'GET' },
    { status: 401, path: '/api/v1/orders', method: 'POST' },
  ]);
  setApiFailureHandler(null);
});

test('order creation retries CSRF failure once with the same idempotency key and body', async () => {
  const receipt = { id: 25, orderNo: 'ORD-25', checkoutUrl: '/checkout/complete?orderId=25' };
  const r = runtime([
    json({ csrfToken: 'old' }),
    json({ errorCode: 'CSRF_FAILED', errorMsg: 'CSRF token expired' }, 403),
    json({ csrfToken: 'new' }),
    json(receipt, 201),
  ]);
  const input = { shippingAddress: { lastName: '山田', firstName: '花子', postalCode: '100-0001', prefecture: '東京都', city: '千代田区', addressLine1: '千代田1', addressLine2: '', phone: '09012345678' }, paymentMethod: 'card', expectedGrandTotal: 3000 };
  const result = await r.load('api/consumerOrderApi.ts').createConsumerOrder(input, 'same-key');
  assert.equal(result.id, 25);
  assert.equal(r.calls.length, 4);
  assert.equal(r.calls[1].init.headers.get('Idempotency-Key'), 'same-key');
  assert.equal(r.calls[3].init.headers.get('Idempotency-Key'), 'same-key');
  assert.equal(r.calls[1].init.body, r.calls[3].init.body);
  assert.equal(r.calls[1].init.headers.get('X-CSRFToken'), 'old');
  assert.equal(r.calls[3].init.headers.get('X-CSRFToken'), 'new');
});

test('checkout destinations accept only this origin or Stripe Checkout over HTTPS', () => {
  const { safeCheckoutUrl } = runtime().load('utils/checkoutUrl.ts');
  const origin = 'http://localhost:5173';
  assert.equal(safeCheckoutUrl('/checkout/complete?orderId=1', origin), 'http://localhost:5173/checkout/complete?orderId=1');
  assert.equal(safeCheckoutUrl('https://checkout.stripe.com/c/pay/abc', origin), 'https://checkout.stripe.com/c/pay/abc');
  for (const value of ['javascript:alert(1)', 'https://evil.test/', 'https://checkout.stripe.com.evil.test/', 'http://checkout.stripe.com/', '//evil.test/', 'https://user@checkout.stripe.com/']) {
    assert.equal(safeCheckoutUrl(value, origin), null, value);
  }
});

test('dynamic IDs accept only positive safe decimal integers', () => {
  const { isValidRouteId } = runtime().load('utils/routeId.ts');
  for (const value of ['1', '123']) assert.equal(isValidRouteId(value), true);
  for (const value of [undefined, 'abc', '0', '-1', '1.2', '1e2', '01', '9007199254740992']) assert.equal(isValidRouteId(value), false, value);
});

test('empty profile phone is omitted from PATCH and populated phone is normalized', async () => {
  for (const [phone, expected] of [[null, undefined], ['090-1234-5678', '09012345678']]) {
    const r = runtime([json({ csrfToken: 'csrf' }), json({ user: {}, profile: {} })]);
    await r.load('api/consumerAccountApi.ts').updateConsumerProfile({ lastName: '山田', firstName: '花子', phone, birthDate: '2000-01-01', prefectureId: null, interests: [] });
    assert.equal(JSON.parse(r.calls[1].init.body).phone, expected);
  }
});

test('password reset sends uid, token and newPassword with CSRF and cookies', async () => {
  const r = runtime([json({ csrfToken: 'csrf' }), json({ message: 'OK' })]);
  await r.load('api/authApi.tsx').confirmPasswordReset('MQ', 'token-123', 'NewPassword123!');
  assert.deepEqual(r.calls.map(call => call.url), ['/api/v1/auth/csrf', '/api/v1/auth/password-reset/confirm']);
  assert.equal(r.calls[1].init.credentials, 'include');
  assert.equal(r.calls[1].init.headers.get('X-CSRFToken'), 'csrf');
  assert.deepEqual(JSON.parse(r.calls[1].init.body), { uid: 'MQ', token: 'token-123', newPassword: 'NewPassword123!' });
});
