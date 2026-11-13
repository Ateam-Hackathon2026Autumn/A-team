import { useEffect, useState } from "react";
import { useAtomValue } from "jotai";
import { Link, useParams } from "react-router";
import ApiError from "../api/apiError";
import { getProduct, getProducts } from "../api/productApi";
import { addCartItem } from "../api/cartApi";
import { apiErrorMessage } from "../utils/apiErrorMessage";
import ProductCard, { ProductImage, yen } from "../components/products/ProductCard";
import Button from "../components/ui/Button";
import { USE_MOCK } from "../config/env";
import { loginStatusAtom } from "../stores/userAtom";
import type { Product, ProductDetail } from "../types/publicProduct";

// IDが変わった際に画像・数量・メッセージをリセットする。
export default function ProductDetailPage() {
  const { productId = "" } = useParams();
  return (
    <ProductDetailContent
      key={productId}
      productId={productId}
    />
  );
}

function ProductDetailContent({ productId }: { productId: string }) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [related, setRelated] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [retry, setRetry] = useState(0);
  const [imageIndex, setImageIndex] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");
  const [cartError, setCartError] = useState("");
  const loggedIn = useAtomValue(loginStatusAtom) === "loggedIn";

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setNotFound(false);
    setRelated([]);
    const id = Number(productId);
    if (!/^\d+$/.test(productId) || !Number.isSafeInteger(id) || id < 1) {
      setNotFound(true);
      setLoading(false);
      return () => controller.abort();
    }
    getProduct(id, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setProduct(result);
        // 関連商品の失敗で、商品詳細そのものを非表示にしない。
        void getProducts({ producerId: result.producer.id, page: 1, pageSize: 5 }, controller.signal)
          .then((list) => {
            if (!controller.signal.aborted) setRelated(list.items.filter((p) => p.producer.id === result.producer.id && p.id !== result.id).slice(0, 4));
          })
          .catch(() => {});
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && cause.status === 404) setNotFound(true);
        else setError(apiErrorMessage(cause, "商品を取得できませんでした。時間をおいて再度お試しください。"));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [productId, retry]);

  async function addToCart() {
    if (!product || adding || !loggedIn || !USE_MOCK || product.stock === 0) return;
    setAdding(true);
    setMessage("");
    setCartError("");
    try {
      await addCartItem(product.id, quantity);
      setMessage(`${product.name}を${quantity}点、デモカートに追加しました。`);
    } catch (cause) {
      setCartError(apiErrorMessage(cause, "カートに追加できませんでした。", "quantity"));
    } finally {
      setAdding(false);
    }
  }

  const linkClass = "text-marche-green no-underline hover:underline";
  if (loading || error || notFound || !product)
    return (
      <div className="mx-auto max-w-[1200px] px-5 py-12 sm:px-8">
        {loading ? (
          <p
            role="status"
            className="m-0"
          >
            商品を読み込んでいます…
          </p>
        ) : (
          <>
            <h1 className="m-0 font-serif text-2xl font-bold">{notFound ? "商品が見つかりません" : "商品を表示できません"}</h1>
            <p
              role={error ? "alert" : undefined}
              className="m-0 my-4 text-marche-muted"
            >
              {notFound ? "販売を終了したか、公開されていない商品です。" : error}
            </p>
            {error && (
              <Button
                onClick={() => setRetry((n) => n + 1)}
                className="mb-5"
              >
                再試行
              </Button>
            )}
            <div>
              <Link
                to="/products"
                className={["no-underline text-inherit", linkClass].join(" ")}
              >
                ← 商品一覧へ戻る
              </Link>
            </div>
          </>
        )}
      </div>
    );

  const images = [...product.images].sort((a, b) => a.sortOrder - b.sortOrder);
  const mainImage = images[imageIndex]?.url ?? product.thumbnailUrl;
  const maxQuantity = Math.min(10, product.stock ?? 10);
  const temperature = ({ normal: "常温", chilled: "冷蔵", frozen: "冷凍" } as Record<string, string>)[product.shipping.temperatureZone] ?? product.shipping.temperatureZone;

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-7 sm:px-8">
      <nav
        aria-label="パンくず"
        className="flex flex-wrap gap-2 text-xs text-marche-muted"
      >
        <Link
          to="/"
          className={["no-underline text-inherit", linkClass].join(" ")}
        >
          ホーム
        </Link>
        <span aria-hidden="true">/</span>
        <Link
          to="/products"
          className={["no-underline text-inherit", linkClass].join(" ")}
        >
          商品一覧
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>
      <div className="mt-6 grid gap-8 lg:grid-cols-2 lg:gap-12">
        <section
          aria-label="商品画像"
          className="min-w-0"
        >
          <ProductImage
            src={mainImage}
            alt={product.name}
            className="aspect-[4/3] rounded-2xl"
          />
          {images.length > 1 && (
            <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
              {images.map((img, index) => (
                <button
                  key={img.id}
                  type="button"
                  aria-label={`商品画像${index + 1}を表示`}
                  aria-pressed={imageIndex === index}
                  onClick={() => setImageIndex(index)}
                  className={["font-sans disabled:cursor-not-allowed", `w-20 shrink-0 cursor-pointer overflow-hidden rounded-lg border-2 bg-white p-0 ${imageIndex === index ? "border-marche-green" : "border-transparent"}`].join(" ")}
                >
                  <ProductImage
                    src={img.url}
                    alt=""
                    className="aspect-square"
                  />
                </button>
              ))}
            </div>
          )}
        </section>
        <section aria-label="商品情報">
          <Link
            to={`/products?category=${product.category.id}`}
            className={["no-underline text-inherit", `text-sm ${linkClass}`].join(" ")}
          >
            {product.category.name}
          </Link>
          <h1 className="m-0 mt-3 font-serif text-3xl font-bold leading-relaxed">{product.name}</h1>
          <p className="m-0 mt-3 text-sm text-marche-muted">
            {product.producer.prefectureName} {product.producer.city} ·{" "}
            <Link
              to={`/producers/${product.producer.id}`}
              className={["no-underline text-inherit", linkClass].join(" ")}
            >
              {product.producer.businessName}
            </Link>
          </p>
          <p className="m-0 mt-3 text-sm text-marche-muted">{product.ratingAvg === null ? "レビューはまだありません" : `★ ${product.ratingAvg.toFixed(1)}（${product.reviewCount}件）`}</p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-marche-green">
            {[product.isSubscription && "定期購入対応", product.isPreorder && "予約商品", product.acceptsDeliveryDate && "お届け日時指定OK"].filter(Boolean).map((tag) => (
              <span
                key={String(tag)}
                className="rounded-full bg-marche-sage px-3 py-1"
              >
                {tag}
              </span>
            ))}
          </div>
          <p className="m-0 mt-5 text-3xl font-bold">
            {yen(product.salePrice)} <span className="text-sm font-normal">税込</span>
          </p>
          {product.salePrice < product.price && (
            <p className="m-0 text-sm text-marche-muted">
              <del>{yen(product.price)}</del> <span className="text-orange-900">{product.discountRate}% OFF</span>
            </p>
          )}
          <p className="m-0 mt-1 text-sm text-marche-muted">内容量：{product.volume}</p>
          <div className="mt-5 rounded-xl bg-marche-sage p-4 text-sm">
            <p className="m-0">
              送料 {yen(product.shipping.shippingFee)}（{temperature}便）
            </p>
            <p className="m-0">{product.shipping.leadTimeText}</p>
            <p className="m-0 mt-1 text-xs text-marche-muted">送料はお届け先・注文内容により変わり、注文時に確定します。</p>
          </div>
          <p className={`m-0 mt-5 font-bold ${product.stock === 0 ? "text-red-800" : "text-marche-green"}`}>{product.stock === 0 ? "ただいま在庫切れです" : product.stock !== null && product.stock <= 5 ? `残りわずか（${product.stock}点）` : "在庫あり"}</p>
          {product.stock !== 0 && (
            <>
              <div className="mt-3 flex items-center gap-3">
                <label
                  htmlFor="product-quantity"
                  className="text-sm font-bold"
                >
                  数量
                </label>
                <select
                  id="product-quantity"
                  value={quantity}
                  disabled={adding}
                  onChange={(event) => {
                    setQuantity(Number(event.target.value));
                    setMessage("");
                    setCartError("");
                  }}
                  className="min-h-11 rounded-lg border border-marche-line bg-white px-4 py-2 font-sans text-base"
                >
                  {Array.from({ length: maxQuantity }, (_, index) => (
                    <option
                      key={index + 1}
                      value={index + 1}
                    >
                      {index + 1}
                    </option>
                  ))}
                </select>
                <span className="text-sm text-marche-muted">小計 {yen(product.salePrice * quantity)}</span>
              </div>
              {loggedIn ? (
                <Button
                  className="mt-4 w-full"
                  disabled={adding || !USE_MOCK}
                  onClick={() => void addToCart()}
                >
                  {adding ? "追加しています…" : "カートに追加"}
                </Button>
              ) : (
                <Link
                  to="/signin"
                  className="mt-4 flex min-h-12 items-center justify-center rounded-full bg-marche-green px-6 py-3 text-sm font-bold text-white no-underline hover:bg-marche-green-dark"
                >
                  ログインしてカートに追加
                </Link>
              )}
            </>
          )}
          <p className="m-0 mt-3 text-xs text-marche-muted">{USE_MOCK ? "商品情報・画像・カートは画面確認用デモです。実際の購入は行われません。" : "カート追加は認証・CSRF連携の接続確認後に利用できます。"}</p>
          {message && (
            <div
              role="status"
              className="mt-4 rounded-xl bg-marche-sage p-4"
            >
              <p className="m-0 text-sm">{message}</p>
              <Link
                to="/cart"
                className={["no-underline text-inherit", `mt-2 inline-block text-sm ${linkClass}`].join(" ")}
              >
                カートを見る →
              </Link>
            </div>
          )}
          {cartError && (
            <p
              role="alert"
              className="m-0 mt-4 text-sm text-red-800"
            >
              {cartError}
            </p>
          )}
        </section>
      </div>

      <div className="mt-12 grid gap-8 lg:grid-cols-[1.4fr_1fr] lg:gap-12">
        <div className="space-y-8">
          <section>
            <h2 className="m-0 font-serif text-xl font-bold">商品説明</h2>
            <p className="m-0 mt-3 whitespace-pre-line leading-8 text-marche-muted">{product.description}</p>
          </section>
          <section>
            <h2 className="m-0 font-serif text-xl font-bold">生産方法</h2>
            <p className="m-0 mt-3 whitespace-pre-line leading-8 text-marche-muted">{product.method || "生産方法の情報は掲載されていません。"}</p>
          </section>
          <section>
            <h2 className="m-0 font-serif text-xl font-bold">配送について</h2>
            <ul className="mb-0 mt-3 space-y-2 pl-5 text-sm text-marche-muted">
              <li>
                {product.producer.businessName}から直接発送します（{temperature}便）。
              </li>
              <li>{product.shipping.leadTimeText}</li>
              {product.shipping.freeShippingThreshold !== null && <li>同じ生産者の商品を{yen(product.shipping.freeShippingThreshold)}以上ご購入で送料無料。</li>}
              <li>他の生産者の商品とは別便でのお届けになります。</li>
            </ul>
          </section>
        </div>
        <aside className="self-start rounded-2xl border border-marche-line bg-white p-6">
          <p className="m-0 text-xs font-bold tracking-widest text-marche-green">この商品をつくった人</p>
          <h2 className="m-0 mt-3 font-serif text-2xl font-bold">{product.producer.businessName}</h2>
          <p className="m-0 mt-2 text-sm text-marche-muted">
            {product.producer.prefectureName} {product.producer.city}
          </p>
          <Link
            to={`/producers/${product.producer.id}`}
            className="mt-5 inline-flex min-h-11 items-center rounded-full bg-marche-green px-5 py-3 text-sm font-bold text-white no-underline hover:bg-marche-green-dark"
          >
            プロフィールを見る →
          </Link>
          <p className="m-0 mt-4 text-xs text-marche-muted">お気に入り登録・レビュー本文の表示は今後対応予定です。</p>
        </aside>
      </div>
      {related.length > 0 && (
        <section className="mt-12">
          <h2 className="m-0 mb-5 font-serif text-2xl font-bold">{product.producer.businessName}の他の商品</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {related.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
              />
            ))}
          </div>
        </section>
      )}
      <div className="mt-10">
        <Link
          to="/products"
          className={["no-underline text-inherit", linkClass].join(" ")}
        >
          ← 商品一覧へ戻る
        </Link>
      </div>
    </div>
  );
}
