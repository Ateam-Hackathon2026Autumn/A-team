// 実行: node --test tests/remaining-api-integration.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { MemoryRouter } = require('react-router');
const {
  runtime,
  json,
  hooksFixture,
  nodes,
  tick,
  deferred,
} = require('./helpers/frontend-runtime.cjs');
const cart = {
  items: [
    {
      id: 1,
      productId: 1,
      productName: 'りんご',
      quantity: 1,
      unitPrice: 300,
      subtotal: 300,
      purchasable: true,
      unavailableReason: null,
    },
  ],
  shipments: [],
  itemsTotal: 300,
  shippingTotal: 500,
  total: 800,
  canCheckout: true,
};
const emptyCart = {
  items: [],
  shipments: [],
  itemsTotal: 0,
  shippingTotal: 0,
  total: 0,
  canCheckout: false,
};
const page = (items) => ({
  items,
  total: items.length,
  page: 1,
  pageSize: 20,
  totalPages: items.length ? 1 : 0,
});

test('guest cart add/update/delete uses cookies, shared CSRF, whole cart and bodyless 204', async () => {
  const r = runtime({
    replies: [
      json({ csrfToken: 'guest-token' }),
      json(cart),
      json(cart),
      new Response(null, { status: 204 }),
    ],
  });
  const api = r.load('api/cartApi.ts');
  assert.equal(
    JSON.stringify(await api.addCartItem(1, 1)),
    JSON.stringify(cart),
  );
  assert.equal(
    JSON.stringify(await api.updateCartItem(1, 2)),
    JSON.stringify(cart),
  );
  await api.removeCartItem(1);
  assert.deepEqual(
    r.calls.map((c) => c.init.method ?? 'GET'),
    ['GET', 'POST', 'PATCH', 'DELETE'],
  );
  assert.ok(r.calls.every((c) => c.init.credentials === 'include'));
  assert.ok(
    r.calls
      .slice(1)
      .every((c) => c.init.headers.get('X-CSRFToken') === 'guest-token'),
  );
  assert.deepEqual(JSON.parse(r.calls[1].init.body), {
    productId: 1,
    quantity: 1,
  });
  assert.deepEqual(JSON.parse(r.calls[2].init.body), { quantity: 2 });
  assert.equal(r.calls[3].init.body, undefined);
});

for (const method of ['addCartItem', 'updateCartItem', 'removeCartItem'])
  test(`${method} rejects an unexpected success status`, async () => {
    const r = runtime({
      replies: [json({ csrfToken: 'token' }), json(cart, 202)],
    });
    await assert.rejects(
      r
        .load('api/cartApi.ts')
        [method](1, ...(method === 'removeCartItem' ? [] : [1])),
      /処理結果を確認できません/,
    );
    assert.equal(r.calls.length, 2);
  });

for (const [status, errorCode] of [
  [400, 'VALIDATION_ERROR'],
  [404, 'CART_ITEM_NOT_FOUND'],
  [409, 'OUT_OF_STOCK'],
  [409, 'UNSUPPORTED_PRODUCT'],
  [409, 'CANNOT_PURCHASE_OWN'],
])
  test(`cart preserves ${status}/${errorCode} and field errors`, async () => {
    const r = runtime({
      replies: [
        json({ csrfToken: 'token' }),
        json(
          {
            errorCode,
            errorMsg: '確認',
            details: { quantity: ['数量を確認'] },
          },
          status,
        ),
      ],
    });
    await assert.rejects(
      r.load('api/cartApi.ts').addCartItem(1, 1),
      (e) =>
        e.errorCode === errorCode && e.details.quantity[0] === '数量を確認',
    );
    assert.equal(r.calls.length, 2);
  });

