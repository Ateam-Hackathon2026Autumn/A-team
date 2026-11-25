import { toApiError } from "./apiError";
import { apiFetch } from "./client";
import { USE_MOCK } from "../config/env";
import type { Cart } from "../types/cart";
function requireMock(): void {
  if (!USE_MOCK) {
    throw new Error("カートの更新は認証・CSRF連携の接続確認後に利用できます。");
  }
}

async function checkResponse(response: Response): Promise<void> {
  if (response.ok) return;
  const fallback = response.status === 409
    ? "在庫が不足しているか、販売状況が変わりました。"
    : response.status === 412
      ? "カートの内容が変更されました。最新の内容をご確認ください。"
      : response.status === 404
        ? "カートの商品が見つかりません。"
        : response.status === 400
          ? "数量は1〜10点の整数で指定してください。"
          : "カートの処理に失敗しました。時間をおいて再度お試しください。";
  throw await toApiError(response, fallback);
}

export async function getCart(signal?: AbortSignal): Promise<Cart> {
  const response = await apiFetch("/api/v1/cart", { signal });
  await checkResponse(response);
  return response.json() as Promise<Cart>;
}

export async function addCartItem(
  productId: number,
  quantity: number,
): Promise<void> {
  requireMock();
  const response = await apiFetch("/api/v1/cart/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productId, quantity }),
  });
  await checkResponse(response);
}

export async function updateCartItem(
  itemId: number,
  quantity: number,
  signal?: AbortSignal,
): Promise<Cart> {
  requireMock();
  const response = await apiFetch(`/api/v1/cart/items/${itemId}`, {
    method: "PATCH",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quantity }),
  });
  await checkResponse(response);
  return response.json() as Promise<Cart>;
}

export async function removeCartItem(
  itemId: number,
  signal?: AbortSignal,
): Promise<void> {
  requireMock();
  const response = await apiFetch(`/api/v1/cart/items/${itemId}`, {
    method: "DELETE",
    signal,
  });
  await checkResponse(response);
}
