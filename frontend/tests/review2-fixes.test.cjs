// 実ソースを実行して、生産者申請の導線・申請済み時の遷移・補足取得の5xx扱いを確認する。
// 実行: node --test tests/review2-fixes.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { runtime: createRuntime, json } = require('./helpers/frontend-runtime.cjs');

const link = props => React.createElement('a', { href: props.to, className: typeof props.className === 'function' ? props.className({ isActive: false }) : props.className }, props.children);
const reactRouter = {
  Link: link,
  NavLink: link,
  Navigate: ({ to }) => React.createElement('span', { 'data-navigate': to }),
  useNavigate: () => () => {},
};
const applicant = (producerApplicationStatus, isProducer = false) => ({
  id: 1, email: 'user@example.com', lastName: '山田', firstName: '太郎', isProducer, producerApplicationStatus, producerAccountStatus: null, emailVerified: true,
});

test('mypage navigation offers the producer application entry only to non-producers, with the right target per status', () => {
  const cases = [
    [applicant('not_applied'), '/producer-application/new'],
    [applicant('pending'), '/producer-application'],
    [applicant('returned'), '/producer-application'],
    [applicant('rejected'), '/producer-application'],
    [applicant('approved', true), null],
    [applicant('not_applied', true), null],
    [applicant('approved'), null],
  ];
  for (const [user, href] of cases) {
    const r = createRuntime({ overrides: { 'react-router': reactRouter, jotai: { useAtomValue: () => user }, '../../stores/userAtom': { userInfoAtom: {} } } });
    const MyPageNavigation = r.load('components/mypage/MyPageNavigation.tsx').default;
    const html = renderToStaticMarkup(React.createElement(MyPageNavigation));
    if (href === null) {
      assert.equal(html.includes('生産者'), false, user.producerApplicationStatus);
    } else {
      assert.equal(html.includes(`href="${href}"`), true, `${user.producerApplicationStatus} -> ${href}`);
      assert.equal(html.includes('生産者'), true, user.producerApplicationStatus);
    }
  }
});

test('producer application new page sends returned and rejected applicants to the edit screen instead of a 409 form', () => {
  const render = status => {
    const r = createRuntime({
      overrides: {
        'react-router': reactRouter,
        jotai: { useAtom: () => [applicant(status), () => {}] },
        '../api/producerApplicationApi': { createProducerApplication: async () => ({}) },
        '../components/producer/ProducerApplicationForm': () => React.createElement('form', null),
        '../components/ui/ContentPage': { ContentPage: ({ children }) => React.createElement('div', null, children), textLinkClass: '' },
        '../stores/userAtom': { userInfoAtom: {} },
      },
    });
    const Page = r.load('pages/ProducerApplicationNewPage.tsx').default;
    return renderToStaticMarkup(React.createElement(Page));
  };
  for (const status of ['returned', 'rejected']) {
    assert.equal(render(status).includes('data-navigate="/producer-application/edit"'), true, status);
  }
  const fresh = render('not_applied');
  assert.equal(fresh.includes('data-navigate'), false);
  assert.equal(fresh.includes('<form'), true);
  assert.equal(render('pending').includes('<form'), false);
});

test('supplementary GET failures do not trigger the global 5xx redirect while 401 is still handled', async () => {
  const r = createRuntime({ replies: [json({}, 503), json({}, 503), json({ errorMsg: '失敗' }, 503), json({ errorMsg: '認証が必要です' }, 401)] });
  const { apiFetch, setApiFailureHandler, SUPPLEMENTARY_FETCH } = r.load('api/client.tsx');
  const { getCategories } = r.load('api/productApi.ts');
  const failures = [];
  setApiFailureHandler((status, path, method) => failures.push({ status, path, method }));
  try {
    await apiFetch('/api/v1/categories', {}, SUPPLEMENTARY_FETCH);
    assert.deepEqual(failures, []);
    await apiFetch('/api/v1/categories');
    assert.deepEqual(failures, [{ status: 503, path: '/api/v1/categories', method: 'GET' }]);
    await assert.rejects(getCategories(undefined, SUPPLEMENTARY_FETCH), error => error.status === 503);
    assert.equal(failures.length, 1);
    // 補足取得でも 401 はセッション切れとして未認証ハンドラーへ通知する
    await apiFetch('/api/v1/categories', {}, SUPPLEMENTARY_FETCH);
    assert.deepEqual(failures.at(-1), { status: 401, path: '/api/v1/categories', method: 'GET' });
    assert.equal(failures.length, 2);
  } finally {
    setApiFailureHandler(null);
  }
});
