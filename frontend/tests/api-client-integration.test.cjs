// 実行: node --test tests/api-client-integration.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const {
  runtime,
  json,
  tick,
  deferred,
} = require('./helpers/frontend-runtime.cjs');

for (const method of ['GET', 'HEAD', 'OPTIONS'])
  test(`${method} skips CSRF and leaves a CSRF-shaped 403 untouched`, async () => {
    const r = runtime({ replies: [json({ errorCode: 'CSRF_FAILED' }, 403)] });
    const response = await r
      .load('api/client.tsx')
      .apiFetch('/api/v1/public', { method });
    assert.equal(response.status, 403);
    assert.equal(r.calls.length, 1);
    assert.equal(r.calls[0].init.credentials, 'include');
  });

test('legacy token accessor and writes use one memory cache', async () => {
  const r = runtime({
    replies: [json({ csrfToken: 'shared' }), json({}), json({})],
  });
  const client = r.load('api/client.tsx');
  assert.equal(await r.load('api/authApi.tsx').getCsrfToken(), 'shared');
  await client.apiFetch('/api/v1/a', { method: 'POST' });
  await client.apiFetch('/api/v1/b', { method: 'DELETE' });
  assert.equal(r.calls.length, 3);
  assert.ok(
    r.calls
      .slice(1)
      .every((c) => c.init.headers.get('X-CSRFToken') === 'shared'),
  );
});

test('concurrent writes share the initial token acquisition', async () => {
  const first = deferred();
  const r = runtime({
    reply: (url) => (url.endsWith('/csrf') ? first.promise : json({})),
  });
  const client = r.load('api/client.tsx');
  const pending = [
    client.apiFetch('/api/v1/a', { method: 'POST' }),
    client.apiFetch('/api/v1/b', { method: 'PATCH' }),
  ];
  await tick();
  assert.equal(r.calls.length, 1);
  first.resolve(json({ csrfToken: 'shared' }));
  await Promise.all(pending);
  assert.equal(r.calls.length, 3);
});

for (const body of [
  null,
  {},
  { csrfToken: '' },
  { csrfToken: ' ' },
  { csrfToken: 1 },
])
  test(`invalid token is not cached (${JSON.stringify(body)})`, async () => {
    const r = runtime({
      replies: [json(body), json({ csrfToken: 'valid' }), json({})],
    });
    const client = r.load('api/client.tsx');
    await assert.rejects(client.apiFetch('/api/v1/a', { method: 'POST' }));
    assert.equal(r.calls.length, 1);
    await client.apiFetch('/api/v1/a', { method: 'POST' });
    assert.equal(r.calls.length, 3);
  });

test('failed token request is released for the next operation', async () => {
  const r = runtime({
    replies: [new Error('Offline'), json({ csrfToken: 'valid' }), json({})],
  });
  const client = r.load('api/client.tsx');
  await assert.rejects(client.getCsrfToken(), /Offline/);
  await client.apiFetch('/api/v1/a', { method: 'POST' });
  assert.equal(r.calls.length, 3);
});

for (const method of ['POST', 'PATCH', 'DELETE'])
  test(`${method} retries CSRF once preserving body, headers and signal`, async () => {
    const r = runtime({
      replies: [
        json({ csrfToken: 'old' }),
        json({ errorCode: 'CSRF_FAILED' }, 403),
        json({ csrfToken: 'fresh' }),
        json({}),
      ],
    });
    const signal = new AbortController().signal;
    const body =
      method === 'DELETE' ? undefined : JSON.stringify({ quantity: 2 });
    const headers = new Headers({
      'x-csrftoken': 'stale',
      'Idempotency-Key': 'same-key',
      'If-Match': 'same-etag',
    });
    await r
      .load('api/client.tsx')
      .apiFetch('/api/v1/a', { method, headers, body, signal });
    assert.equal(r.calls.length, 4);
    for (const c of [r.calls[1], r.calls[3]]) {
      assert.equal(c.init.method, method);
      assert.equal(c.init.body, body);
      assert.equal(c.init.signal, signal);
      assert.equal(c.init.headers.get('Idempotency-Key'), 'same-key');
      assert.equal(c.init.headers.get('If-Match'), 'same-etag');
      assert.equal(c.init.credentials, 'include');
    }
    assert.equal(r.calls[1].init.headers.get('X-CSRFToken'), 'old');
    assert.equal(r.calls[3].init.headers.get('X-CSRFToken'), 'fresh');
    assert.equal(
      headers.get('X-CSRFToken'),
      'stale',
      'caller headers are not mutated',
    );
  });

