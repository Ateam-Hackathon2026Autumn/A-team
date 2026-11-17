import type { DashboardProduct, ProductImage } from '../../../types/product';
import type { MockResult } from '../../types';
import { hoursFromNow } from '../../helpers';
import {
  conflict,
  idFromPath,
  imageUrlFor,
  isObject,
  isStale,
  loadState,
  nextEtag,
  nextId,
  notFound,
  nowIso,
  paginate,
  preconditionFailed,
  readJsonBody,
  saveState,
  validationError,
} from './common';

// ダッシュボード商品のモックストア
//
// 一覧・詳細・登録・更新（公開切り替えを含む）・在庫更新・削除の各モックが、このデータを読み書きする
// 更新のたびに etag（"product-{id}-v{版数}"）と updatedAt が変わり、古い etag で更新すると 412 になる
//
// 初期データはログイン中の生産者（山本農園）の商品3件
//   1: 安曇野ふじ（公開中）  2: シャインマスカット（公開中・残りわずか）  3: りんごのドライチップス（非公開）

const STORAGE_KEY = 'tsunagaru-marche.mock-dashboard-products.v1';
const PRODUCER_ID = 1;
const MAX_INT = 2147483647;
const NOT_FOUND_MESSAGE = '商品が見つかりません。';

function seedProducts(): DashboardProduct[] {
  return [
    {
      id: 2,
      producerId: PRODUCER_ID,
      name: 'シャインマスカット',
      volume: '2房',
      categoryId: 2,
      shippingSettingId: 1,
      price: 5400,
      taxRate: 8,
      discountRate: null,
      description:
        '皮ごと食べられる、香り高いシャインマスカット。糖度18度以上のものだけを選んでお届けします。',
      method: '減農薬（県基準の50%以下）',
      isSubscription: false,
      isPreorder: false,
      acceptsDeliveryDate: true,
      publishStatus: 'public',
      salePrice: 5400,
      // 残りわずか
      stock: 3,
      ratingAvg: 4.9,
      reviewCount: 48,
      images: [
        {
          id: 4,
          key: 'products/2/shine-muscat-1.jpg',
          url: 'https://picsum.photos/seed/shine1/800/600',
          sortOrder: 0,
        },
      ],
      createdAt: hoursFromNow(-24 * 60),
      updatedAt: hoursFromNow(-2),
      etag: '"product-2-v5"',
    },
    {
      id: 1,
      producerId: PRODUCER_ID,
      name: '安曇野ふじ 家庭用',
      volume: '5kg',
      categoryId: 2,
      shippingSettingId: 1,
      price: 4800,
      taxRate: 8,
      discountRate: null,
      description:
        '北アルプスの雪どけ水で育てた、蜜たっぷりのふじりんご。見た目に小さな傷がある家庭用です。',
      method: '草生栽培・減農薬（県基準の50%以下）',
      isSubscription: false,
      isPreorder: false,
      acceptsDeliveryDate: true,
      publishStatus: 'public',
      salePrice: 4800,
      stock: 40,
      ratingAvg: 4.8,
      reviewCount: 126,
      images: [
        {
          id: 1,
          key: 'products/1/fuji-1.jpg',
          url: 'https://picsum.photos/seed/fuji1/800/600',
          sortOrder: 0,
        },
        {
          id: 2,
          key: 'products/1/fuji-2.jpg',
          url: 'https://picsum.photos/seed/fuji2/800/600',
          sortOrder: 1,
        },
      ],
      createdAt: hoursFromNow(-24 * 90),
      updatedAt: hoursFromNow(-5),
      etag: '"product-1-v12"',
    },
    {
      id: 3,
      producerId: PRODUCER_ID,
      name: 'りんごのドライチップス',
      volume: '50g×3',
      categoryId: 7,
      shippingSettingId: 1,
      price: 1500,
      taxRate: 8,
      discountRate: null,
      description: '規格外のりんごを薄切りにして、低温でじっくり乾燥させました。砂糖不使用です。',
      method: null,
      isSubscription: false,
      isPreorder: false,
      acceptsDeliveryDate: false,
      // 非公開
      publishStatus: 'private',
      salePrice: 1500,
      stock: 2,
      ratingAvg: null,
      reviewCount: 0,
      images: [
        {
          id: 3,
          key: 'products/3/apple-chips-1.jpg',
          url: 'https://picsum.photos/seed/chips1/800/600',
          sortOrder: 0,
        },
      ],
      createdAt: hoursFromNow(-24 * 30),
      updatedAt: hoursFromNow(-24 * 3),
      etag: '"product-3-v2"',
    },
  ];
}