test('real-mode cart row keeps quantity/remove controls available to guests', () => {
  const r = runtime();
  const Row = r.load('components/cart/CartItemRow.tsx').default;
  const tree = Row({
    item: cart.items[0],
    product: { stock: 5 },
    busy: false,
    onQuantityChange() {},
    onRemove() {},
  });
  assert.equal(
    nodes(tree).find((n) => n.type === 'select').props.disabled,
    false,
  );
  assert.equal(
    nodes(tree).find((n) => n.props?.children === '削除').props.disabled,
    false,
  );
  const missing = Row({
    item: cart.items[0],
    busy: false,
    onQuantityChange() {},
    onRemove() {},
  });
  assert.equal(
    nodes(missing).find((n) => n.type === 'select').props.disabled,
    true,
  );
  assert.equal(
    nodes(missing).find((n) => n.props?.children === '削除').props.disabled,
    false,
  );
});

test('guest product page adds to real cart and locks simultaneous clicks', async () => {
  const hooks = hooksFixture(),
    pending = deferred();
  let product;
  const r = runtime({
    overrides: {
      react: hooks.react,
      jotai: { ...require('jotai'), useAtomValue: () => 'loggedOut' },
      'react-router': {
        ...require('react-router'),
        useParams: () => ({ productId: '1' }),
        useLocation: () => ({ pathname: '/products/1', search: '', hash: '' }),
        useNavigate: () => () => {},
      },
    },
    reply: (url) => {
      if (url === '/api/v1/products/1') return json(product);
      if (url.startsWith('/api/v1/products?')) return json(page([]));
      if (url.endsWith('/csrf')) return json({ csrfToken: 'guest' });
      if (url === '/api/v1/cart/items') return pending.promise;
      assert.fail(`Unexpected URL ${url}`);
    },
  });
  product = r.load('mocks/rest/endpoint/get_api_v1_products_productId.tsx')
    .productDetail.body;
  const Page = r.load('pages/ProductDetailPage.tsx').default;
  const Form = Page().type;
  hooks.render(Form, { productId: '1' });
  await tick();
  let tree = hooks.render(Form, { productId: '1' });
  const add = nodes(tree).find((n) => n.props?.children === 'カートに追加');
  assert.ok(add);
  assert.equal(add.props.disabled, false);
  add.props.onClick();
  add.props.onClick();
  await tick();
  assert.equal(r.calls.filter((c) => c.init.method === 'POST').length, 1);
  pending.resolve(json(cart));
  await tick();
  tree = hooks.render(Form, { productId: '1' });
  assert.ok(
    nodes(tree).some(
      (n) =>
        typeof n.props?.children === 'string' &&
        n.props.children.includes('カートに追加しました'),
    ),
  );
  assert.ok(
    !nodes(tree).some((n) => n.props?.children === 'ログインしてカートに追加'),
  );
});

test('real cart page updates, reloads after 409, and reloads after deleting', async () => {
  const hooks = hooksFixture();
  let product,
    gets = 0;
  const r = runtime({
    overrides: {
      react: hooks.react,
      jotai: { ...require('jotai'), useAtomValue: () => 'loggedOut' },
    },
    reply: (url, init) => {
      if (url === '/api/v1/cart') {
        gets++;
        return json(gets >= 3 ? emptyCart : cart);
      }
      if (url === '/api/v1/products/1') return json(product);
      if (url.endsWith('/csrf')) return json({ csrfToken: 'token' });
      if (init.method === 'PATCH')
        return json(
          { errorCode: 'QUANTITY_EXCEEDS_STOCK', errorMsg: '在庫が足りません' },
          409,
        );
      if (init.method === 'DELETE') return new Response(null, { status: 204 });
      assert.fail(`Unexpected URL ${url}`);
    },
  });
  product = r.load('mocks/rest/endpoint/get_api_v1_products_productId.tsx')
    .productDetail.body;
  const Cart = r.load('pages/CartPage.tsx').default;
  hooks.render(Cart);
  await tick();
  let tree = hooks.render(Cart);
  let row = nodes(tree).find((n) => n.props?.onQuantityChange);
  assert.ok(row);
  row.props.onQuantityChange(2);
  await tick();
  tree = hooks.render(Cart);
  assert.equal(gets, 2);
  assert.ok(nodes(tree).some((n) => n.props?.children === '在庫が足りません'));
  row = nodes(tree).find((n) => n.props?.onQuantityChange);
  row.props.onRemove();
  await tick();
  hooks.render(Cart);
  assert.equal(gets, 3);
  assert.deepEqual(
    r.calls
      .filter((c) => ['PATCH', 'DELETE'].includes(c.init.method))
      .map((c) => c.init.method),
    ['PATCH', 'DELETE'],
  );
});

