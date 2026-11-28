// 実行: node --test tests/review2-fix.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { MemoryRouter } = require('react-router');
const {
  runtime,
  json,
  hooksFixture,
} = require('./helpers/frontend-runtime.cjs');

const producer = {
  id: 1,
  businessName: '山本農園',
  genre: 'agriculture',
  prefectureName: '長野県',
  city: '安曇野市',
  coverImageUrl: null,
  acceptsExperience: true,
  recruiting: true,
  badges: [],
};
const pageOf = (items) => ({
  items,
  total: items.length,
  page: 1,
  pageSize: 20,
  totalPages: items.length ? 1 : 0,
});

test('getProducers sends featured=true only when requested', async () => {
  const r = runtime({ reply: () => json(pageOf([producer])) });
  const api = r.load('api/producerApi.ts');
  await api.getProducers(undefined, { featured: true });
  await api.getProducers();
  const featured = new URL(r.calls[0].url, 'http://localhost');
  assert.equal(featured.pathname, '/api/v1/producers');
  assert.equal(featured.searchParams.get('featured'), 'true');
  assert.equal(featured.searchParams.get('sort'), 'featured');
  assert.equal(
    new URL(r.calls[1].url, 'http://localhost').searchParams.has('featured'),
    false,
  );
});

test('producers mock returns only featured producers for featured=true and never badges them as featured', () => {
  const { producersList } = runtime().load(
    'mocks/rest/endpoint/get_api_v1_producers.tsx',
  );
  const all = producersList.handler(
    new URL('http://localhost/api/v1/producers?page=1&pageSize=20'),
  ).body;
  assert.equal(all.total, 6);
  const featured = producersList.handler(
    new URL(
      'http://localhost/api/v1/producers?featured=true&page=1&pageSize=20',
    ),
  ).body;
  assert.equal(featured.items.map((item) => item.id).join(','), '1,2,3,4');
  assert.equal(featured.total, 4);
  assert.ok(all.items.every((item) => !item.badges.includes('featured')));
  assert.ok(featured.items.every((item) => !item.badges.includes('featured')));
});

test('ScrollToTop scrolls to top only when the pathname changes', () => {
  const hooks = hooksFixture();
  let pathname = '/products';
  const r = runtime({
    overrides: {
      react: hooks.react,
      'react-router': {
        useLocation: () => ({ pathname, search: '', hash: '' }),
      },
    },
  });
  const ScrollToTop = r.load('components/ScrollToTop.tsx').default;
  hooks.render(ScrollToTop);
  assert.deepEqual(r.scrolls, [[0, 0]]);
  hooks.render(ScrollToTop);
  assert.equal(r.scrolls.length, 1, 'same pathname must not scroll again');
  pathname = '/experiences';
  hooks.render(ScrollToTop);
  assert.deepEqual(r.scrolls, [
    [0, 0],
    [0, 0],
  ]);
});

test('dashboard layout scrolls its own container to the top when the pathname changes', () => {
  const hooks = hooksFixture();
  let pathname = '/dashboard/products';
  const r = runtime({
    overrides: {
      react: hooks.react,
      jotai: { useAtomValue: () => null, atom: () => ({}) },
      'react-router': {
        Link: () => null,
        NavLink: () => null,
        Outlet: () => null,
        useLocation: () => ({ pathname, search: '', hash: '' }),
      },
    },
  });
  const DashboardLayout = r.load('Layouts/DashboardLayout.tsx').default;
  const scrollCalls = [];
  // 初回描画で ref を取得し、描画後の要素（スクロールするdiv）に見立てたオブジェクトを差し込む
  const container = hooks.render(DashboardLayout).props.children.props.ref;
  container.current = {
    scrollTo: (options) => scrollCalls.push(JSON.stringify(options)),
  };
  pathname = '/dashboard/jobs';
  hooks.render(DashboardLayout);
  assert.deepEqual(
    scrollCalls,
    ['{"top":0}'],
    'pathname change must scroll the dashboard container',
  );
  hooks.render(DashboardLayout);
  assert.equal(scrollCalls.length, 1, 'same pathname must not scroll again');
  pathname = '/dashboard/products';
  hooks.render(DashboardLayout);
  assert.equal(scrollCalls.length, 2);
  assert.equal(
    r.scrolls.length,
    0,
    'window is not the scroll container on the dashboard',
  );
});

test('header shows real page links on every route and uses the favicon as the logo', () => {
  const r = runtime();
  const Header = r.load('components/layout/Header.tsx').default;
  for (const entry of ['/', '/cart']) {
    const html = renderToStaticMarkup(
      React.createElement(
        MemoryRouter,
        { initialEntries: [entry] },
        React.createElement(Header),
      ),
    );
    for (const to of ['/products', '/experiences', '/jobs', '/learn'])
      assert.ok(html.includes(`href="${to}"`), `${entry} should link to ${to}`);
    assert.equal(html.includes('href="#products"'), false);
    assert.ok(html.includes('src="/favicon.svg"'));
    assert.equal(html.includes('>つ<'), false);
  }
});