type State = { products: DashboardProduct[] };

function isState(value: unknown): value is State {
  return (
    isObject(value) &&
    Array.isArray(value.products) &&
    value.products.every(
      (product) =>
        isObject(product) &&
        typeof product.id === 'number' &&
        typeof product.etag === 'string' &&
        typeof product.updatedAt === 'string' &&
        Array.isArray(product.images),
    )
  );
}

let state: State | null = null;

// 最初に使われたときに、保存内容（なければ初期データ）を読み込む
function getState(): State {
  state ??= loadState(STORAGE_KEY, isState) ?? { products: seedProducts() };

  return state;
}

function save(): void {
  saveState(STORAGE_KEY, getState());
}

function findProduct(url: URL, indexFromEnd = 0): DashboardProduct | undefined {
  const id = idFromPath(url, indexFromEnd);

  return getState().products.find((product) => product.id === id);
}

// 割引後の販売価格（フォームの表示と同じ計算）
function calcSalePrice(price: number, discountRate: number | null): number {
  return Math.floor((price * (100 - (discountRate ?? 0))) / 100);
}

// imageKeys を画像の配列にする（すでにある画像は ID・URL をそのまま使う）
function toImages(keys: string[], current: ProductImage[]): ProductImage[] {
  let lastId = Math.max(
    0,
    ...getState().products.flatMap((product) => product.images.map((image) => image.id)),
  );

  return keys.map((key, sortOrder) => {
    const existing = current.find((image) => image.key === key);

    if (existing !== undefined) {
      return { ...existing, sortOrder };
    }

    lastId += 1;

    return { id: lastId, key, url: imageUrlFor(key), sortOrder };
  });
}

// ---------------------------------------------------------------------------
// 入力チェック（画面側と同じ条件の最低限。本物の API の代わりに 400 を返す）
// ---------------------------------------------------------------------------

type ProductFields = Partial<
  Pick<
    DashboardProduct,
    | 'name'
    | 'volume'
    | 'categoryId'
    | 'shippingSettingId'
    | 'price'
    | 'taxRate'
    | 'discountRate'
    | 'description'
    | 'method'
    | 'isSubscription'
    | 'isPreorder'
    | 'acceptsDeliveryDate'
    | 'publishStatus'
    | 'stock'
  >
> & { imageKeys?: string[] };

type FieldName = keyof ProductFields;

const isText = (value: unknown, max: number) =>
  typeof value === 'string' && value.trim() !== '' && value.length <= max;
const isOptionalText = (value: unknown) => value === null || typeof value === 'string';
const isId = (value: unknown) => Number.isSafeInteger(value) && Number(value) >= 1;
const isCount = (value: unknown) =>
  Number.isInteger(value) && Number(value) >= 0 && Number(value) <= MAX_INT;

