import type {
  Category,
  DashboardProduct,
  DashboardProductList,
  ProductCreateInput,
  ProductPublishStatus,
  ProductUpdateInput,
  ShippingSetting,
} from '../types/product';
import { toApiError } from './apiError';
import { apiFetch, type ApiFetchOptions } from './client';

// 公開・非公開の切り替えや在庫更新の結果のうち、一覧に反映するもの
type ProductUpdateResult = {
  updatedAt: string;
  etag?: string;
};

// 実APIは ETag を返さない。旧モックが返す場合だけ If-Match を付ける
async function sendProductRequest(
  path: string,
  method: 'PATCH' | 'DELETE',
  etag?: string,
  body?: unknown,
): Promise<Response> {

  return apiFetch(path, {
    method,
    headers: {
      ...(etag ? { 'If-Match': etag } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

// 本人の商品一覧を取得（公開状態に関係なく、更新の新しい順）
async function getDashboardProducts(
  page: number,
): Promise<DashboardProductList> {
  const response = await apiFetch(`/api/v1/dashboard/products?page=${page}`);

  if (response.ok) {
    return (await response.json()) as DashboardProductList;
  }

  throw await toApiError(response, '商品一覧を取得できませんでした');
}

// 本人の商品を1件取得（編集画面用。下書き・非公開も取得できる）
async function getDashboardProduct(productId: number): Promise<DashboardProduct> {
  const response = await apiFetch(`/api/v1/dashboard/products/${productId}`);

  if (response.ok) {
    return (await response.json()) as DashboardProduct;
  }

  throw await toApiError(response, '商品を取得できませんでした');
}

// カテゴリー一覧を取得（一覧画面の補足情報は options に SUPPLEMENTARY_FETCH を渡す）
async function getCategories(options: ApiFetchOptions = {}): Promise<Category[]> {
  const response = await apiFetch('/api/v1/categories', {}, options);

  if (response.ok) {
    const { items } = (await response.json()) as { items: Category[] };

    return items;
  }

  throw await toApiError(response, 'カテゴリーを取得できませんでした');
}

// 配送設定（温度帯ごとの送料・発送目安）の一覧を取得
// ※ 配送設定取得APIは仕様が未作成のため、モックは仮の形（src/mocks/rest/endpoint/get_api_v1_dashboard_shipping-settings.tsx）
async function getShippingSettings(): Promise<ShippingSetting[]> {
  const response = await apiFetch('/api/v1/dashboard/shipping-settings');

  if (response.ok) {
    const { items } = (await response.json()) as { items: ShippingSetting[] };

    return items;
  }

  throw await toApiError(response, '配送設定を取得できませんでした');
}

// 商品を登録
async function createProduct(
  input: ProductCreateInput,
): Promise<DashboardProduct> {
  const response = await apiFetch('/api/v1/dashboard/products', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });

  if (response.ok) {
    return (await response.json()) as DashboardProduct;
  }

  throw await toApiError(response, '商品を登録できませんでした');
}

// 商品の内容を更新（画像は imageKeys の内容で置き換わる）
async function updateProduct(
  productId: number,
  input: ProductUpdateInput,
  etag?: string,
): Promise<DashboardProduct> {
  const response = await sendProductRequest(
    `/api/v1/dashboard/products/${productId}`,
    'PATCH',
    etag,
    input,
  );

  if (response.ok) {
    return (await response.json()) as DashboardProduct;
  }

  throw await toApiError(response, '商品を保存できませんでした');
}

// 公開状態を変更
async function updateProductPublishStatus(
  productId: number,
  publishStatus: Exclude<ProductPublishStatus, 'suspended'>,
  etag?: string,
): Promise<ProductUpdateResult> {
  const response = await sendProductRequest(
    `/api/v1/dashboard/products/${productId}`,
    'PATCH',
    etag,
    { publishStatus },
  );

  if (response.ok) {
    return (await response.json()) as ProductUpdateResult;
  }

  throw await toApiError(response, '公開状態を変更できませんでした');
}

// 在庫数を変更（増減ではなく変更後の数を送る。null は在庫管理なし）
async function updateProductStock(
  productId: number,
  stock: number | null,
  etag?: string,
): Promise<ProductUpdateResult> {
  const response = await sendProductRequest(
    `/api/v1/dashboard/products/${productId}/stock`,
    'PATCH',
    etag,
    { stock },
  );

  if (response.ok) {
    return (await response.json()) as ProductUpdateResult;
  }

  throw await toApiError(response, '在庫数を変更できませんでした');
}

// 商品を削除（非公開・下書きのみ可能）
async function deleteProduct(productId: number, etag?: string): Promise<void> {
  const response = await sendProductRequest(
    `/api/v1/dashboard/products/${productId}`,
    'DELETE',
    etag,
  );

  if (!response.ok) {
    throw await toApiError(response, '商品を削除できませんでした');
  }
}

export {
  createProduct,
  deleteProduct,
  getCategories,
  getDashboardProduct,
  getDashboardProducts,
  getShippingSettings,
  updateProduct,
  updateProductPublishStatus,
  updateProductStock,
};
