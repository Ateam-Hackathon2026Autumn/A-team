import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import {
  deleteProduct,
  getCategories,
  getDashboardProducts,
  updateProductPublishStatus,
  updateProductStock,
} from '../../api/dashboardProductApi';
import DashboardButton from '../../components/DashboardButton';
import { PlusIcon } from '../../components/DashboardIcons';
import DashboardProductRow from '../../components/DashboardProductRow';
import { userInfoAtom } from '../../stores/userAtom';
import type { Category, DashboardProduct } from '../../types/product';

const NEW_PRODUCT_PATH = '/dashboard/products/new';

function ProductRowSkeleton() {
  return (
    <li className="box-border flex animate-pulse items-center gap-4 rounded-2xl border border-solid border-marche-line bg-white p-4">
      <div className="size-16 shrink-0 rounded-xl bg-marche-canvas" />
      <div className="flex-1 flex flex-col gap-2">
        <div className="h-4 w-48 max-w-full rounded bg-marche-canvas" />
        <div className="h-3 w-24 rounded bg-marche-canvas" />
      </div>
    </li>
  );
}

function DashboardProductListPage() {
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、商品のAPIは承認済みの生産者のみ使える
  const canManageProducts = userInfo?.isProducer === true;

  const location = useLocation();
  const navigate = useNavigate();
  // 登録画面などから戻ってきたときのお知らせ（例: 「〇〇」を公開しました。）
  const [flash] = useState<string | null>(
    (location.state as { flash?: string } | null)?.flash ?? null,
  );

  // 再読み込みでお知らせが再表示されないよう、履歴の state を消す
  useEffect(() => {
    if (location.state !== null) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  const [products, setProducts] = useState<DashboardProduct[] | null>(null);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<Category[]>([]);
  const [hasLoadError, setHasLoadError] = useState(false);
  // 再読み込みのときに値を変えて、一覧を取り直す
  const [reloadCount, setReloadCount] = useState(0);
  // 通信中の商品ID
  const [pendingIds, setPendingIds] = useState<ReadonlySet<number>>(new Set());
  // 在庫変更・公開切り替え・削除の失敗メッセージ
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!canManageProducts) {
      return;
    }

    // 画面を離れた後に結果が返ってきても state を更新しない
    let isActive = true;

    async function fetchProducts() {
      try {
        const data = await getDashboardProducts(page);

        if (!isActive) {
          return;
        }

        // 削除などで今のページが総ページ数を超えた（空になった）ら、最後のページへ戻る
        if (data.items.length === 0 && page > 1 && page > data.totalPages) {
          setProducts(null);
          setPage(Math.max(1, data.totalPages));
          return;
        }

        setProducts(data.items);
        setTotal(data.total);
        setTotalPages(data.totalPages);
      } catch (error) {
        // セッション切れ。ログイン状態を確認し直すため再読み込みする
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setHasLoadError(true);
        }
      }
    }

    fetchProducts();

    return () => {
      isActive = false;
    };
  }, [canManageProducts, page, reloadCount]);

  useEffect(() => {
    if (!canManageProducts) {
      return;
    }

    let isActive = true;

    // カテゴリー名は補足情報のため、取得できなくても一覧は表示する
    getCategories()
      .then((items) => {
        if (isActive) {
          setCategories(items);
        }
      })
      .catch(() => {});

    return () => {
      isActive = false;
    };
  }, [canManageProducts]);

  const reloadProducts = () => {
    setHasLoadError(false);
    setProducts(null);
    setReloadCount((count) => count + 1);
  };

  const changePage = (nextPage: number) => {
    setActionError(null);
    setProducts(null);
    setPage(nextPage);
  };

  // 商品ごとの更新処理の共通部分（通信中の管理とエラーの表示）
  const runProductAction = async (
    productId: number,
    action: () => Promise<void>,
  ) => {
    setActionError(null);
    setPendingIds((ids) => new Set(ids).add(productId));

    try {
      await action();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (error instanceof ApiError && error.status === 412) {
        setActionError(
          '他の画面で商品が更新されていたため、最新の内容を読み込み直しました。もう一度操作してください。',
        );
        reloadProducts();
      } else if (error instanceof ApiError) {
        setActionError(error.message);
      } else {
        setActionError(
          '通信に失敗しました。時間をおいて、もう一度お試しください。',
        );
      }
    } finally {
      setPendingIds((ids) => {
        const nextIds = new Set(ids);
        nextIds.delete(productId);

        return nextIds;
      });
    }
  };

  const applyProductChange = (
    productId: number,
    change: Partial<DashboardProduct>,
  ) => {
    setProducts(
      (current) =>
        current?.map((product) =>
          product.id === productId ? { ...product, ...change } : product,
        ) ?? null,
    );
  };

  const handleStockChange = (product: DashboardProduct, stock: number) => {
    runProductAction(product.id, async () => {
      const { etag, updatedAt } = await updateProductStock(
        product.id,
        stock,
        product.etag,
      );

      applyProductChange(product.id, { stock, etag, updatedAt });
    });
  };

  const handlePublishToggle = (product: DashboardProduct) => {
    const publishStatus =
      product.publishStatus === 'public' ? 'private' : 'public';

    runProductAction(product.id, async () => {
      const { etag, updatedAt } = await updateProductPublishStatus(
        product.id,
        publishStatus,
        product.etag,
      );

      applyProductChange(product.id, { publishStatus, etag, updatedAt });
    });
  };

  const handleDelete = (product: DashboardProduct) => {
    if (
      !window.confirm(
        `「${product.name}」を削除します。元に戻せません。よろしいですか？`,
      )
    ) {
      return;
    }

    runProductAction(product.id, async () => {
      await deleteProduct(product.id, product.etag);

      // 取り直すまでの間も削除した商品が残らないよう、先に一覧から外す
      setProducts((current) =>
        current === null
          ? null
          : current.filter(({ id }) => id !== product.id),
      );
      // 総件数・総ページ数・今のページの商品を合わせるため一覧を取り直す
      // （今のページが空になった場合は、取得結果を見て最後のページへ戻る）
      setReloadCount((count) => count + 1);
    });
  };

  const categoryNames = new Map(categories.map(({ id, name }) => [id, name]));

  if (!canManageProducts) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="m-0 font-serif text-2xl font-bold">商品管理</h1>
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          商品の登録・管理は、生産者登録が承認されると使えるようになります。
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="m-0 font-serif text-2xl font-bold">
          商品管理
          {products !== null && (
            <span className="ml-2 text-sm font-normal text-marche-muted">
              {total}件
            </span>
          )}
        </h1>
        <DashboardButton to={NEW_PRODUCT_PATH}>
          <PlusIcon className="size-4" />
          商品を登録
        </DashboardButton>
      </header>

      {flash !== null && (
        <p
          role="status"
          className="m-0 box-border rounded-2xl border border-solid border-marche-green/30 bg-marche-sage p-4 text-sm font-bold text-marche-green"
        >
          {flash}
        </p>
      )}

      {actionError !== null && (
        <p
          role="alert"
          className="m-0 box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-4 text-sm font-bold text-marche-red"
        >
          {actionError}
        </p>
      )}

      {hasLoadError ? (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">
            商品一覧を読み込めませんでした。
          </p>
          <p className="m-0 mt-1 text-marche-muted">
            時間をおいて、もう一度お試しください。
          </p>
          <DashboardButton
            variant="secondary"
            onClick={reloadProducts}
            className="mt-4"
          >
            再読み込み
          </DashboardButton>
        </div>
      ) : products === null ? (
        <ul aria-busy="true" className="m-0 list-none flex flex-col gap-3 p-0">
          {Array.from({ length: 3 }, (_, i) => (
            <ProductRowSkeleton key={i} />
          ))}
        </ul>
      ) : products.length === 0 ? (
        <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-8 text-center">
          <p className="m-0 font-bold">まだ商品がありません</p>
          <p className="m-0 mt-1 text-sm text-marche-muted">
            最初の商品を登録しましょう。
          </p>
          <DashboardButton to={NEW_PRODUCT_PATH} className="mt-4">
            <PlusIcon className="size-4" />
            商品を登録
          </DashboardButton>
        </div>
      ) : (
        <ul className="m-0 list-none flex flex-col gap-3 p-0">
          {products.map((product) => (
            <DashboardProductRow
              key={product.id}
              product={product}
              categoryName={categoryNames.get(product.categoryId)}
              isPending={pendingIds.has(product.id)}
              onStockChange={handleStockChange}
              onPublishToggle={handlePublishToggle}
              onDelete={handleDelete}
            />
          ))}
        </ul>
      )}

      {!hasLoadError && products !== null && totalPages > 1 && (
        <nav
          aria-label="ページ移動"
          className="flex items-center justify-center gap-4"
        >
          <DashboardButton
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => changePage(page - 1)}
          >
            前へ
          </DashboardButton>
          <span className="text-sm text-marche-muted">
            {page} / {totalPages}
          </span>
          <DashboardButton
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => changePage(page + 1)}
          >
            次へ
          </DashboardButton>
        </nav>
      )}
    </div>
  );
}

export default DashboardProductListPage;