test('a second CSRF error is returned intact after exactly one retry', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'old' }),
      json({ errorCode: 'CSRF_FAILED' }, 403),
      json({ csrfToken: 'new' }),
      json({ errorCode: 'CSRF_FAILED', errorMsg: 'Rejected' }, 403),
    ],
  });
  const response = await r
    .load('api/client.tsx')
    .apiFetch('/api/v1/a', { method: 'POST' });
  assert.equal(response.status, 403);
  assert.equal((await response.json()).errorMsg, 'Rejected');
  assert.equal(r.calls.length, 4);
});

for (const [status, errorCode] of [
  [400, 'VALIDATION_ERROR'],
  [401, 'UNAUTHENTICATED'],
  [403, 'FORBIDDEN'],
  [409, 'CONFLICT'],
  [429, 'RATE_LIMITED'],
  [500, 'SERVER_ERROR'],
])
  test(`${status}/${errorCode} is not retried and its body remains readable`, async () => {
    const body = { errorCode, details: { quantity: ['確認'] } };
    const r = runtime({
      replies: [json({ csrfToken: 'token' }), json(body, status)],
    });
    const response = await r
      .load('api/client.tsx')
      .apiFetch('/api/v1/a', { method: 'POST' });
    assert.deepEqual(await response.json(), body);
    assert.equal(r.calls.length, 2);
  });

test('HTML 403 is returned without trying to refresh CSRF', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'token' }),
      new Response('Forbidden', { status: 403 }),
    ],
  });
  const response = await r
    .load('api/client.tsx')
    .apiFetch('/api/v1/a', { method: 'POST' });
  assert.equal(await response.text(), 'Forbidden');
  assert.equal(r.calls.length, 2);
});

test('network failure during a write never retries the write', async () => {
  const r = runtime({
    replies: [json({ csrfToken: 'token' }), new Error('Offline')],
  });
  await assert.rejects(
    r.load('api/client.tsx').apiFetch('/api/v1/a', { method: 'POST' }),
    /Offline/,
  );
  assert.equal(r.calls.length, 2);
});

test('concurrent CSRF rejections share a single refresh', async () => {
  let acquisitions = 0;
  const r = runtime({
    reply: (url, init) =>
      url.endsWith('/csrf')
        ? json({ csrfToken: ++acquisitions === 1 ? 'old' : 'new' })
        : init.headers.get('X-CSRFToken') === 'old'
          ? json({ errorCode: 'CSRF_FAILED' }, 403)
          : json({}),
  });
  const client = r.load('api/client.tsx');
  const results = await Promise.all(
    ['a', 'b', 'c'].map((id) =>
      client.apiFetch(`/api/v1/${id}`, { method: 'POST' }),
    ),
  );
  assert.ok(results.every((r) => r.ok));
  assert.equal(acquisitions, 2);
  assert.equal(r.calls.filter((c) => c.init.method === 'POST').length, 6);
});

test('an invalidated in-flight acquisition cannot restore the old token', async () => {
  const old = deferred();
  const r = runtime({
    replies: [() => old.promise, json({ csrfToken: 'new' })],
  });
  const client = r.load('api/client.tsx');
  const pending = client.getCsrfToken();
  await tick();
  client.clearCsrfToken();
  assert.equal(await client.getCsrfToken(), 'new');
  old.resolve(json({ csrfToken: 'old' }));
  assert.equal(await pending, 'new');
  assert.equal(await client.getCsrfToken(), 'new');
  assert.equal(r.calls.length, 2);
});