const fieldChecks: Record<FieldName, (value: unknown) => boolean> = {
  name: (value) => isText(value, 100),
  volume: (value) => isText(value, 50),
  categoryId: isId,
  shippingSettingId: isId,
  price: isCount,
  taxRate: (value) => value === 8 || value === 10,
  discountRate: (value) =>
    value === null || (Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 99),
  description: isOptionalText,
  method: isOptionalText,
  isSubscription: (value) => typeof value === 'boolean',
  isPreorder: (value) => typeof value === 'boolean',
  acceptsDeliveryDate: (value) => typeof value === 'boolean',
  publishStatus: (value) => value === 'draft' || value === 'public' || value === 'private',
  stock: (value) => value === null || isCount(value),
  imageKeys: (value) =>
    Array.isArray(value) &&
    value.length <= 10 &&
    value.every((key) => typeof key === 'string' && key !== '') &&
    new Set(value).size === value.length,
};

type ParseResult =
  | { ok: true; fields: ProductFields }
  | { ok: false; errors: Record<string, string[]> };

// 送られた項目だけチェックする（required の項目は、送られていなければエラー）
function parseFields(input: unknown, required: FieldName[]): ParseResult {
  if (!isObject(input)) {
    return { ok: false, errors: { body: ['リクエストの形式が正しくありません。'] } };
  }

  const errors: Record<string, string[]> = {};
  const fields: Record<string, unknown> = {};

  for (const [name, check] of Object.entries(fieldChecks)) {
    if (!(name in input)) {
      if (required.includes(name as FieldName)) {
        errors[name] = ['入力してください。'];
      }
    } else if (check(input[name])) {
      fields[name] = input[name];
    } else {
      errors[name] = ['正しい値を入力してください。'];
    }
  }

  return Object.keys(errors).length > 0
    ? { ok: false, errors }
    : { ok: true, fields: fields as ProductFields };
}

// 公開するのに足りない項目があれば 409
function publishConflict(product: DashboardProduct): MockResult | null {
  if (
    product.publishStatus === 'public' &&
    (product.images.length === 0 ||
      (product.description ?? '').trim() === '' ||
      product.stock === null ||
      product.salePrice <= 0)
  ) {
    return conflict('PRODUCT_STATE_CONFLICT', '公開するには画像・商品説明・在庫数が必要です。');
  }

  return null;
}

// 掲載停止中（運営が停止）の商品は生産者が変更できない
function suspendedConflict(product: DashboardProduct): MockResult | null {
  return product.publishStatus === 'suspended'
    ? conflict('PRODUCT_STATE_CONFLICT', '掲載停止中の商品は変更できません。')
    : null;
}

// ---------------------------------------------------------------------------
// 各APIの処理
// ---------------------------------------------------------------------------

// GET /api/v1/dashboard/products（更新の新しい順）
function listProducts(url: URL): MockResult {
  const sorted = [...getState().products].sort(
    (a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt) || b.id - a.id,
  );
  const page = paginate(sorted, url);

  return page === null
    ? validationError({ page: ['正しい値を指定してください。'] })
    : { status: 200, body: page };
}

// GET /api/v1/dashboard/products/:productId
function getProduct(url: URL): MockResult {
  const product = findProduct(url);

  return product === undefined ? notFound(NOT_FOUND_MESSAGE) : { status: 200, body: product };
}

// POST /api/v1/dashboard/products
function createProduct(init?: RequestInit): MockResult {
  const parsed = parseFields(readJsonBody(init), [
    'name',
    'volume',
    'categoryId',
    'shippingSettingId',
    'price',
    'taxRate',
    'publishStatus',
    'imageKeys',
  ]);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  const { imageKeys = [], ...fields } = parsed.fields;
  const products = getState().products;
  const id = nextId(products);
  const now = nowIso();
  const product: DashboardProduct = {
    id,
    producerId: PRODUCER_ID,
    name: '',
    volume: '',
    categoryId: 1,
    shippingSettingId: 1,
    price: 0,
    taxRate: 8,
    discountRate: null,
    description: null,
    method: null,
    isSubscription: false,
    isPreorder: false,
    acceptsDeliveryDate: false,
    publishStatus: 'draft',
    stock: null,
    ...fields,
    salePrice: 0,
    ratingAvg: null,
    reviewCount: 0,
    images: toImages(imageKeys, []),
    createdAt: now,
    updatedAt: now,
    etag: nextEtag('product', id),
  };
  product.salePrice = calcSalePrice(product.price, product.discountRate);

  const error = publishConflict(product);

  if (error !== null) {
    return error;
  }

  products.push(product);
  save();

  return { status: 201, body: product };
}