for (const flag of ['subscription', 'preorder'])
  for (const value of [undefined, true, false])
    test(`${flag}=${value} is encoded using the API boolean contract`, async () => {
      const r = runtime({ replies: [json(page([]))] });
      await r.load('api/productApi.ts').getProducts({ [flag]: value });
      assert.equal(
        new URL(r.calls[0].url, 'https://test.local').searchParams.get(flag),
        value === undefined ? null : String(value),
      );
    });

for (const search of ['', 'subscription=1&preorder=1'])
  test(`product screen keeps unchecked filters unspecified (${search})`, async () => {
    const hooks = hooksFixture();
    const r = runtime({
      overrides: {
        react: hooks.react,
        'react-router': {
          ...require('react-router'),
          useSearchParams: () => [new URLSearchParams(search), () => {}],
        },
      },
      reply: () => json(page([])),
    });
    hooks.render(r.load('pages/ProductListPage.tsx').default);
    await tick();
    const query = new URL(
      r.calls.find((c) => c.url.startsWith('/api/v1/products?')).url,
      'https://test.local',
    ).searchParams;
    assert.equal(query.get('subscription'), search ? 'true' : null);
    assert.equal(query.get('preorder'), search ? 'true' : null);
  });

test('product mock validates true/false and applies explicit false as exclusion', () => {
  const r = runtime();
  const { productsList, productSamples } = r.load(
    'mocks/rest/endpoint/get_api_v1_products.tsx',
  );
  for (const flag of ['subscription', 'preorder']) {
    const field = flag === 'subscription' ? 'isSubscription' : 'isPreorder';
    for (const value of ['true', 'false']) {
      const result = productsList.handler(
        new URL(
          `http://localhost/api/v1/products?${flag}=${value}&pageSize=50`,
        ),
      );
      assert.equal(result.status, 200);
      assert.equal(
        result.body.total,
        productSamples.filter((p) => p[field] === (value === 'true')).length,
      );
      assert.ok(
        result.body.items.every((p) => p[field] === (value === 'true')),
      );
    }
    assert.equal(
      productsList.handler(
        new URL(`http://localhost/api/v1/products?${flag}=1`),
      ).status,
      400,
    );
  }
});

