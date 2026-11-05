import { useEffect, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import {
  getCategories,
  getDashboardProduct,
  getShippingSettings,
  updateProduct,
  updateProductStock,
} from '../../api/dashboardProductApi';
import DashboardButton from '../../components/DashboardButton';
import DashboardProductForm from '../../components/DashboardProductForm';
import { userInfoAtom } from '../../stores/userAtom';
import type {
  Category,
  DashboardProduct,
  ProductCreateInput,
  ShippingSetting,
} from '../../types/product';

const PRODUCT_LIST_PATH = '/dashboard/products';

// 他の画面で先に更新されていた（412）ときの案内
const STALE_MESSAGE =
  '他の画面で商品が更新されていたため、最新の内容を読み込み直しました。もう一度編集して保存してください。';

type EditData = {
  product: DashboardProduct;
  categories: Category[];
  shippingSettings: ShippingSetting[];
};

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
      {children}
    </div>
  );
}

function DashboardProductEditPage() {
  const navigate = useNavigate();
  const { productId: productIdParam } = useParams();
  const productId = Number(productIdParam);
  const isValidId = Number.isInteger(productId) && productId > 0;

  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、商品のAPIは承認済みの生産者のみ使える
  const canManageProducts = userInfo?.isProducer === true;

  const [data, setData] = useState<EditData | null>(null);
  const [loadError, setLoadError] = useState<'notFound' | 'failed' | null>(
    null,
  );
  // 412 で読み込み直したときなどのお知らせ
  const [notice, setNotice] = useState<string | null>(null);
  // 読み込み直すたびに増やす（フォームも作り直して最新の内容にする）
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    if (!canManageProducts || !isValidId) {
      return;
    }

    let isActive = true;

    async function fetchData() {
      try {
        const [product, categories, shippingSettings] = await Promise.all([
          getDashboardProduct(productId),
          getCategories(),
          getShippingSettings(),
        ]);

        if (isActive) {
          setData({ product, categories, shippingSettings });
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setLoadError(
            error instanceof ApiError && error.status === 404
              ? 'notFound'
              : 'failed',
          );
        }
      }
    }

    fetchData();

    return () => {
      isActive = false;
    };
  }, [canManageProducts, isValidId, productId, reloadCount]);

  const reload = () => {
    setLoadError(null);
    setData(null);
    setReloadCount((count) => count + 1);
  };

  const handleSubmit = async (input: ProductCreateInput) => {
    if (data === null) {
      return;
    }

    const { product } = data;
    const { stock, ...fields } = input;
    const stockChanged = stock !== product.stock;
    // 在庫と内容（価格・公開状態など）は別々のAPIで保存するため、途中で失敗しても
    // 「旧価格のまま在庫だけ補充されて販売できる」状態にならない順で更新する
    // - 原則は内容が先（価格を変えてから在庫を補充する）
    // - 在庫が未設定（null）の商品は公開できないため、そのときだけ在庫を先に設定する
    //   （未設定の商品は公開中ではないので、在庫を先に入れても販売は始まらない）
    const updateStockFirst = stockChanged && product.stock === null;
    // 1つ目の更新が成功したか（2つ目で失敗したときに一部だけ保存されたことを伝える）
    let firstSaved = false;

    setNotice(null);

    try {
      if (updateStockFirst) {
        const { etag } = await updateProductStock(product.id, stock, product.etag);
        firstSaved = true;
        await updateProduct(product.id, fields, etag);
      } else {
        const updated = await updateProduct(product.id, fields, product.etag);
        firstSaved = true;

        if (stockChanged) {
          await updateProductStock(product.id, stock, updated.etag);
        }
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return;
      }

      if (firstSaved) {
        // 一部だけ保存された。保存済みの内容を読み込み直して画面と一致させる
        const failedPart = updateStockFirst ? '商品の内容' : '在庫数';
        const savedPart = updateStockFirst ? '在庫数' : '商品の内容';
        const reason =
          error instanceof ApiError && error.status !== 412
            ? `（${error.message}）`
            : '';

        setNotice(
          `${savedPart}は保存しましたが、${failedPart}は保存できませんでした${reason}。保存済みの内容を読み込み直したので、${failedPart}を確認してもう一度保存してください。`,
        );
        reload();
        window.scrollTo({ top: 0 });
        return;
      }

      if (error instanceof ApiError && error.status === 412) {
        setNotice(STALE_MESSAGE);
        reload();
        window.scrollTo({ top: 0 });
        return;
      }

      throw error;
    }

    navigate(PRODUCT_LIST_PATH, {
      state: { flash: `「${fields.name}」を保存しました。` },
    });
  };

  const renderBody = () => {
    if (!canManageProducts) {
      return (
        <Notice>
          商品の登録・管理は、生産者登録が承認されると使えるようになります。
        </Notice>
      );
    }

    if (!isValidId || loadError === 'notFound') {
      return (
        <Notice>
          <p className="m-0 font-bold">商品が見つかりません。</p>
          <p className="m-0 mt-1 text-marche-muted">
            削除されたか、URL が間違っている可能性があります。
          </p>
          <DashboardButton to={PRODUCT_LIST_PATH} variant="secondary" className="mt-4">
            商品管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    if (loadError === 'failed') {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">
            商品を読み込めませんでした。
          </p>
          <p className="m-0 mt-1 text-marche-muted">
            時間をおいて、もう一度お試しください。
          </p>
          <DashboardButton variant="secondary" onClick={reload} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (data === null) {
      return (
        <div aria-busy="true" className="flex flex-col gap-6">
          {Array.from({ length: 3 }, (_, i) => (
            <div
              key={i}
              className="box-border h-48 animate-pulse rounded-2xl border border-solid border-marche-line bg-white"
            />
          ))}
        </div>
      );
    }

    // 運営による掲載停止中は、生産者は変更できない
    if (data.product.publishStatus === 'suspended') {
      return (
        <Notice>
          <p className="m-0 font-bold">
            この商品は運営により掲載停止中のため、編集できません。
          </p>
          <p className="m-0 mt-1 text-marche-muted">
            くわしくは運営にお問い合わせください。
          </p>
          <DashboardButton to={PRODUCT_LIST_PATH} variant="secondary" className="mt-4">
            商品管理に戻る
          </DashboardButton>
        </Notice>
      );
    }

    return (
      <DashboardProductForm
        key={reloadCount}
        product={data.product}
        categories={data.categories}
        shippingSettings={data.shippingSettings}
        onSubmit={handleSubmit}
        cancelTo={PRODUCT_LIST_PATH}
      />
    );
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <header>
        <Link
          to={PRODUCT_LIST_PATH}
          className="text-sm font-bold text-marche-green no-underline hover:underline"
        >
          ← 商品管理に戻る
        </Link>
        <h1 className="m-0 mt-2 text-2xl font-bold">商品編集</h1>
      </header>

      {notice !== null && (
        <div
          role="status"
          className="box-border rounded-2xl border border-solid border-marche-orange/40 bg-marche-orange/15 p-4 text-sm font-bold"
        >
          {notice}
        </div>
      )}

      {renderBody()}
    </div>
  );
}

export default DashboardProductEditPage;
