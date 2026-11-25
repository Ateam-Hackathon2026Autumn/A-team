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
const configured = { DEV: true, VITE_USE_MOCK: 'false', VITE_TERMS_URL: 'https://example.com/terms', VITE_PRIVACY_POLICY_URL: 'https://example.com/privacy' };
const policies = { termsVersion: '2027-04-01', privacyPolicyVersion: '2027-05-01' };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function runtime(replies = [], env = configured, overrides = {}) {
  const calls = [];
  const cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify(env));
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} };
    cache.set(filename, module);
    const context = vm.createContext({ module, exports: module.exports, Response, Headers, URL, console,
      fetch: async (url, init) => {
        calls.push({ url, init });
        assert.ok(replies.length > 0, `Unexpected request: ${url}`);
        const reply = replies.shift();
        if (reply instanceof Error) throw reply;
        return reply;
      },
      require: (name) => {
        if (Object.hasOwn(overrides, name)) return overrides[name];
        if (!name.startsWith('.')) return require(name);
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
  return { calls, api: load(path.join(src, 'api/authApi.tsx')), validation: load(path.join(src, 'utils/authValidation.ts')), env: load(path.join(src, 'config/env.tsx')), loadSource: (name) => load(path.join(src, name)) };
}

test('signin sends CSRF, cookies and exact password, then refreshes CSRF', async () => {
  const r = runtime([json({ csrfToken: 'before' }), json({ authenticated: true, user, message: 'OK' }), json({ csrfToken: 'after' })]);
  const result = await r.api.signin(' user@example.com ', ' secret ');
  assert.deepEqual(r.calls.map((call) => call.url), ['/api/v1/auth/csrf', '/api/v1/auth/signin', '/api/v1/auth/csrf']);
  assert.ok(r.calls.every((call) => call.init.credentials === 'include'));
  assert.equal(r.calls[1].init.method, 'POST');
  assert.equal(r.calls[1].init.headers.get('X-CSRFToken'), 'before');
  assert.deepEqual(JSON.parse(r.calls[1].init.body), { email: 'user@example.com', password: ' secret ' });
  assert.equal(result.user.id, 1);
  assert.equal(result.csrfRefreshFailed, false);
});

test('getPolicies uses the exact URL with cookies and returns current versions', async () => {
  const r = runtime([json(policies)]);
  assert.deepEqual(JSON.parse(JSON.stringify(await r.api.getPolicies())), policies);
  assert.equal(r.calls[0].url, '/api/v1/policies');
  assert.equal(r.calls[0].init.credentials, 'include');
  assert.equal(r.calls[0].init.method, undefined);
});

for (const invalid of [{ ...policies, termsVersion: '' }, { ...policies, privacyPolicyVersion: ' ' }, {}]) {
  test(`getPolicies rejects invalid versions ${JSON.stringify(invalid)}`, async () => {
    const r = runtime([json(invalid)]);
    await assert.rejects(r.api.getPolicies());
  });
}

test('getPolicies preserves the server error shape', async () => {
  const r = runtime([json({ errorCode: 'VALIDATION_ERROR', errorMsg: 'Invalid', details: { name: ['Wrong'] } }, 400)]);
  await assert.rejects(r.api.getPolicies(), (error) => error.status === 400 && error.errorCode === 'VALIDATION_ERROR' && error.details.name[0] === 'Wrong');
});

test('REST mocks include policies and allow a logged-out session', () => {
  const r = runtime([], { ...configured, VITE_MOCK_LOGGED_OUT: 'true' });
  const session = r.loadSource('mocks/rest/endpoint/get_api_v1_auth_session.tsx').authSession;
  const policyMock = r.loadSource('mocks/rest/endpoint/get_api_v1_policies.tsx').policies;
  assert.equal(session.body.authenticated, false);
  assert.equal(session.body.user, null);
  assert.equal(policyMock.path, '/api/v1/policies');
  assert.equal(policyMock.body.termsVersion, '2026-10-01');
});

for (const prefectureId of ['', '13']) {
  test(`signup sends policy versions and converts prefectureId=${JSON.stringify(prefectureId)}`, async () => {
    const r = runtime([json({ csrfToken: 'before' }), json({ authenticated: true, user, message: 'Created' }, 201), json({ csrfToken: 'after' })]);
    await r.api.signup({ ...values, prefectureId }, policies);
    assert.equal(r.calls[1].url, '/api/v1/users');
    assert.deepEqual(JSON.parse(r.calls[1].init.body), { ...values, lastName: '山田', firstName: '太郎', email: 'user@example.com', prefectureId: prefectureId ? 13 : null, ...policies });
    assert.equal(r.calls.length, 3);
  });
}

for (const [status, errorCode] of [[400, 'VALIDATION_ERROR'], [401, 'INVALID_CREDENTIALS'], [403, 'FORBIDDEN'], [409, 'ALREADY_AUTHENTICATED'], [429, 'RATE_LIMITED'], [500, 'SERVER_ERROR'], [401, 'CSRF_FAILED']]) {
  test(`signin preserves ${status} and ${errorCode} without retrying POST`, async () => {
    const r = runtime([json({ csrfToken: 'token' }), json({ errorCode, errorMsg: 'Rejected', details: { email: ['Invalid'] } }, status)]);
    await assert.rejects(r.api.signin('user@example.com', 'secret'), (error) => error.status === status && error.errorCode === errorCode && error.details.email[0] === 'Invalid');
    assert.equal(r.calls.length, 2);
  });
}

for (const operation of ['signin', 'signup']) {
  test(`${operation} retries CSRF_FAILED once with a new token and identical body`, async () => {
    const r = runtime([
      json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED', errorMsg: 'Expired' }, 403),
      json({ csrfToken: 'renewed' }), json({ authenticated: true, user }, operation === 'signin' ? 200 : 201),
      json({ csrfToken: 'after-login' }),
    ]);
    const result = operation === 'signin' ? await r.api.signin('user@example.com', ' secret ') : await r.api.signup(values, policies);
    assert.equal(result.authenticated, true);
    assert.deepEqual(r.calls.map((call) => call.init.method ?? 'GET'), ['GET', 'POST', 'GET', 'POST', 'GET']);
    assert.equal(r.calls[1].init.headers.get('X-CSRFToken'), 'old');
    assert.equal(r.calls[3].init.headers.get('X-CSRFToken'), 'renewed');
    assert.equal(r.calls[1].init.body, r.calls[3].init.body);
    assert.ok(r.calls.every((call) => call.init.credentials === 'include'));
  });

  test(`${operation} stops after a second CSRF_FAILED without looping`, async () => {
    const r = runtime([
      json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED' }, 403),
      json({ csrfToken: 'renewed' }), json({ errorCode: 'CSRF_FAILED', errorMsg: 'Still rejected' }, 403),
    ]);
    const request = operation === 'signin' ? r.api.signin('user@example.com', 'secret') : r.api.signup(values, policies);
    await assert.rejects(request, (error) => error.status === 403 && error.errorCode === 'CSRF_FAILED');
    assert.equal(r.calls.length, 4);
  });
}

test('failed CSRF reacquisition does not resend the rejected POST', async () => {
  const r = runtime([json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED' }, 403), json({}, 503)]);
  await assert.rejects(r.api.signup(values, policies), (error) => error.status === 503);
  assert.equal(r.calls.filter((call) => call.init.method === 'POST').length, 1);
});

test('network failure during registration POST never triggers an automatic retry', async () => {
  const r = runtime([json({ csrfToken: 'token' }), new Error('Connection lost')]);
  await assert.rejects(r.api.signup(values, policies), /Connection lost/);
  assert.equal(r.calls.length, 2);
});

for (const errorCode of ['EMAIL_ALREADY_EXISTS', 'POLICY_VERSION_MISMATCH']) {
  test(`signup preserves ${errorCode} and does not refresh CSRF after rejection`, async () => {
    const r = runtime([json({ csrfToken: 'token' }), json({ errorCode, errorMsg: 'Conflict' }, 409)]);
    await assert.rejects(r.api.signup(values, policies), (error) => error.status === 409 && error.errorCode === errorCode);
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
  const result = await r.api.signup(values, policies);
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
  await assert.rejects(r.api.signup(values, policies));
});

test('optional policy links exclude invalid URLs without blocking registration', () => {
  assert.equal(runtime([], {}).env.TERMS_URL, '');
  assert.equal(runtime().env.TERMS_URL, 'https://example.com/terms');
  assert.equal(runtime([], { ...configured, VITE_TERMS_URL: 'javascript:alert(1)' }).env.TERMS_URL, '');
});

test('email and phone validation matches backend limits', () => {
  const { validation: v } = runtime();
  assert.equal(v.validateEmail('a'.repeat(242) + '@example.com'), undefined);
  assert.ok(v.validateEmail('a'.repeat(243) + '@example.com'));
  assert.equal(Object.keys(v.validateSignup(values)).length, 0);
  for (const phone of ['1234567', '+819012345678', '(090)12345678', '19012345678']) assert.ok(v.validateSignup({ ...values, phone }).phone);
  for (const phone of ['09012345678', '03-1234-5678']) assert.equal(v.validateSignup({ ...values, phone }).phone, undefined);
  for (const key of ['agreedToTerms', 'agreedToPrivacyPolicy']) assert.ok(v.validateSignup({ ...values, [key]: false })[key]);
});

test('return path keeps internal pathname, search and hash', () => {
  const { getAuthReturnPath } = runtime().loadSource('utils/authRedirect.ts');
  assert.equal(getAuthReturnPath({ pathname: '/checkout', search: '?step=1', hash: '#delivery' }), '/checkout?step=1#delivery');
  assert.equal(getAuthReturnPath('/products/1?quantity=2#details'), '/products/1?quantity=2#details');
  assert.equal(getAuthReturnPath({ pathname: '/mypage/orders' }), '/mypage/orders');
});

test('return path rejects external URLs, malformed values and auth loops', () => {
  const { getAuthReturnPath } = runtime().loadSource('utils/authRedirect.ts');
  for (const from of [undefined, null, 1, {}, { pathname: '/checkout', search: 3 }, { pathname: '/checkout', hash: 'bad' }, { pathname: '/checkout', search: '//evil.test' }, 'https://evil.test', '//evil.test/path', '/\\evil.test', '/%2f%2fevil.test', '/%5cevil.test', '/%00', '/bad%escape', '/\nevil.test', '/signin', '/signup', '/signup/complete', '/admin/signin', '/foo/../signin', '/%73ignin', { pathname: '//evil.test' }, { pathname: '/checkout?bad=1' }]) {
    assert.equal(getAuthReturnPath(from), '/', JSON.stringify(from));
  }
});

// 実際の Jotai ストア・React コンポーネントを使用し、ルーターの現在位置と
// Navigate の出力だけを差し替える。状態更新が URL 更新に先行する順序を再現する。
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { Provider } = require('jotai');
const { createStore } = require('jotai/vanilla');
function guardFixture(pathname, env = configured) {
  const redirects = [];
  const router = {
    ...require('react-router'),
    useLocation: () => ({ pathname, search: '', hash: '', state: null }),
    useNavigate: () => () => {},
    Navigate: (props) => { redirects.push(props); return null; },
    Outlet: () => React.createElement('span', null, 'outlet'),
  };
  const r = runtime([], env, { 'react-router': router });
  const atoms = r.loadSource('stores/userAtom.tsx');
  const Guard = r.loadSource('components/AuthWrapper.tsx').default;
  const store = createStore();
  return { r, atoms, store, redirects, render: () => renderToStaticMarkup(React.createElement(Provider, { store }, React.createElement(Guard))) };
}

test('signup guard preserves completion and producer metadata when login becomes visible first', () => {
  const f = guardFixture('/signup');
  const navigation = { to: '/signup/complete', state: { registered: true, purpose: 'producer', csrfRefreshFailed: false } };
  let observed = false;
  const unsubscribe = f.store.sub(f.atoms.loginStatusAtom, () => {
    observed = true;
    assert.equal(f.store.get(f.atoms.pendingAuthNavigationAtom).to, '/signup/complete');
    assert.equal(f.store.get(f.atoms.userInfoAtom).id, user.id);
  });
  f.store.set(f.atoms.authenticatedNavigationAtom, { user, navigation });
  f.render();
  unsubscribe();
  assert.equal(observed, true);
  assert.equal(f.redirects.length, 1);
  assert.equal(f.redirects[0].to, '/signup/complete');
  assert.equal(f.redirects[0].state.purpose, 'producer');
  assert.equal(f.redirects[0].state.registered, true);
});

test('signin guard prioritizes checkout return path while still at signin', () => {
  const f = guardFixture('/signin');
  f.store.set(f.atoms.authenticatedNavigationAtom, { user, navigation: { to: '/checkout?step=1#delivery' } });
  f.render();
  assert.equal(f.redirects[0].to, '/checkout?step=1#delivery');
});

test('normal authenticated visits to signin go home and unauthenticated protected visits keep from', () => {
  const loggedIn = guardFixture('/signin');
  loggedIn.store.set(loggedIn.atoms.userInfoAtom, user);
  loggedIn.store.set(loggedIn.atoms.loginStatusAtom, 'loggedIn');
  loggedIn.render();
  assert.equal(loggedIn.redirects[0].to, '/');
  const loggedOut = guardFixture('/mypage/orders');
  loggedOut.store.set(loggedOut.atoms.loginStatusAtom, 'loggedOut');
  loggedOut.render();
  assert.equal(loggedOut.redirects[0].to, '/signin');
  assert.equal(loggedOut.redirects[0].state.from.pathname, '/mypage/orders');
});

test('registration form without policy URLs permits submission and retains required agreement checks', () => {
  const r = runtime([], {});
  const AccountStep = r.loadSource('components/signup/AccountStep.tsx').default;
  const html = renderToStaticMarkup(React.createElement(AccountStep, { values, purpose: 'consumer', errors: {}, isSubmitting: false, message: '', onChange() {}, onBack() {}, onSubmit() {} }));
  assert.ok(html.includes('登録する →'));
  const submit = html.match(/<button\b[^>]*type="submit"[^>]*>/)?.[0];
  assert.ok(submit);
  assert.ok(!submit.includes('disabled=""'));
  assert.ok(!html.includes('現在は登録できません'));
  assert.ok(html.includes('name="agreedToTerms"'));
  assert.ok(html.includes('name="agreedToPrivacyPolicy"'));
});

test('registration form blocks submission while policy loading fails and offers reload', () => {
  const r = runtime([], {});
  const AccountStep = r.loadSource('components/signup/AccountStep.tsx').default;
  const html = renderToStaticMarkup(React.createElement(AccountStep, { values, purpose: 'consumer', errors: {}, isSubmitting: false, policiesReady: false, policiesError: true, message: '', onChange() {}, onBack() {}, onSubmit() {}, onReloadPolicies() {} }));
  assert.ok(html.includes('利用規約の情報を取得できませんでした'));
  assert.ok(html.includes('再読み込み'));
  const submit = html.match(/<button\b[^>]*type="submit"[^>]*>/)?.[0];
  assert.ok(submit);
  assert.ok(submit.includes('disabled=""'));
});

test('auth layout shows demo notice only with mocks enabled', () => {
  for (const [env, expected] of [[{ DEV: true }, true], [{ DEV: true, VITE_USE_MOCK: 'false' }, false], [{ DEV: false }, false]]) {
    const r = runtime([], env, { 'react-router': { Outlet: () => null } });
    const Layout = r.loadSource('Layouts/AuthLayout.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Layout));
    assert.equal(html.includes('画面確認用デモです。APIは未接続です。'), expected);
  }
});

test('restored auth layout keeps dev dark panel and playback control without emoji', () => {
  const r = runtime([], configured, { 'react-router': { Outlet: () => null } });
  const Layout = r.loadSource('Layouts/AuthLayout.tsx').default;
  const html = renderToStaticMarkup(React.createElement(Layout));
  assert.ok(html.includes('bg-marche-green-dark'));
  assert.ok(html.includes('背景動画を再生'));
  assert.ok(!html.includes('🌿'));
});

test('restored background video uses the existing video sources and poster', () => {
  const r = runtime();
  const { BackgroundVideo, useBackgroundVideo } = r.loadSource('components/BackgroundVideo.tsx');
  function VideoFixture() { return React.createElement(BackgroundVideo, { control: useBackgroundVideo() }); }
  const html = renderToStaticMarkup(React.createElement(VideoFixture));
  for (const asset of ['home-hero.webm', 'home-hero.mp4', 'home-hero-poster.jpg']) assert.ok(html.includes(asset));
});

test('completion screen renders CheckIcon and preserves producer application link', () => {
  const router = { ...require('react-router'), useLocation: () => ({ state: { registered: true, purpose: 'producer' } }) };
  const r = runtime([], configured, { 'react-router': router });
  const Complete = r.loadSource('components/signup/CompleteStep.tsx').default;
  const html = renderToStaticMarkup(React.createElement(require('react-router').MemoryRouter, null, React.createElement(Complete)));
  assert.ok(html.includes('<svg'));
  assert.ok(html.includes('登録が完了しました！'));
  assert.ok(html.includes('href="/producer-application/new"'));
});

test('signup progress shows only the two form steps', () => {
  const r = runtime();
  const Signup = r.loadSource('pages/SignupPage.tsx').default;
  const html = renderToStaticMarkup(React.createElement(require('react-router').MemoryRouter, null, React.createElement(Signup)));
  const progress = html.match(/<ol[^>]*>[\s\S]*?<\/ol>/)?.[0];
  assert.ok(progress);
  assert.equal((progress.match(/<li\b/g) ?? []).length, 2);
});
