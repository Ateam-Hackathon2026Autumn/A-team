import ApiError from "./apiError";
import { apiFetch } from "./client";
import type { Category, ProductDetail, ProductListResponse } from "../types/product";

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(path, { signal });
  if (!response.ok) throw new ApiError(response.status, "商品情報の取得に失敗しました。");
  return response.json() as Promise<T>;
}

// 全ページを取得してから画面内で絞り込む。先頭ページだけを検索対象にしない。
export async function getProducts(signal?: AbortSignal): Promise<ProductListResponse> {
  const first = await getJson<ProductListResponse>("/api/v1/products", signal);
  const items = [...first.items];
  for (let page = 2; page <= first.totalPages; page += 1) {
    const result = await getJson<ProductListResponse>(`/api/v1/products?page=${page}`, signal);
    items.push(...result.items);
  }
  return { ...first, items };
}
export const getCategories = (signal?: AbortSignal) => getJson<{ items: Category[] }>("/api/v1/categories", signal);
export const getProduct = (id: number, signal?: AbortSignal) => getJson<ProductDetail>(`/api/v1/products/${id}`, signal);

// 認証・CSRF・リクエスト形式の正式な接続確認まで、追加操作はモック環境に限定する。
export async function addProductToCart(productId: number, quantity: number): Promise<void> {
  const response = await apiFetch("/api/v1/cart/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productId, quantity }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, response.status === 409
      ? "在庫が不足しています。数量をご確認ください。"
      : response.status === 400
        ? "カート内の同じ商品は合計10点までです。数量をご確認ください。"
        : "カートに追加できませんでした。もう一度お試しください。");
  }
}
