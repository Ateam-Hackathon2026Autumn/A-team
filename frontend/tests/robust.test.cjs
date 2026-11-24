const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function runtime(replies = []) {
  const calls = [];
  const cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify({ DEV: true, VITE_USE_MOCK: 'false' }));
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} };
    cache.set(filename, module);
    const context = vm.createContext({ module, exports: module.exports, Response, URL, console,
      fetch: async (url, init) => {
        calls.push({ url, init });
        assert.ok(replies.length, `Unexpected request: ${url}`);
        return replies.shift();
      },
      require: (name) => {
        if (!name.startsWith('.')) return require(name);
        const base = path.resolve(path.dirname(filename), name);
        const resolved = ['.tsx', '.ts'].map(ext => base + ext).find(fs.existsSync);
        assert.ok(resolved, `Module not found: ${name}`);
        return load(resolved);
      },
    });
    new vm.Script(code, { filename }).runInContext(context);
    return module.exports;
  }
  return { calls, load: relative => load(path.resolve(__dirname, '../src', relative)) };
}
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

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
  assert.equal(r.calls[1].init.headers['X-CSRFToken'], 'csrf');
  assert.deepEqual(JSON.parse(r.calls[1].init.body), { uid: 'MQ', token: 'token-123', newPassword: 'NewPassword123!' });
});