test('abort before a write does not acquire CSRF', async () => {
  const r = runtime();
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    r
      .load('api/client.tsx')
      .apiFetch('/api/v1/a', { method: 'POST', signal: controller.signal }),
    (e) => e.name === 'AbortError',
  );
  assert.equal(r.calls.length, 0);
});

test('aborting a waiter does not cancel the token shared with another write', async () => {
  const token = deferred(),
    controller = new AbortController();
  const r = runtime({
    reply: (url) => (url.endsWith('/csrf') ? token.promise : json({})),
  });
  const client = r.load('api/client.tsx');
  const aborted = assert.rejects(
    client.apiFetch('/api/v1/a', { method: 'POST', signal: controller.signal }),
    (e) => e.name === 'AbortError',
  );
  const other = client.apiFetch('/api/v1/b', { method: 'POST' });
  controller.abort();
  token.resolve(json({ csrfToken: 'token' }));
  await Promise.all([aborted, other]);
  assert.equal(r.calls.length, 2);
  assert.equal(r.calls[1].url, '/api/v1/b');
});

test('abort after a CSRF rejection prevents refresh and retry', async () => {
  const controller = new AbortController();
  const r = runtime({
    replies: [
      json({ csrfToken: 'token' }),
      () => {
        controller.abort();
        return json({ errorCode: 'CSRF_FAILED' }, 403);
      },
    ],
  });
  await assert.rejects(
    r
      .load('api/client.tsx')
      .apiFetch('/api/v1/a', { method: 'POST', signal: controller.signal }),
    (e) => e.name === 'AbortError',
  );
  assert.equal(r.calls.length, 2);
});

test('FormData is replayed without forcing a multipart Content-Type', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'old' }),
      json({ errorCode: 'CSRF_FAILED' }, 403),
      json({ csrfToken: 'new' }),
      json({}),
    ],
  });
  const body = new FormData();
  body.append('file', new Blob(['test'], { type: 'image/png' }), 'test.png');
  await r
    .load('api/client.tsx')
    .apiFetch('/api/v1/uploads/images', { method: 'POST', body });
  assert.equal(r.calls[1].init.body, body);
  assert.equal(r.calls[3].init.body, body);
  assert.equal(r.calls[3].init.headers.has('Content-Type'), false);
});

test('consumed stream bodies are never replayed', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'old' }),
      json({ errorCode: 'CSRF_FAILED' }, 403),
    ],
  });
  const body = new ReadableStream({
    start(controller) {
      controller.close();
    },
  });
  const response = await r
    .load('api/client.tsx')
    .apiFetch('/api/v1/a', { method: 'POST', body, duplex: 'half' });
  assert.equal(response.status, 403);
  assert.equal(r.calls.length, 2);
});

test('successful signout invalidates the cached token', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'before' }),
      json({}),
      json({ csrfToken: 'after' }),
    ],
  });
  await r.load('api/consumerAccountApi.ts').signOutConsumer();
  assert.equal(await r.load('api/client.tsx').getCsrfToken(), 'after');
  assert.equal(r.calls.length, 3);
});

test('failed post-login CSRF refresh does not resend login and leaves the next write able to acquire', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'before' }),
      json({ authenticated: true, user: { id: 1 } }),
      json({}, 503),
      json({ csrfToken: 'after' }),
      json({}),
    ],
  });
  const result = await r
    .load('api/authApi.tsx')
    .signin('user@example.com', 'secret');
  assert.equal(result.csrfRefreshFailed, true);
  await r.load('api/client.tsx').apiFetch('/api/v1/a', { method: 'PATCH' });
  assert.equal(r.calls.filter((c) => c.url.endsWith('/signin')).length, 1);
  assert.equal(r.calls.at(-1).init.headers.get('X-CSRFToken'), 'after');
});
