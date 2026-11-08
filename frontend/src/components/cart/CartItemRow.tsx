import { Link } from "react-router";
import { ProductImage, yen } from "../products/ProductCard";
import { USE_MOCK } from "../../config/env";
import type { CartItem } from "../../types/cart";
import type { ProductDetail } from "../../types/publicProduct";

type Props = {
  item: CartItem;
  product?: ProductDetail;
  busy: boolean;
  onQuantityChange: (quantity: number) => void;
  onRemove: () => void;
};

export default function CartItemRow({
  item,
  product,
  busy,
  onQuantityChange,
  onRemove,
}: Props) {
  const name = item.productName ?? "販売を終了した商品";
  const unavailable = item.unavailableReason === "PRODUCT_UNAVAILABLE";
  const disabled = busy || !USE_MOCK;
  // nullは在庫管理なしとして10点まで。詳細未取得とは区別する。
  const maxQuantity = product ? Math.min(10, product.stock ?? 10) : 0;
  const quantityDisabled = disabled || unavailable || !product || maxQuantity < 1;
  const currentOutOfRange = item.quantity > maxQuantity;
  const quantityButton =
    "grid size-10 shrink-0 cursor-pointer place-items-center border-0 bg-transparent font-sans text-lg text-marche-ink disabled:cursor-not-allowed disabled:text-gray-400";

  return (
    <li className="flex flex-wrap items-start gap-4 py-5 sm:flex-nowrap">
      <Link
        to={`/products/${item.productId}`}
        aria-label={`${name}の商品詳細`}
        className="block w-20 shrink-0 no-underline sm:w-24"
      >
        <ProductImage
          src={product?.thumbnailUrl ?? null}
          alt=""
          className="aspect-square rounded-xl"
        />
      </Link>
      <div className="min-w-0 flex-1">
        <Link
          to={`/products/${item.productId}`}
          className="text-sm font-bold leading-relaxed text-marche-ink no-underline hover:underline"
        >
          {name}
        </Link>
        <p className="m-0 mt-1 text-xs text-marche-muted">
          {item.unitPrice === null ? "価格を取得できません" : `${yen(item.unitPrice)}（税込）`}
          {product?.volume ? ` · ${product.volume}` : ""}
        </p>
        {!item.purchasable && (
          <p className="m-0 mt-2 text-xs font-bold text-red-800">
            {unavailable
              ? "現在購入できません。カートから削除してください。"
              : product?.stock === 0
                ? "在庫がありません。カートから削除してください。"
                : "在庫不足などにより購入できません。数量を変更するか削除してください。"}
          </p>
        )}
        {!product && (
          <p className="m-0 mt-2 text-xs text-marche-muted">
            在庫情報を取得できないため数量変更を停止しています。
          </p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="inline-flex items-center rounded-full border border-marche-line bg-white">
            <button
              type="button"
              aria-label={`${name}の数量を減らす`}
              disabled={quantityDisabled || item.quantity <= 1}
              onClick={() => onQuantityChange(Math.min(item.quantity - 1, maxQuantity))}
              className={quantityButton}
            >
              −
            </button>
            <label className="sr-only" htmlFor={`cart-quantity-${item.id}`}>
              {name}の数量
            </label>
            <select
              id={`cart-quantity-${item.id}`}
              value={item.quantity}
              disabled={quantityDisabled}
              onChange={(event) => onQuantityChange(Number(event.target.value))}
              className="min-h-10 cursor-pointer rounded-lg border-0 bg-transparent px-1 font-sans text-sm font-bold text-marche-ink disabled:cursor-not-allowed"
            >
              {currentOutOfRange && (
                <option value={item.quantity} disabled>
                  {item.quantity}点（{product ? "在庫超過" : "在庫未確認"}）
                </option>
              )}
              {Array.from({ length: maxQuantity }, (_, index) => (
                <option key={index + 1} value={index + 1}>
                  {index + 1}
                </option>
              ))}
            </select>
            <button
              type="button"
              aria-label={`${name}の数量を増やす`}
              disabled={quantityDisabled || item.quantity >= maxQuantity}
              onClick={() => onQuantityChange(item.quantity + 1)}
              className={quantityButton}
            >
              ＋
            </button>
          </div>
          <button
            type="button"
            disabled={disabled}
            aria-label={`${name}をカートから削除`}
            onClick={onRemove}
            className="min-h-11 cursor-pointer border-0 bg-transparent px-2 font-sans text-xs text-red-800 underline disabled:cursor-not-allowed disabled:text-gray-400"
          >
            削除
          </button>
        </div>
      </div>
      <p className="m-0 ml-auto shrink-0 text-right text-base font-bold">
        {item.subtotal === null ? "金額未確定" : yen(item.subtotal)}
        <span className="block text-xs font-normal text-marche-muted">商品小計</span>
      </p>
    </li>
  );
}