const jobInput = {
  workDateIds: [1],
  message: null,
  answers: [],
  requirementsConfirmed: true,
};
const jobReceipt = {
  id: 10,
  jobId: 1,
  workDateIds: [1],
  message: null,
  answers: [],
  status: 'applied',
  decidedAt: null,
  createdAt: '2026-11-24T10:00:00+09:00',
};
const job = {
  id: 1,
  title: '収穫のお手伝い',
  producer: { id: 2, businessName: '農園', genre: 'agriculture' },
  areaId: 1,
  prefectureName: '北海道',
  termType: 'short',
  payUnit: 'hourly',
  payAmount: 1200,
  periodStart: null,
  periodEnd: null,
  workHours: '9〜12時',
  workPlace: '農園',
  slots: 5,
  inexperiencedOk: true,
  coverImageUrl: null,
  isAcceptingApplications: true,
  description: '作業',
  requirements: null,
  belongings: null,
  notes: null,
  hasApplied: false,
  applicationQuestions: [],
  workDates: page([
    {
      id: 1,
      workDate: '2099-12-01',
      neededCount: 5,
      remainingCount: 5,
      isSelectable: true,
    },
  ]),
};
test('job sends only defined fields including confirmation and requires a 201/applied receipt', async () => {
  const r = runtime({
    replies: [json({ csrfToken: 'token' }), json(jobReceipt, 201)],
  });
  const result = await r
    .load('api/jobApi.ts')
    .applyJob(1, { ...jobInput, extra: 'must not be sent' });
  assert.deepEqual(JSON.parse(r.calls[1].init.body), jobInput);
  assert.equal(result.id, 10);
});
for (const [status, body] of [
  [200, jobReceipt],
  [201, {}],
  [201, null],
  [201, { id: 0, status: 'applied' }],
  [201, { id: 1, status: 'hired' }],
])
  test(`invalid job receipt (${status}/${JSON.stringify(body)}) never completes`, async () => {
    const r = runtime({
      replies: [json({ csrfToken: 'token' }), json(body, status)],
    });
    await assert.rejects(r.load('api/jobApi.ts').applyJob(1, jobInput));
    assert.equal(r.calls.length, 2);
  });

function jobFixture({
  replies = [],
  data = structuredClone(job),
  mock = false,
} = {}) {
  const hooks = hooksFixture(),
    state = {
      data,
      loading: false,
      error: '',
      retry() {
        state.retried = true;
      },
    };
  const r = runtime({
    replies,
    mock,
    overrides: {
      react: hooks.react,
      'react-router': {
        ...require('react-router'),
        useParams: () => ({ jobId: '1' }),
      },
      '../hooks/usePublicContent': { usePublicContent: () => state },
    },
  });
  const Form = r.load('pages/JobApplyPage.tsx').default().type;
  let tree;
  const render = () => (tree = hooks.render(Form, { id: 1 }));
  const find = (predicate) => {
    const result = nodes(tree).find(predicate);
    assert.ok(result);
    return result;
  };
  const change = (predicate, value) => {
    find(predicate).props.onChange({ target: value });
    render();
  };
  const submit = () => {
    find((n) => n.type === 'form').props.onSubmit({ preventDefault() {} });
    render();
  };
  render();
  return {
    r,
    state,
    render,
    find,
    change,
    submit,
    get tree() {
      return tree;
    },
    fill() {
      if (data.workDates.total)
        change(
          (n) => n.type === 'input' && n.props.id !== 'requirements-confirmed',
          { checked: true },
        );
      change((n) => n.props?.id === 'requirements-confirmed', {
        checked: true,
      });
    },
  };
}
test('job form blocks submission until requirements are confirmed', () => {
  const f = jobFixture();
  f.change((n) => n.type === 'input' && !n.props.id, { checked: true });
  f.submit();
  assert.equal(f.r.calls.length, 0);
  assert.ok(f.find((n) => n.props?.id === 'requirements-error'));
});
test('job form submits in real mode once and renders the actual receipt', async () => {
  const pending = deferred();
  const f = jobFixture({
    replies: [json({ csrfToken: 'token' }), () => pending.promise],
  });
  f.fill();
  f.submit();
  f.submit();
  f.submit();
  await tick();
  assert.equal(f.r.calls.filter((c) => c.init.method === 'POST').length, 1);
  assert.deepEqual(JSON.parse(f.r.calls[1].init.body), jobInput);
  assert.equal(f.find((n) => n.props?.type === 'submit').props.disabled, true);
  pending.resolve(json(jobReceipt, 201));
  await tick();
  f.render();
  assert.ok(
    nodes(f.tree).some((n) => n.props?.children === '応募を受け付けました'),
  );
  assert.ok(
    !nodes(f.tree).some(
      (n) => n.props?.children === '実際の応募・通知は行いません。',
    ),
  );
});
test('job without dates allows an empty workDateIds array', async () => {
  const f = jobFixture({
    data: { ...job, workDates: page([]) },
    replies: [
      json({ csrfToken: 'token' }),
      json({ ...jobReceipt, workDateIds: [] }, 201),
    ],
  });
  f.fill();
  f.submit();
  f.submit();
  await tick();
  assert.deepEqual(JSON.parse(f.r.calls[1].init.body).workDateIds, []);
});
for (const [status, errorCode] of [
  [400, 'VALIDATION_ERROR'],
  [401, 'UNAUTHENTICATED'],
  [409, 'ALREADY_APPLIED'],
  [409, 'JOB_NOT_ACCEPTING'],
  [409, 'WORK_DATE_UNAVAILABLE'],
])
  test(`job form handles ${status}/${errorCode}`, async () => {
    const f = jobFixture({
      replies: [
        json({ csrfToken: 'token' }),
        json(
          {
            errorCode,
            errorMsg: '確認してください',
            details: { requirementsConfirmed: ['条件を確認'] },
          },
          status,
        ),
      ],
    });
    f.fill();
    f.submit();
    f.submit();
    await tick();
    f.render();
    assert.equal(f.r.calls.length, 2);
    if (status === 400)
      assert.equal(
        f.find((n) => n.props?.id === 'requirements-error').props.children,
        '条件を確認',
      );
    if (status === 401)
      assert.equal(
        f.find((n) => n.props?.to === '/signin').props.state.from,
        '/jobs/1/apply',
      );
    if (errorCode === 'ALREADY_APPLIED')
      assert.ok(f.find((n) => n.props?.to === '/mypage/jobs'));
    if (['JOB_NOT_ACCEPTING', 'WORK_DATE_UNAVAILABLE'].includes(errorCode)) {
      assert.equal(f.state.retried, true);
      assert.equal(
        f.find((n) => n.props?.id === 'requirements-confirmed').props.checked,
        false,
      );
    }
  });
