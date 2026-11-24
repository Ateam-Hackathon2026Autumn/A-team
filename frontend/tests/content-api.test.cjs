const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const root = path.resolve(__dirname, '../src');

function runtime(replies) {
  const calls = [];
  const cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify({ DEV: true, VITE_USE_MOCK: 'false' }));
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} };
    cache.set(filename, module);
    const context = vm.createContext({ module, exports: module.exports, Response, URL, URLSearchParams, console,
      fetch: async (url, init) => {
        calls.push({ url, init });
        assert.ok(replies.length, `Unexpected request: ${url}`);
        const reply = replies.shift();
        if (reply instanceof Error) throw reply;
        return reply;
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
  return { calls, load: name => load(path.join(root, name)) };
}

function assertWrite(calls, path, method, body, token = 'csrf') {
  assert.deepEqual(calls.map(call => call.url), ['/api/v1/auth/csrf', path]);
  assert.ok(calls.every(call => call.init.credentials === 'include'));
  assert.equal(calls[1].init.method, method);
  assert.equal(calls[1].init.headers['X-CSRFToken'], token);
  assert.deepEqual(JSON.parse(calls[1].init.body), body);
}

test('cart add, update and delete use backend routes and CSRF', async () => {
  const cart = { items: [], shipments: [], itemsTotal: 0, shippingTotal: 0, total: 0, canCheckout: false };
  const add = runtime([json({ csrfToken: 'csrf' }), json(cart)]);
  await add.load('api/cartApi.ts').addCartItem(12, 2);
  assertWrite(add.calls, '/api/v1/cart/items', 'POST', { productId: 12, quantity: 2 });

  const update = runtime([json({ csrfToken: 'csrf' }), json(cart)]);
  assert.deepEqual(JSON.parse(JSON.stringify(await update.load('api/cartApi.ts').updateCartItem(9, 3))), cart);
  assertWrite(update.calls, '/api/v1/cart/items/9', 'PATCH', { quantity: 3 });

  const remove = runtime([json({ csrfToken: 'csrf' }), new Response(null, { status: 204 })]);
  await remove.load('api/cartApi.ts').removeCartItem(9);
  assert.deepEqual(remove.calls.map(call => call.url), ['/api/v1/auth/csrf', '/api/v1/cart/items/9']);
  assert.equal(remove.calls[1].init.method, 'DELETE');
  assert.equal(remove.calls[1].init.headers['X-CSRFToken'], 'csrf');
  assert.equal(remove.calls[1].init.body, undefined);
});

test('content POST uses exact experience fields and job requirements confirmation', async () => {
  const experience = { slotId: 4, adultCount: 2, childCount: 1, infantCount: 1, lastName: '山田', firstName: '花子', phone: '09012345678', message: '', agreedToCancelPolicy: true, eligibilityConfirmed: true, expectedTotalAmount: 9000 };
  const exp = runtime([json({ csrfToken: 'csrf' }), json({ id: 7, reservationNo: 'R0007', totalAmount: 9000 }, 201)]);
  await exp.load('api/experienceApi.ts').applyExperience(2, experience);
  assertWrite(exp.calls, '/api/v1/experiences/2/applications', 'POST', experience);
  for (const key of ['quoteToken', 'representativeName', 'policyAgreed']) assert.ok(!Object.hasOwn(JSON.parse(exp.calls[1].init.body), key));

  const jobInput = { workDateIds: [8], message: 'よろしくお願いします', answers: [], requirementsConfirmed: true };
  const job = runtime([json({ csrfToken: 'csrf' }), json({ id: 5 }, 201)]);
  await job.load('api/jobApi.ts').applyJob(3, jobInput);
  assertWrite(job.calls, '/api/v1/jobs/3/applications', 'POST', jobInput);
});

test('content POST refreshes CSRF and retries once only for CSRF_FAILED', async () => {
  const r = runtime([json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED' }, 403), json({ csrfToken: 'new' }), json({ id: 5 }, 201)]);
  await r.load('api/publicContentApi.ts').submitContent('/api/v1/jobs/3/applications', { requirementsConfirmed: true });
  assert.deepEqual(r.calls.map(call => call.url), ['/api/v1/auth/csrf', '/api/v1/jobs/3/applications', '/api/v1/auth/csrf', '/api/v1/jobs/3/applications']);
  assert.equal(r.calls[1].init.headers['X-CSRFToken'], 'old');
  assert.equal(r.calls[3].init.headers['X-CSRFToken'], 'new');
  assert.equal(r.calls[1].init.body, r.calls[3].init.body);
});

test('products send true for subscription and preorder', async () => {
  const r = runtime([json({ items: [] })]);
  await r.load('api/productApi.ts').getProducts({ subscription: true, preorder: true });
  const url = new URL(r.calls[0].url, 'http://localhost');
  assert.equal(url.pathname, '/api/v1/products');
  assert.equal(url.searchParams.get('subscription'), 'true');
  assert.equal(url.searchParams.get('preorder'), 'true');
  assert.equal(r.calls[0].init.credentials, 'include');
});