// PATCH /api/v1/dashboard/products/:productId（送った項目だけ更新。公開切り替えは publishStatus だけ送る）
function updateProduct(url: URL, init?: RequestInit): MockResult {
  const product = findProduct(url);

  if (product === undefined) {
    return notFound(NOT_FOUND_MESSAGE);
  }

  if (isStale(init, product.etag)) {
    return preconditionFailed();
  }

  const stateError = suspendedConflict(product);

  if (stateError !== null) {
    return stateError;
  }

  const parsed = parseFields(readJsonBody(init), []);

  if (!parsed.ok) {
    return validationError(parsed.errors);
  }

  // 在庫は在庫更新APIで変える（この API では受け付けない）
  const { imageKeys, stock: _ignoredStock, ...fields } = parsed.fields;
  const updated: DashboardProduct = {
    ...product,
    ...fields,
    images: imageKeys === undefined ? product.images : toImages(imageKeys, product.images),
  };
  updated.salePrice = calcSalePrice(updated.price, updated.discountRate);

  const error = publishConflict(updated);

  if (error !== null) {
    return error;
  }

  updated.updatedAt = nowIso();
  updated.etag = nextEtag('product', product.id, product.etag);
  Object.assign(product, updated);
  save();

  return { status: 200, body: product };
}

// PATCH /api/v1/dashboard/products/:productId/stock（増減ではなく変更後の数。null は未設定）
function updateStock(url: URL, init?: RequestInit): MockResult {
  const product = findProduct(url, 1);

  if (product === undefined) {
    return notFound(NOT_FOUND_MESSAGE);
  }

  if (isStale(init, product.etag)) {
    return preconditionFailed();
  }

  const stateError = suspendedConflict(product);

  if (stateError !== null) {
    return stateError;
  }

  const input = readJsonBody(init);

  if (!isObject(input) || !(input.stock === null || isCount(input.stock))) {
    return validationError({ stock: ['在庫数は0以上の整数で指定してください。'] });
  }

  if (input.stock === null && product.publishStatus === 'public') {
    return conflict('STOCK_STATE_CONFLICT', '公開中の商品は在庫数を未設定にできません。');
  }

  product.stock = input.stock as number | null;
  product.updatedAt = nowIso();
  product.etag = nextEtag('product', product.id, product.etag);
  save();

  return {
    status: 200,
    body: {
      productId: product.id,
      stock: product.stock,
      updatedAt: product.updatedAt,
      etag: product.etag,
    },
  };
}

// DELETE /api/v1/dashboard/products/:productId（非公開・下書きのみ）
function deleteProduct(url: URL, init?: RequestInit): MockResult {
  const product = findProduct(url);

  if (product === undefined) {
    return notFound(NOT_FOUND_MESSAGE);
  }

  if (isStale(init, product.etag)) {
    return preconditionFailed();
  }

  if (product.publishStatus === 'public' || product.publishStatus === 'suspended') {
    return conflict('PRODUCT_DELETE_CONFLICT', '公開中または注文のある商品は削除できません。');
  }

  const products = getState().products;
  products.splice(products.indexOf(product), 1);
  save();

  return { status: 204 };
}

// ダッシュボード集計（GET /api/v1/dashboard/summary）用。公開中の商品数
function countPublishedProducts(): number {
  return getState().products.filter((product) => product.publishStatus === 'public').length;
}

export {
  countPublishedProducts,
  createProduct,
  deleteProduct,
  getProduct,
  listProducts,
  updateProduct,
  updateStock,
};
