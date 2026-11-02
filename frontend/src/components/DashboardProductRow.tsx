import { useState, type KeyboardEvent } from 'react';

import type { DashboardProduct } from '../types/product';
import DashboardButton from './DashboardButton';
import { MinusIcon, PlusIcon, ProductIcon } from './DashboardIcons';

// 在庫数の上限（API の仕様）
const MAX_STOCK = 2147483647;

// この数以下で「在庫わずか」を表示する
const LOW_STOCK_THRESHOLD = 5;

const yenFormatter = new Intl.NumberFormat('ja-JP');

function formatYen(amount: number) {
  return `¥${yenFormatter.format(amount)}`;
}

function publishLabel(product: DashboardProduct) {
  switch (product.publishStatus) {
    case 'public':
      return '公開中';
    case 'private':
      return '非公開';
    case 'draft':
      return '下書き';
    case 'suspended':
      return '掲載停止中';
  }
}

function StockBadge({ stock }: { stock: number | null }) {
  const className =
    'inline-block rounded-full px-2.5 py-0.5 text-xs font-bold';

  if (stock === null) {
    return (
      <span className={`${className} bg-marche-canvas text-marche-muted`}>
        在庫未設定
      </span>
    );
  }

  if (stock === 0) {
    return (
      <span className={`${className} bg-marche-red text-white`}>売り切れ</span>
    );
  }

  if (stock <= LOW_STOCK_THRESHOLD) {
    return (
      <span className={`${className} bg-marche-red/10 text-marche-red`}>
        在庫わずか
      </span>
    );
  }

  return null;
}

type DashboardProductRowProps = {
  product: DashboardProduct;
  categoryName: string | undefined;
  // 通信中はこの行の操作を止める（古い etag での二重送信を防ぐ）
  isPending: boolean;
  onStockChange: (product: DashboardProduct, stock: number) => void;
  onPublishToggle: (product: DashboardProduct) => void;
  onDelete: (product: DashboardProduct) => void;
};

// 商品管理画面の1行（在庫の増減・公開切り替え・編集・削除）
function DashboardProductRow({
  product,
  categoryName,
  isPending,
  onStockChange,
  onPublishToggle,
  onDelete,
}: DashboardProductRowProps) {
  const { id, name, volume, stock, publishStatus, images } = product;

  // 在庫数の入力中の値（入力していないときは null）
  const [stockDraft, setStockDraft] = useState<string | null>(null);

  const isSuspended = publishStatus === 'suspended';
  const isPublic = publishStatus === 'public';
  const isStockLocked = isPending || isSuspended;
  // 公開中は先に非公開へ変更してから削除する。掲載停止中は運営の対応が必要
  const canDelete = !isPublic && !isSuspended;

  const commitStockDraft = () => {
    if (stockDraft === null) {
      return;
    }

    setStockDraft(null);

    // 数字以外・空欄・上限超えは元の値に戻す（公開中の商品は未設定にできないため空欄を送らない）
    if (!/^\d+$/.test(stockDraft)) {
      return;
    }

    const nextStock = Number(stockDraft);

    if (nextStock <= MAX_STOCK && nextStock !== stock) {
      onStockChange(product, nextStock);
    }
  };

  const handleStockKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.currentTarget.blur();
    }

    if (event.key === 'Escape') {
      setStockDraft(null);
    }
  };

  const stepButtonClassName =
    'box-border grid size-9 cursor-pointer place-items-center rounded-full border border-solid border-marche-line bg-white p-0 text-marche-green transition-colors hover:bg-marche-canvas disabled:pointer-events-none disabled:opacity-40';

  return (
    <li className="box-border flex flex-wrap items-center gap-x-5 gap-y-3 rounded-2xl border border-solid border-marche-line bg-white p-4">
      <div
        className={`flex min-w-0 flex-1 basis-64 items-center gap-4 ${isPublic ? '' : 'opacity-70'}`}
      >
        {images.length > 0 ? (
          <img
            src={images[0].url}
            alt=""
            loading="lazy"
            className="size-16 shrink-0 rounded-xl bg-marche-sage object-cover"
          />
        ) : (
          <span className="grid size-16 shrink-0 place-items-center rounded-xl bg-marche-sage text-marche-muted">
            <ProductIcon />
          </span>
        )}

        <div className="min-w-0">
          <p className="m-0 truncate font-bold">
            {name} {volume}
          </p>
          <p className="m-0 text-sm text-marche-muted">
            {product.discountRate !== null && (
              <s className="mr-1 text-xs">{formatYen(product.price)}</s>
            )}
            {formatYen(product.salePrice)}
            {categoryName !== undefined && ` ・ ${categoryName}`}
          </p>
          <div className="mt-1 empty:hidden">
            <StockBadge stock={stock} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="flex items-center gap-2">
          <span id={`stock-label-${id}`} className="text-xs text-marche-muted">
            在庫
          </span>
          <button
            type="button"
            aria-label={`${name}の在庫を1減らす`}
            disabled={isStockLocked || stock === null || stock === 0}
            onClick={() => onStockChange(product, (stock ?? 0) - 1)}
            className={stepButtonClassName}
          >
            <MinusIcon className="size-4" />
          </button>
          <input
            type="text"
            inputMode="numeric"
            aria-labelledby={`stock-label-${id}`}
            placeholder="-"
            disabled={isStockLocked}
            value={stockDraft ?? stock ?? ''}
            onChange={(event) => setStockDraft(event.target.value)}
            onBlur={commitStockDraft}
            onKeyDown={handleStockKeyDown}
            className="box-border w-14 rounded-lg border border-solid border-marche-line bg-white py-1.5 text-center text-base font-bold text-marche-ink [font-family:inherit] disabled:opacity-60"
          />
          <button
            type="button"
            aria-label={`${name}の在庫を1増やす`}
            disabled={isStockLocked || stock === MAX_STOCK}
            onClick={() => onStockChange(product, (stock ?? 0) + 1)}
            className={stepButtonClassName}
          >
            <PlusIcon className="size-4" />
          </button>
        </div>

        {isSuspended ? (
          <span className="rounded-full bg-marche-red/10 px-3 py-1 text-xs font-bold text-marche-red">
            {publishLabel(product)}
          </span>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              role="switch"
              aria-checked={isPublic}
              aria-label={`${name}を公開する`}
              disabled={isPending}
              onClick={() => onPublishToggle(product)}
              className={`relative box-border h-7 w-12 shrink-0 cursor-pointer rounded-full border-0 p-0 transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${isPublic ? 'bg-marche-green' : 'bg-marche-line'}`}
            >
              <span
                className={`absolute top-0.5 left-0.5 size-6 rounded-full bg-white shadow transition-transform ${isPublic ? 'translate-x-5' : ''}`}
              />
            </button>
            <span className="w-12 text-xs font-bold">
              {publishLabel(product)}
            </span>
          </div>
        )}

        {/* 削除ボタンの有無で在庫・公開の位置がずれないよう、PC では幅を固定する */}
        <div className="flex items-center gap-2 md:w-28 md:justify-end">
          {!isSuspended && (
            <DashboardButton
              to={`/dashboard/products/${id}/edit`}
              variant="secondary"
              size="sm"
            >
              編集
            </DashboardButton>
          )}
          {canDelete && (
            <DashboardButton
              variant="danger"
              size="sm"
              disabled={isPending}
              onClick={() => onDelete(product)}
            >
              削除
            </DashboardButton>
          )}
        </div>
      </div>
    </li>
  );
}

export default DashboardProductRow;
