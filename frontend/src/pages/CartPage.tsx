import { useEffect, useMemo, useRef, useState } from "react";
import { useAtomValue } from "jotai";
import { Link } from "react-router";
import ApiError from "../api/apiError";
import { getCart, removeCartItem, updateCartItem } from "../api/cartApi";
import { getProduct } from "../api/productApi";
import { apiErrorMessage } from "../utils/apiErrorMessage";
import CartItemRow from "../components/cart/CartItemRow";
import { yen } from "../components/products/ProductCard";
import Button from "../components/ui/Button";
import { USE_MOCK } from "../config/env";
import { loginStatusAtom } from "../stores/userAtom";
import type { Cart, CartItem } from "../types/cart";
import type { ProductDetail } from "../types/publicProduct";

type CartGroup = {
  key: string;
  product?: ProductDetail;
  items: CartItem[];
};

const temperatureLabels: Record<string, string> = { normal: "常温", chilled: "冷蔵", frozen: "冷凍" };
const linkClass = "text-marche-green no-underline hover:underline";

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [products, setProducts] = useState<Record<number, ProductDetail>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");
  const [detailsWarning, setDetailsWarning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const operationLock = useRef(false);
  const loggedIn = useAtomValue(loginStatusAtom) === "loggedIn";

  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setLoadError("");
    setProducts({});
    setDetailsWarning(false);
    async function load() {
      try {
        const result = await getCart(request.signal);
        if (request.signal.aborted) return;
        setCart(result);
        // 補足情報の取得に失敗しても、カートの商品・金額・削除操作は表示する。
        const ids = [...new Set(result.items.map((item) => item.productId))];
        const details = await Promise.allSettled(ids.map((id) => getProduct(id, request.signal)));
        if (request.signal.aborted) return;
        const available: Record<number, ProductDetail> = {};
        for (const detail of details) if (detail.status === "fulfilled") available[detail.value.id] = detail.value;
        setProducts(available);
        setDetailsWarning(details.some((detail) => detail.status === "rejected"));
      } catch (cause: unknown) {
        if (!request.signal.aborted) setLoadError(apiErrorMessage(cause, "カートを取得できませんでした。時間をおいて再度お試しください。"));
      } finally {
        if (!request.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => request.abort();
  }, [retry]);

  const groups = useMemo(() => {
    const result = new Map<string, CartGroup>();
    for (const item of cart?.items ?? []) {
      const product = products[item.productId];
      const key = product ? `${product.producer.id}-${product.shipping.temperatureZone}` : `unknown-${item.id}`;
      const group = result.get(key) ?? { key, product, items: [] };
      group.items.push(item);
      result.set(key, group);
    }
    return [...result.values()];
  }, [cart, products]);

  async function changeItem(item: CartItem, quantity?: number) {
    const request = controller.current;
    if (!request || request.signal.aborted || operationLock.current || !USE_MOCK) return;
    operationLock.current = true;
    setBusy(true);
    setActionError("");
    setMessage("");
    try {
      let updated: Cart;
      if (quantity === undefined) {
        await removeCartItem(item.id, request.signal);
        updated = await getCart(request.signal);
      } else {
        updated = await updateCartItem(item.id, quantity, request.signal);
      }
      if (request.signal.aborted) return;
      setCart(updated);
      setMessage(quantity === undefined ? "商品をカートから削除しました。" : "数量を変更しました。");
    } catch (cause) {
      if (request.signal.aborted) return;
      setActionError(apiErrorMessage(cause, "カートを更新できませんでした。", "quantity"));
      if (cause instanceof ApiError && [404, 409, 412].includes(cause.status)) {
        try {
          const latest = await getCart(request.signal);
          if (!request.signal.aborted) setCart(latest);
          const ids = [...new Set(latest.items.map((line) => line.productId))];
          const details = await Promise.allSettled(ids.map((id) => getProduct(id, request.signal)));
          if (!request.signal.aborted) {
            const available: Record<number, ProductDetail> = {};
            for (const detail of details) {
              if (detail.status === "fulfilled") available[detail.value.id] = detail.value;
            }
            setProducts(available);
            setDetailsWarning(details.some((detail) => detail.status === "rejected"));
          }
        } catch {
          if (!request.signal.aborted) setActionError("カートを更新できず、最新の内容も取得できませんでした。「カートを再読み込み」をお試しください。");
        }
      }
    } finally {
      operationLock.current = false;
      if (!request.signal.aborted) setBusy(false);
    }
  }

  const itemCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
  const canProceed = Boolean(cart?.items.length && cart.canCheckout && cart.items.every((item) => item.purchasable));

  async function resetCart() {
    if (!USE_MOCK || operationLock.current) return;
    operationLock.current = true;
    setBusy(true);
    try {
      const { resetDemoCart } = await import("../mocks/demoCart");
      await resetDemoCart();
      setActionError("");
      setMessage("デモカートを初期状態に戻しました。");
      setRetry((value) => value + 1);
    } catch {
      setActionError("デモカートを初期化できませんでした。");
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1100px] px-5 py-7 sm:px-8">
      <nav
        aria-label="パンくず"
        className="mb-6 flex flex-wrap gap-2 text-xs text-marche-muted"
      >
        <Link
          to="/"
          className={linkClass}
        >
          ホーム
        </Link>
        <span aria-hidden="true">/</span>
        <Link
          to="/products"
          className={linkClass}
        >
          商品一覧
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">カート</span>
      </nav>
      <ol
        aria-label="購入の手順"
        className="m-0 mb-8 grid list-none grid-cols-4 gap-2 p-0 text-xs sm:text-sm"
      >
        {["カート", "お届け先・支払い", "確認", "完了"].map((label, index) => (
          <li
            key={label}
            aria-current={index === 0 ? "step" : undefined}
            className={index === 0 ? "font-bold text-marche-green" : "text-marche-muted"}
          >
            <span className={`mb-2 block h-1 rounded-full ${index === 0 ? "bg-marche-green" : "bg-marche-line"}`} />
            {index + 1}. {label}
          </li>
        ))}
      </ol>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="m-0 font-serif text-3xl font-bold">カート {!loading && !loadError && <span className="text-base font-normal text-marche-muted">{itemCount}点</span>}</h1>
        <Link
          to="/products"
          className={`inline-flex min-h-11 items-center text-sm ${linkClass}`}
        >
          ← 買い物を続ける
        </Link>
      </div>
      {USE_MOCK && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-marche-sage px-4 py-3">
          <p className="m-0 text-xs text-marche-muted">画面確認用のデモです。実際の注文・決済は行いません。カートは同じタブのセッションに保存します。</p>
          <button
            type="button"
            disabled={busy || loading}
            onClick={() => void resetCart()}
            className="min-h-11 cursor-pointer border-0 bg-transparent px-2 font-sans text-xs text-marche-green underline disabled:cursor-not-allowed disabled:text-gray-400"
          >
            デモカートを初期状態に戻す
          </button>
        </div>
      )}
      <div
        aria-live="polite"
        aria-atomic="true"
      >
        {message && (
          <p
            role="status"
            className="m-0 mb-4 rounded-xl bg-marche-sage p-4 text-sm"
          >
            {message}
          </p>
        )}
      </div>
      {actionError && (
        <div
          role="alert"
          className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4"
        >
          <p className="m-0 text-sm text-red-800">{actionError}</p>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => {
              setActionError("");
              setRetry((value) => value + 1);
            }}
            className="mt-3"
          >
            カートを再読み込み
          </Button>
        </div>
      )}

      {loading ? (
        <p
          role="status"
          className="m-0 rounded-2xl bg-white p-8"
        >
          カートを読み込んでいます…
        </p>
      ) : loadError ? (
        <div
          role="alert"
          className="rounded-2xl border border-red-200 bg-white p-6"
        >
          <p className="m-0 mb-4 text-red-800">{loadError}</p>
          <Button onClick={() => setRetry((value) => value + 1)}>再試行</Button>
        </div>
      ) : !cart?.items.length ? (
        <section className="rounded-3xl border border-marche-line bg-white px-5 py-14 text-center">
          <h2 className="m-0 font-serif text-2xl font-bold">カートは空です</h2>
          <p className="m-0 mt-3 text-sm text-marche-muted">旬の商品や、応援したい生産者の商品を探してみましょう。</p>
          <Link
            to="/products"
            className="mt-6 inline-flex min-h-12 items-center justify-center rounded-full bg-marche-green px-6 py-3 text-sm font-bold text-white no-underline hover:bg-marche-green-dark"
          >
            商品を探す →
          </Link>
        </section>
      ) : (
        <div className="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_310px]">
          <div
            className="min-w-0 space-y-5"
            aria-busy={busy}
          >
            <p className="m-0 rounded-xl bg-marche-sage p-4 text-sm text-marche-muted">産地から直送するため、送料・お届け日・配送温度帯は生産者ごとに異なります。</p>
            {detailsWarning && <p className="m-0 text-xs text-marche-muted">一部の商品画像・生産者・配送情報を取得できませんでした。商品名・数量・金額はカートの情報を表示しています。</p>}
            {groups.map((group) => (
              <section
                key={group.key}
                aria-label={group.product?.producer.businessName ?? "生産者情報を取得できない商品"}
                className="overflow-hidden rounded-2xl border border-marche-line bg-white"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-marche-line bg-marche-sage/50 px-5 py-4">
                  {group.product ? (
                    <Link
                      to={`/producers/${group.product.producer.id}`}
                      className="text-sm font-bold text-marche-ink no-underline hover:underline"
                    >
                      {group.product.producer.businessName}
                      <span className="ml-2 text-xs font-normal text-marche-muted">{group.product.producer.prefectureName}</span>
                    </Link>
                  ) : (
                    <h2 className="m-0 text-sm font-bold">生産者情報未取得</h2>
                  )}
                  {group.product && <span className="rounded-md bg-white px-2 py-1 text-xs">{temperatureLabels[group.product.shipping.temperatureZone] ?? group.product.shipping.temperatureZone}便</span>}
                </div>
                <ul className="m-0 list-none divide-y divide-marche-line px-5 py-0">
                  {group.items.map((item) => (
                    <CartItemRow
                      key={item.id}
                      item={item}
                      product={products[item.productId]}
                      busy={busy}
                      onQuantityChange={(quantity) => void changeItem(item, quantity)}
                      onRemove={() => void changeItem(item)}
                    />
                  ))}
                </ul>
                <div className="space-y-2 border-t border-marche-line px-5 py-4 text-sm">
                  <p className="m-0 flex justify-between gap-3">
                    <span>この便の商品小計</span>
                    <span className="font-bold">{group.items.some((item) => item.subtotal === null) ? "一部金額未確定" : yen(group.items.reduce((sum, item) => sum + (item.subtotal ?? 0), 0))}</span>
                  </p>
                  {group.product && (
                    <p className="m-0 text-xs text-marche-muted">
                      {group.product.shipping.leadTimeText} · 参考送料 {yen(group.product.shipping.shippingFee)}
                    </p>
                  )}
                  <p className="m-0 text-xs text-marche-muted">送料はお届け先・注文内容に応じて購入手続きで確定します。</p>
                </div>
              </section>
            ))}
          </div>
          <aside
            aria-label="ご注文金額"
            className="rounded-2xl border border-marche-line bg-white p-6 shadow-sm lg:sticky lg:top-28"
          >
            <h2 className="m-0 font-serif text-xl font-bold">ご注文金額</h2>
            <dl className="m-0 mt-5 space-y-3">
              <div className="flex justify-between gap-3 text-sm">
                <dt>商品小計（{itemCount}点）</dt>
                <dd className="m-0">{yen(cart.itemsTotal)}</dd>
              </div>
              <div className="flex justify-between gap-3 text-sm text-marche-muted">
                <dt>送料</dt>
                <dd className="m-0">注文時に確定</dd>
              </div>
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-t border-marche-line pt-4">
                <dt className="text-sm font-bold">商品合計（税込・送料別）</dt>
                <dd className="m-0 text-2xl font-bold">{yen(cart.itemsTotal)}</dd>
              </div>
            </dl>
            {cart.items.some((item) => item.subtotal === null) && <p className="m-0 mt-3 text-xs text-red-800">価格を取得できない商品は合計に含まれていません。</p>}
            {!canProceed && (
              <p
                role="status"
                className="m-0 mt-4 text-sm text-red-800"
              >
                購入できない商品があります。数量を変更するか、対象商品を削除してください。
              </p>
            )}
            {canProceed && !busy ? (
              <Link
                to={loggedIn ? "/checkout" : "/signin"}
                state={loggedIn ? { quoteToken: cart.quoteToken } : { from: { pathname: "/cart" } }}
                className="mt-5 flex min-h-12 items-center justify-center rounded-full bg-marche-green px-4 py-3 text-sm font-bold text-white no-underline hover:bg-marche-green-dark"
              >
                {loggedIn ? "購入手続きへ →" : "ログインして購入手続きへ"}
              </Link>
            ) : (
              <Button
                disabled
                className="mt-5 w-full"
              >
                {busy ? "更新しています…" : "購入手続きへ"}
              </Button>
            )}
            <p className="m-0 mt-3 text-xs leading-6 text-marche-muted">購入手続き画面は準備中です。現在はカートの確認・変更まで利用できます。</p>
            {!USE_MOCK && <p className="m-0 mt-3 text-xs text-marche-muted">数量変更・削除は認証・CSRF連携の接続確認後に利用できます。</p>}
            <Link
              to="/products"
              className={`mt-4 flex min-h-11 items-center justify-center text-sm ${linkClass}`}
            >
              買い物を続ける
            </Link>
          </aside>
        </div>
      )}
    </div>
  );
}
