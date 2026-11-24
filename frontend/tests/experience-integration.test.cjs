// Run: node --test tests/experience-integration.test.cjs
// 通信だけを差し替えて実 API クライアントを実行する。画面操作は下の軽量 hooks fixture で確認する。
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { MemoryRouter } = require('react-router');

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const input = { slotId: 1, adultCount: 2, childCount: 1, infantCount: 1, lastName: '山田', firstName: '太郎', phone: '090-1234-5678', message: null, agreedToCancelPolicy: true, eligibilityConfirmed: true, expectedTotalAmount: 7500 };
const receipt = { id: 12, reservationNo: 'RV-20261124-123456', experienceId: 1, slotId: 1, adultCount: 2, childCount: 1, infantCount: 1, representativeName: '山田 太郎', phone: '09012345678', message: null, totalAmount: 7500, status: 'confirmed', policyAgreedAt: '2026-11-24T10:00:00+09:00', createdAt: '2026-11-24T10:00:00+09:00' };
const slot = { id: 1, startAt: '2099-12-01T10:00:00+09:00', durationMin: 120, capacity: 10, remainingCapacity: 4, bookingDeadlineAt: '2099-11-30T10:00:00+09:00', bookable: true };
const detail = { id: 1, title: '収穫体験', areaId: 1, prefectureName: '北海道', priceAdult: 3000, priceChild: 1500, familyOk: true, beginnerOk: true, thumbnailUrl: null, nextStartAt: slot.startAt, producer: { id: 1, businessName: '農園', city: '札幌市' }, description: '説明', images: [], place: '農園', ageCondition: null, flow: [{ time: '10:00', text: '集合' }, { time: '11:00', text: '収穫' }], belongings: null, notes: null, cancelPolicy: '前日まで', slots: { items: [slot], total: 1, page: 1, pageSize: 20, totalPages: 1 } };

