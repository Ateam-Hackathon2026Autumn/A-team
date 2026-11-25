import { USE_MOCK } from "../config/env";

export async function resetDemoCart(): Promise<void> {
  if (!USE_MOCK) {
    throw new Error("デモカートの初期化はモック環境でのみ利用できます。");
  }
  const { resetMockCart } = await import("./rest/endpoint/get_api_v1_cart");
  resetMockCart();
}