test('job detail offers undated application and an applied-status link', () => {
  for (const applied of [false, true]) {
    const r = runtime({
      overrides: {
        '../hooks/usePublicContent': {
          usePublicContent: () => ({
            data: { ...job, workDates: page([]), hasApplied: applied },
            loading: false,
            error: '',
            retry() {},
          }),
        },
      },
    });
    const Page = r.load('pages/JobDetailPage.tsx').default;
    const html = renderToStaticMarkup(
      React.createElement(MemoryRouter, null, React.createElement(Page)),
    );
    assert.ok(html.includes(applied ? '/mypage/jobs' : '/jobs/1/apply'));
  }
});

test('actual job mock rejects missing confirmation, invalid dates, answers, and accepts undated applications', () => {
  const r = runtime();
  const { jobApply } = r.load(
    'mocks/rest/endpoint/post_api_v1_jobs_jobId_applications.tsx',
  );
  const { jobDetail, getMockJob } = r.load(
    'mocks/rest/endpoint/get_api_v1_jobs_jobId.tsx',
  );
  const send = (body) =>
    jobApply.handler(new URL('http://localhost/api/v1/jobs/1/applications'), {
      body: JSON.stringify(body),
    });
  for (const change of [
    { requirementsConfirmed: false },
    { workDateIds: [1, 1] },
    { workDateIds: [999] },
    { answers: ['x'] },
    { extra: 1 },
  ])
    assert.equal(send({ ...jobInput, ...change }).status, 400);
  jobDetail.body.workDates = page([]);
  const success = send({ ...jobInput, workDateIds: [] });
  assert.equal(success.status, 201);
  assert.equal(success.body.status, 'applied');
  assert.equal(success.body.decidedAt, null);
  assert.equal(getMockJob(1).hasApplied, true);
  assert.equal(
    send({ ...jobInput, workDateIds: [] }).body.errorCode,
    'ALREADY_APPLIED',
  );
});

