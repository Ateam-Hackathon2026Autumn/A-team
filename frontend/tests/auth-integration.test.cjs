// 追加依存なしで実際の API クライアントを実行する。通信先だけを差し替える。
// 実行: node --test tests/auth-integration.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const user = { id: 1, email: 'user@example.com', lastName: '山田', firstName: '太郎', isProducer: false, producerApplicationStatus: 'not_applied', producerAccountStatus: null, emailVerified: false };
const values = { lastName: ' 山田 ', firstName: ' 太郎 ', email: ' user@example.com ', password: 'Abcd1234!', phone: '090-1234-5678', birthDate: '2000-01-01', prefectureId: '13', interests: ['vegetables'], agreedToTerms: true, agreedToPrivacyPolicy: true };
const configured = { DEV: true, VITE_USE_MOCK: 'false', VITE_TERMS_VERSION: '2026-10-01', VITE_PRIVACY_POLICY_VERSION: '2026-10-01', VITE_TERMS_URL: 'https://example.com/terms', VITE_PRIVACY_POLICY_URL: 'https://example.com/privacy' };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function runtime(replies = [], env = configured) {
  const calls = [];
  const cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify(env));
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} };
    cache.set(filename, module);
    const context = vm.createContext({ module, exports: module.exports, Response, URL, console,
      fetch: async (url, init) => {
        calls.push({ url, init });
        assert.ok(replies.length > 0, `Unexpected request: ${url}`);
        const reply = replies.shift();
        if (reply instanceof Error) throw reply;
        return reply;
      },
      require: (name) => {
        assert.ok(name.startsWith('.'), `Unexpected dependency: ${name}`);
        const base = path.resolve(path.dirname(filename), name);
        const resolved = ['.tsx', '.ts'].map((ext) => base + ext).find(fs.existsSync);
        assert.ok(resolved, `Module not found: ${name}`);
        return load(resolved);
      },
    });
    new vm.Script(code, { filename }).runInContext(context);
    return module.exports;
  }
  const src = path.resolve(__dirname, '../src');
  return { calls, api: load(path.join(src, 'api/authApi.tsx')), validation: load(path.join(src, 'utils/authValidation.ts')), env: load(path.join(src, 'config/env.tsx')) };
}

test('signin sends CSRF, cookies and exact password, then refreshes CSRF', async () => {
  const r = runtime([json({ csrfToken: 'before' }), json({ authenticated: true, user, message: 'OK' }), json({ csrfToken: 'after' })]);
  const result = await r.api.signin(' user@example.com ', ' secret ');
  assert.deepEqual(r.calls.map((call) => call.url), ['/api/v1/auth/csrf', '/api/v1/auth/signin', '/api/v1/auth/csrf']);
  assert.ok(r.calls.every((call) => call.init.credentials === 'include'));
  assert.equal(r.calls[1].init.method, 'POST');
  assert.equal(r.calls[1].init.headers['X-CSRFToken'], 'before');
  assert.deepEqual(JSON.parse(r.calls[1].init.body), { email: 'user@example.com', password: ' secret ' });
  assert.equal(result.user.id, 1);
  assert.equal(result.csrfRefreshFailed, false);
});

for (const prefectureId of ['', '13']) {
  test(`signup sends policy versions and converts prefectureId=${JSON.stringify(prefectureId)}`, async () => {
    const r = runtime([json({ csrfToken: 'before' }), json({ authenticated: true, user, message: 'Created' }, 201), json({ csrfToken: 'after' })]);
    await r.api.signup({ ...values, prefectureId });
    assert.equal(r.calls[1].url, '/api/v1/users');
    assert.deepEqual(JSON.parse(r.calls[1].init.body), { ...values, lastName: '山田', firstName: '太郎', email: 'user@example.com', prefectureId: prefectureId ? 13 : null, termsVersion: '2026-10-01', privacyPolicyVersion: '2026-10-01' });
    assert.equal(r.calls.length, 3);
  });
}

for (const [status, errorCode] of [[400, 'VALIDATION_ERROR'], [401, 'INVALID_CREDENTIALS'], [403, 'CSRF_FAILED'], [409, 'ALREADY_AUTHENTICATED'], [429, 'THROTTLED']]) {
  test(`signin preserves ${status} and ${errorCode} without retrying POST`, async () => {
    const r = runtime([json({ csrfToken: 'token' }), json({ errorCode, errorMsg: 'Rejected', details: { email: ['Invalid'] } }, status)]);
    await assert.rejects(r.api.signin('user@example.com', 'secret'), (error) => error.status === status && error.errorCode === errorCode && error.details.email[0] === 'Invalid');
    assert.equal(r.calls.length, 2);
  });
}

for (const errorCode of ['EMAIL_ALREADY_EXISTS', 'POLICY_VERSION_MISMATCH']) {
  test(`signup preserves ${errorCode} and does not refresh CSRF after rejection`, async () => {
    const r = runtime([json({ csrfToken: 'token' }), json({ errorCode, errorMsg: 'Conflict' }, 409)]);
    await assert.rejects(r.api.signup(values), (error) => error.status === 409 && error.errorCode === errorCode);
    assert.equal(r.calls.length, 2);
  });
}

test('CSRF acquisition failure prevents the authentication POST', async () => {
  const r = runtime([json({}, 503)]);
  await assert.rejects(r.api.signin('user@example.com', 'secret'));
  assert.equal(r.calls.length, 1);
});

test('successful registration survives CSRF refresh network failure without resubmitting', async () => {
  const r = runtime([json({ csrfToken: 'token' }), json({ authenticated: true, user, message: 'Created' }, 201), new Error('Offline')]);
  const result = await r.api.signup(values);
  assert.equal(result.authenticated, true);
  assert.equal(result.csrfRefreshFailed, true);
  assert.equal(r.calls.filter((call) => call.init.method === 'POST').length, 1);
});

test('unexpected successful response is not treated as authentication success', async () => {
  const r = runtime([json({ csrfToken: 'token' }), json({ authenticated: false, user: null })]);
  await assert.rejects(r.api.signin('user@example.com', 'secret'));
  assert.equal(r.calls.length, 2);
});

test('signup requires 201 rather than treating arbitrary 2xx as registration success', async () => {
  const r = runtime([json({ csrfToken: 'token' }), json({ authenticated: true, user })]);
  await assert.rejects(r.api.signup(values));
});

test('policy configuration requires both versions and valid document URLs', () => {
  assert.equal(runtime().env.SIGNUP_POLICY_CONFIGURED, true);
  for (const key of ['VITE_TERMS_VERSION', 'VITE_PRIVACY_POLICY_VERSION', 'VITE_TERMS_URL', 'VITE_PRIVACY_POLICY_URL']) {
    assert.equal(runtime([], { ...configured, [key]: '' }).env.SIGNUP_POLICY_CONFIGURED, false);
  }
  assert.equal(runtime([], { ...configured, VITE_TERMS_URL: 'javascript:alert(1)' }).env.SIGNUP_POLICY_CONFIGURED, false);
});

test('email and phone validation matches backend limits', () => {
  const { validation: v } = runtime();
  assert.equal(v.validateEmail('a'.repeat(242) + '@example.com'), undefined);
  assert.ok(v.validateEmail('a'.repeat(243) + '@example.com'));
  assert.equal(Object.keys(v.validateSignup(values)).length, 0);
  for (const phone of ['1234567', '+819012345678', '(090)12345678', '19012345678']) assert.ok(v.validateSignup({ ...values, phone }).phone);
  for (const phone of ['09012345678', '03-1234-5678']) assert.equal(v.validateSignup({ ...values, phone }).phone, undefined);
});