function runtime(replies = [], overrides = {}, mock = false) {
  const calls = [], cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify({ DEV: true, VITE_USE_MOCK: String(mock) }));
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} };
    cache.set(filename, module);
    const context = vm.createContext({ module, exports: module.exports, Response, Request, URL, URLSearchParams, Headers, console,
      window: { location: { origin: 'http://localhost' } },
      fetch: async (url, init) => {
        calls.push({ url, init });
        assert.ok(replies.length, `Unexpected request: ${url}`);
        const reply = replies.shift();
        if (reply instanceof Error) throw reply;
        return typeof reply === 'function' ? reply(url, init) : reply;
      },
      require: (name) => {
        if (Object.hasOwn(overrides, name)) return overrides[name];
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
  const loadSource = name => load(path.resolve(__dirname, '../src', name));
  return { calls, loadSource, api: loadSource('api/experienceApi.ts'), validation: loadSource('utils/experienceValidation.ts') };
}

test('real API mode sends exact application contract, cookies and CSRF, returning the server receipt', async () => {
  const r = runtime([json({ csrfToken: 'token' }), json(receipt, 201)]);
  const result = await r.api.applyExperience(1, { ...input, quoteToken: 'old', representativeName: 'old', policyAgreed: true });
  assert.deepEqual(r.calls.map(c => c.url), ['/api/v1/auth/csrf', '/api/v1/experiences/1/applications']);
  assert.ok(r.calls.every(c => c.init.credentials === 'include'));
  assert.equal(r.calls[1].init.method, 'POST');
  assert.equal(r.calls[1].init.headers['X-CSRFToken'], 'token');
  assert.equal(r.calls[1].init.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(r.calls[1].init.body), input);
  assert.equal(JSON.stringify(result), JSON.stringify(receipt));
});

test('CSRF_FAILED retries once with a fresh token and the same application', async () => {
  const r = runtime([json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED' }, 403), json({ csrfToken: 'new' }), json(receipt, 201)]);
  await r.api.applyExperience(1, input);
  assert.deepEqual(r.calls.map(c => c.init.method ?? 'GET'), ['GET', 'POST', 'GET', 'POST']);
  assert.equal(r.calls[3].init.headers['X-CSRFToken'], 'new');
  assert.equal(r.calls[1].init.body, r.calls[3].init.body);
});

test('a second CSRF_FAILED stops without a retry loop', async () => {
  const r = runtime([json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED' }, 403), json({ csrfToken: 'new' }), json({ errorCode: 'CSRF_FAILED' }, 403)]);
  await assert.rejects(r.api.applyExperience(1, input), e => e.status === 403 && e.errorCode === 'CSRF_FAILED');
  assert.equal(r.calls.length, 4);
});

for (const refresh of [false, true]) test(`CSRF acquisition failure stops POST (refresh=${refresh})`, async () => {
  const r = runtime([...(refresh ? [json({ csrfToken: 'old' }), json({ errorCode: 'CSRF_FAILED' }, 403)] : []), json({}, 503)]);
  await assert.rejects(r.api.applyExperience(1, input), e => e.status === 503);
  assert.equal(r.calls.filter(c => c.init.method === 'POST').length, refresh ? 1 : 0);
});

for (const [status, errorCode] of [[400, 'VALIDATION_ERROR'], [401, 'UNAUTHENTICATED'], [403, 'FORBIDDEN'], [404, 'SLOT_NOT_FOUND'], [409, 'QUOTE_CHANGED'], [409, 'CAPACITY_EXCEEDED'], [409, 'BOOKING_CLOSED'], [409, 'ALREADY_APPLIED'], [409, 'CANNOT_APPLY_OWN'], [429, 'RATE_LIMITED'], [500, 'SERVER_ERROR']]) {
  test(`${status} ${errorCode} preserves API details and never retries`, async () => {
    const r = runtime([json({ csrfToken: 'token' }), json({ errorCode, errorMsg: '拒否', details: { phone: ['確認'] } }, status)]);
    await assert.rejects(r.api.applyExperience(1, input), e => e.status === status && e.errorCode === errorCode && e.details.phone[0] === '確認');
    assert.equal(r.calls.length, 2);
  });
}

test('network failure never resends an application', async () => {
  const r = runtime([json({ csrfToken: 'token' }), new Error('Offline')]);
  await assert.rejects(r.api.applyExperience(1, input), /Offline/);
  assert.equal(r.calls.length, 2);
});

for (const [status, body] of [[200, receipt], [201, { ...receipt, status: 'applied' }], [201, { ...receipt, totalAmount: null }], [201, {}], [201, null]]) {
  test(`unexpected success is not shown as completed (${status}, ${body?.status})`, async () => {
    const r = runtime([json({ csrfToken: 'token' }), json(body, status)]);
    await assert.rejects(r.api.applyExperience(1, input), /申込結果を確認できません/);
    assert.equal(r.calls.length, 2);
  });
}

test('enabling experience submission leaves real job submission blocked', async () => {
  const r = runtime();
  await assert.rejects(r.loadSource('api/jobApi.ts').applyJob(1, {}), /実際の送信は/);
  assert.equal(r.calls.length, 0);
});

test('mock mode uses the actual CSRF/detail/application endpoints with the real API contract', async () => {
  const restMocks = [];
  const r = runtime([], { './rest': { restMocks }, './rest/settings': { delayMs: 0 } }, true);
  for (const [file, name] of [['get_api_v1_auth_csrf', 'authCsrf'], ['get_api_v1_experiences_experienceId', 'experienceDetail'], ['post_api_v1_experiences_experienceId_applications', 'experienceApply']]) {
    restMocks.push(r.loadSource(`mocks/rest/endpoint/${file}.tsx`)[name]);
  }
  const experience = await r.api.getExperience(1);
  assert.equal(experience.slots.items[0].bookable, true);
  assert.equal(experience.slots.items[0].quoteToken, undefined);
  const result = await r.api.applyExperience(1, { ...input, expectedTotalAmount: 9000 });
  assert.equal(result.status, 'confirmed');
  assert.equal(result.totalAmount, 9000);
  assert.equal(result.representativeName, '山田 太郎');
  assert.equal(result.infantCount, 1);
  assert.equal(result.phone, '09012345678');
  assert.equal(r.calls.length, 0);
});

const valid = { adult: '2', child: '1', infant: '1', lastName: '山田', firstName: '太郎', phone: '090-1234-5678', message: '', agreed: true, eligibilityConfirmed: true, familyOk: true, childAllowed: true, total: 7500, selected: slot };
test('application validation follows people, name, phone, amount and consent limits', () => {
  const { validateExperienceApply: validate } = runtime().validation;
  assert.equal(Object.keys(validate(valid)).length, 0);
  for (const [change, key] of [
    [{ adult: '0' }, 'adult'], [{ adult: '1.5' }, 'adult'], [{ child: '-1' }, 'child'], [{ infant: '100' }, 'infant'],
    [{ adult: '50', child: '30', infant: '20' }, 'capacity'], [{ infant: '2' }, 'capacity'],
    [{ familyOk: false }, 'child'], [{ familyOk: false, child: '0' }, 'infant'], [{ childAllowed: false }, 'child'],
    [{ lastName: ' ' }, 'lastName'], [{ firstName: 'あ'.repeat(51) }, 'firstName'],
    [{ lastName: 'あ'.repeat(50), firstName: 'い'.repeat(50) }, 'firstName'],
    [{ phone: '+819012345678' }, 'phone'], [{ phone: '０９０１２３４５６７８' }, 'phone'], [{ phone: '(090)12345678' }, 'phone'],
    [{ message: 'あ'.repeat(2001) }, 'message'], [{ agreed: false }, 'agreed'], [{ eligibilityConfirmed: false }, 'eligibilityConfirmed'],
    [{ total: 2147483648 }, 'total'], [{ total: NaN }, 'total'], [{ selected: undefined }, 'slot'],
  ]) assert.ok(validate({ ...valid, ...change })[key], `${JSON.stringify(change)} -> ${key}`);
  assert.equal(Object.keys(validate({ ...valid, adult: '1', child: '0', familyOk: true, childAllowed: false, total: 3000 })).length, 0, 'infants are allowed without a child price');
});

test('bookable, deadline, start time and capacity all restrict slot selection', () => {
  const { isExperienceSlotBookable: check } = runtime().validation;
  const now = new Date('2026-11-24T10:00:00+09:00').getTime();
  assert.equal(check(slot, now), true);
  for (const change of [{ bookable: false }, { remainingCapacity: 0 }, { bookingDeadlineAt: '2026-11-24T10:00:00+09:00' }, { startAt: '2026-11-24T09:00:00+09:00' }, { bookingDeadlineAt: 'bad' }]) assert.equal(check({ ...slot, ...change }, now), false);
});

// 軽量 fixture：画面本体の hooks とイベントを実行する。DOM・ブラウザー検証ではない。
function hooksFixture() {
  const values = [], effects = [];
  let cursor = 0;
  return { reset: () => { cursor = 0; }, effects,
    react: { ...React, useCallback: fn => fn,
      useState: initial => { const i = cursor++; if (!(i in values)) values[i] = typeof initial === 'function' ? initial() : initial; return [values[i], next => { values[i] = typeof next === 'function' ? next(values[i]) : next; }]; },
      useRef: initial => { const i = cursor++; return values[i] ??= { current: initial }; },
      useEffect: (fn, deps) => { const i = cursor++; if (!values[i] || deps?.some((dep, j) => dep !== values[i][j])) { values[i] = deps; effects.push(fn); } },
    },
  };
}
function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...nodes(tree.props?.children)];
}
function applicationFixture(replies = [], mock = false) {
  const hooks = hooksFixture();
  const content = { data: structuredClone(detail), loading: false, error: '', retry() { content.loading = true; } };
  const r = runtime(replies, { react: hooks.react, 'react-router': { useParams: () => ({ experienceId: '1' }), Link: 'a' }, '../hooks/usePublicContent': { usePublicContent: () => content } }, mock);
  const Page = r.loadSource('pages/ExperienceApplyPage.tsx').default;
  const Form = Page().type;
  let tree;
  function render() { hooks.reset(); tree = Form({ id: 1 }); hooks.effects.splice(0).forEach(fn => fn()); return tree; }
  const find = predicate => { const node = nodes(tree).find(predicate); assert.ok(node, 'Expected form element'); return node; };
  const field = (name, value) => { find(n => n.props?.name === name).props.onChange(value); render(); };
  const check = id => { find(n => n.props?.id === id).props.onChange({ target: { checked: true } }); render(); };
  const submit = () => find(n => n.type === 'form').props.onSubmit({ preventDefault() {} });
  render();
  return { r, content, render, find, field, check, submit, get tree() { return tree; },
    fill() {
      find(n => n.props?.id === 'slot').props.onChange({ target: { value: '1' } }); render();
      for (const [name, value] of [['adult', '2'], ['child', '1'], ['infant', '1'], ['lastName', ' 山田 '], ['firstName', ' 太郎 '], ['phone', '090-1234-5678']]) field(name, value);
      check('policy-agreed'); check('eligibility-confirmed');
    },
  };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
test('application input -> confirmation -> real submission -> receipt, with double-submit lock', async () => {
  let finish;
  const response = new Promise(resolve => { finish = resolve; });
  const f = applicationFixture([json({ csrfToken: 'token' }), () => response]);
  f.fill(); f.submit(); f.render();
  assert.ok(nodes(f.tree).some(n => n.props?.children === '申込を送信する'));
  f.submit(); f.submit(); f.render();
  assert.equal(f.find(n => n.props?.type === 'submit').props.disabled, true);
  await tick();
  assert.equal(f.r.calls.filter(c => c.init.method === 'POST').length, 1);
  assert.deepEqual(JSON.parse(f.r.calls[1].init.body), input);
  finish(json(receipt, 201)); await tick(); f.render();
  assert.ok(nodes(f.tree).some(n => n.props?.children === '申込を受け付けました'));
  assert.ok(!nodes(f.tree).some(n => n.props?.children === '実際の予約・決済・メール送信は行いません。'));
});

for (const errorCode of ['QUOTE_CHANGED', 'CAPACITY_EXCEEDED', 'BOOKING_CLOSED']) test(`${errorCode} reloads details and requires slot/consent reconfirmation`, async () => {
  const f = applicationFixture([json({ csrfToken: 'token' }), json({ errorCode, errorMsg: '変更' }, 409)]);
  f.fill(); f.submit(); f.render(); f.submit(); await tick(); f.render();
  assert.equal(f.content.loading, true);
  f.content.data = { ...detail, familyOk: false, priceChild: null }; f.content.loading = false;
  f.render(); f.render();
  assert.equal(f.find(n => n.props?.id === 'slot').props.value, '');
  assert.equal(f.find(n => n.props?.id === 'policy-agreed').props.checked, false);
  assert.equal(f.find(n => n.props?.id === 'eligibility-confirmed').props.checked, false);
  f.submit(); f.render();
  assert.ok(f.find(n => n.props?.name === 'adult').props.value === '2');
  assert.equal(f.r.calls.length, 2);
});

test('server 400 returns to input and displays the field error', async () => {
  const f = applicationFixture([json({ csrfToken: 'token' }), json({ errorCode: 'VALIDATION_ERROR', errorMsg: '確認', details: { phone: ['電話番号を確認'] } }, 400)]);
  f.fill(); f.submit(); f.render(); f.submit(); await tick(); f.render();
  assert.equal(f.find(n => n.props?.name === 'phone').props.error, '電話番号を確認');
});

test('expired session provides a signin link with the application return path', async () => {
  const f = applicationFixture([json({ csrfToken: 'token' }), json({ errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください' }, 401)]);
  f.fill(); f.submit(); f.render(); f.submit(); await tick(); f.render();
  assert.equal(f.find(n => n.props?.to === '/signin').props.state.from, '/experiences/1/apply');
});

test('C2: actual public detail renders time/text flow and null optional fields', () => {
  const r = runtime([], { '../hooks/usePublicContent': { usePublicContent: () => ({ data: detail, loading: false, error: '', retry() {} }) }, 'react-router': { ...require('react-router'), useParams: () => ({ experienceId: '1' }) } });
  const Page = r.loadSource('pages/ExperienceDetailPage.tsx').default;
  const html = renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(Page)));
  assert.ok(html.includes('<time dateTime="10:00"'));
  assert.ok(html.includes('集合'));
  assert.ok(html.includes('収穫'));
  assert.ok(html.includes('参加を申し込む'));
});

test('C2: management form preserves object flow on edit/save and sends null for empty flow', async () => {
  for (const flow of [detail.flow, null]) {
    const hooks = hooksFixture();
    const r = runtime([], { react: hooks.react });
    const Form = r.loadSource('components/DashboardExperienceForm.tsx').default;
    const experience = { ...detail, prefectureId: 1, publishStatus: 'draft', images: [], flow };
    let saved;
    const tree = Form({ experience, cancelTo: '/', onSubmit: async value => { saved = value; } });
    tree.props.onSubmit({ preventDefault() {} });
    await tick();
    assert.ok(saved, 'The existing management form submits successfully');
    assert.equal(JSON.stringify(saved.flow), JSON.stringify(flow));
    assert.ok(Array.isArray(saved.imageKeys));
  }
});

test('C2: legacy mock flow migration retains the entire HH:MM time', () => {
  const overrides = {};
  const r = runtime([], overrides);
  const stored = { experiences: [{ ...detail, images: [], flow: ['09:35 集合', { time: '10:20', text: '収穫' }] }], etags: {}, slots: [], applications: [], idempotency: {} };
  overrides['./common'] = { ...r.loadSource('mocks/rest/store/common.tsx'), loadState: (_, isValid) => { assert.equal(isValid(stored), true); return stored; } };
  const store = r.loadSource('mocks/rest/store/dashboardExperiences.tsx');
  const result = store.getExperience(new URL('http://localhost/api/v1/dashboard/experiences/1'));
  assert.equal(result.status, 200);
  assert.equal(JSON.stringify(result.body.flow), JSON.stringify([{ time: '09:35', text: '集合' }, { time: '10:20', text: '収穫' }]));
});

test('a deadline crossed while confirming prevents POST and returns to input', () => {
  const f = applicationFixture();
  f.fill(); f.submit(); f.render();
  f.content.data.slots.items[0].bookingDeadlineAt = '2020-01-01T00:00:00+09:00';
  f.submit(); f.render();
  assert.equal(f.r.calls.length, 0);
  assert.ok(nodes(f.tree).some(n => n.props?.children === '現在申し込める開催枠はありません。'));
});