const producer = {
  id: 7,
  businessName: '北の農園',
  genre: 'agriculture',
  prefectureName: '北海道',
  city: '札幌市',
  coverImageUrl: null,
  acceptsExperience: false,
  recruiting: false,
};
const story = {
  id: 44,
  producerId: 7,
  craft: null,
  method: null,
  process: null,
  environment: null,
  reason: '土を大切にする',
  goal: null,
  updatedAt: '2026-11-24T00:00:00+09:00',
  producer,
};
test('C4: story API works without title/category and distinguishes story ID from producer ID', async () => {
  const r = runtime({
    reply: (url) =>
      url.startsWith('/api/v1/producers?')
        ? json(page([producer]))
        : json(story),
  });
  const api = r.load('api/storyApi.ts');
  const result = await api.getStory(44);
  assert.equal(result.producerId, 7);
  assert.equal(api.storyLead(result), '土を大切にする');
  await assert.rejects(api.getStory(7), (e) => e.status === 404);
  assert.equal(
    new URL(r.calls[0].url, 'http://localhost').searchParams.get('hasStory'),
    'true',
  );
  assert.ok(r.calls.some((c) => c.url === '/api/v1/producers/7/story'));
});
for (const allNull of [false, true])
  for (const name of ['HomePage', 'LearnPage', 'StoryDetailPage'])
    test(`C4: ${name} renders API-shaped story (allNull=${allNull})`, () => {
      const data = { ...story, reason: allNull ? null : story.reason };
      let count = 0;
      // HomePage は補足取得オプションを渡すため、ストーリーの読み込みは loadStories（名前で識別）になる
      const r = runtime({
        overrides: {
          '../hooks/usePublicContent': {
            usePublicContent: (loader) => ({
              data:
                name === 'HomePage'
                  ? loader.name === 'loadStories'
                    ? [data]
                    : null
                  : name === 'StoryDetailPage'
                    ? count++ === 0
                      ? data
                      : page([])
                    : [data],
              loading: false,
              error: '',
              retry() {},
            }),
          },
        },
      });
      const Component = r.load(`pages/${name}.tsx`).default;
      const html = renderToStaticMarkup(
        React.createElement(MemoryRouter, null, React.createElement(Component)),
      );
      assert.ok(html.includes('北の農園'));
      assert.equal(html.includes('土を大切にする'), !allNull);
    });

test('actual cart mock returns full cart, treats null stock as unlimited, and uses bodyless delete', () => {
  const r = runtime();
  const { cartItemAdd } = r.load(
    'mocks/rest/endpoint/post_api_v1_cart_items.tsx',
  );
  const { cartItemUpdate } = r.load(
    'mocks/rest/endpoint/patch_api_v1_cart_items_itemId.tsx',
  );
  const { cartItemDelete } = r.load(
    'mocks/rest/endpoint/delete_api_v1_cart_items_itemId.tsx',
  );
  const { productSamples } = r.load(
    'mocks/rest/endpoint/get_api_v1_products.tsx',
  );
  productSamples.find((p) => p.id === 1).stock = null;
  const added = cartItemAdd.handler(
    new URL('http://localhost/api/v1/cart/items'),
    { body: JSON.stringify({ productId: 1, quantity: 1 }) },
  );
  assert.equal(added.status, 200);
  assert.ok(Array.isArray(added.body.shipments));
  const id = added.body.items.find((i) => i.productId === 1).id;
  const url = new URL(`http://localhost/api/v1/cart/items/${id}`);
  const updated = cartItemUpdate.handler(url, {
    body: JSON.stringify({ quantity: 10 }),
  });
  assert.equal(updated.status, 200);
  assert.equal(updated.body.items.find((i) => i.id === id).quantity, 10);
  assert.equal(cartItemDelete.handler(url).status, 204);
  assert.equal(cartItemDelete.handler(url).status, 404);
});
