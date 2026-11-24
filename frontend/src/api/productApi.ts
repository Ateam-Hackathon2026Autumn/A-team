import { toApiError } from "./apiError";
import { apiFetch } from "./client";
import type {
  Category,
  ProductDetail,
  ProductListResponse,
  ProductQuery,
} from "../types/publicProduct";

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(path, { signal });
  if (!response.ok) {
    throw await toApiError(response, "商品情報の取得に失敗しました。");
  }
  return response.json() as Promise<T>;
}

// バックエンドの公開商品APIに合わせたクエリ。
export function getProducts(
  query: ProductQuery = {},
  signal?: AbortSignal,
): Promise<ProductListResponse> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    pageSize: String(query.pageSize ?? 9),
    sort: query.sort ?? "popular",
  });
  if (query.q?.trim()) params.set("q", query.q.trim());
  if (query.categoryId !== undefined) params.set("categoryId", String(query.categoryId));
  if (query.producerId !== undefined) params.set("producerId", String(query.producerId));
  if (query.price && query.price !== "all") params.set("price", query.price);
  if (query.subscription) params.set("subscription", "true");
  if (query.preorder) params.set("preorder", "true");
  return getJson<ProductListResponse>(`/api/v1/products?${params}`, signal);
}

export const getCategories = (signal?: AbortSignal) =>
  getJson<{ items: Category[] }>("/api/v1/categories", signal);

export const getProduct = (id: number, signal?: AbortSignal) =>
  getJson<ProductDetail>(`/api/v1/products/${id}`, signal);
