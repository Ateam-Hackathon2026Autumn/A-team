import ApiError from "./apiError";
import { apiFetch } from "./client";
import { USE_MOCK } from "../config/env";
import type { Cart } from "../types/cart";
import { resetMockCart } from "../mocks/rest/endpoint/get_api_v1_cart";

async function checkResponse(response: Response): Promise<void> {
  if (response.ok) return;
  const message = response.status === 409
    ? "在庫が不足しているか、販売状況が変わりました。カートの内容をご確認ください。"
    : response.status === 412
      ? "カートの内容が変更されました。最新の内容をご確認ください。"
      : response.status === 404
        ? "カートの商品が見つかりません。最新の内容をご確認ください。"
        : response.status === 400
          ? "数量は1〜10点の整数で指定してください。"
          : "カートの処理に失敗しました。時間をおいて再度お試しください。";
  throw new ApiError(response.status, message);
}

export async function getCart(signal?: AbortSignal): Promise<Cart> {
  const response = await apiFetch("/api/v1/cart", { signal });
  await checkResponse(response);
  return response.json() as Promise<Cart>;
}

function requireMock() {
  if (!USE_MOCK) throw new Error("カートの更新は認証・CSRF連携の接続確認後に利用できます。");
}

// デモ専用。実APIへ初期化リクエストは送信しない。
export async function resetDemoCart(): Promise<void> {
  requireMock();
  resetMockCart();
}

export async function updateCartItem(itemId: number, quantity: number, signal?: AbortSignal): Promise<Cart> {
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

export async function removeCartItem(itemId: number, signal?: AbortSignal): Promise<void> {
  requireMock();
  const response = await apiFetch(`/api/v1/cart/items/${itemId}`, { method: "DELETE", signal });
  await checkResponse(response);
}
