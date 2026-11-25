import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useAtomValue } from 'jotai';

import ApiError from '../../api/apiError';
import {
  createProduct,
  getCategories,
  getShippingSettings,
} from '../../api/dashboardProductApi';
import DashboardButton from '../../components/DashboardButton';
import DashboardProductForm from '../../components/DashboardProductForm';
import { userInfoAtom } from '../../stores/userAtom';
import type { Category, ProductCreateInput, ShippingSetting } from '../../types/product';

const PRODUCT_LIST_PATH = '/dashboard/products';

type Choices = {
  categories: Category[];
  shippingSettings: ShippingSetting[];
};

function DashboardProductNewPage() {
  const navigate = useNavigate();
  const userInfo = useAtomValue(userInfoAtom);
  // 審査中は管理画面に入れるが、商品のAPIは承認済みの生産者のみ使える
  const canManageProducts = userInfo?.isProducer === true;

  // カテゴリーと配送方法の選択肢
  const [choices, setChoices] = useState<Choices | null>(null);
  const [hasLoadError, setHasLoadError] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    if (!canManageProducts) {
      return;
    }

    let isActive = true;

    async function fetchChoices() {
      try {
        const [categories, shippingSettings] = await Promise.all([
          getCategories(),
          getShippingSettings(),
        ]);

        if (isActive) {
          setChoices({ categories, shippingSettings });
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setHasLoadError(true);
        }
      }
    }

    fetchChoices();

    return () => {
      isActive = false;
    };
  }, [canManageProducts, reloadCount]);

  const handleReload = () => {
    setHasLoadError(false);
    setReloadCount((count) => count + 1);
  };

  const handleSubmit = async (input: ProductCreateInput) => {
    await createProduct(input);

    const statusLabel = input.publishStatus === 'public' ? '公開' : '下書き保存';
    navigate(PRODUCT_LIST_PATH, {
      state: { flash: `「${input.name}」を${statusLabel}しました。` },
    });
  };

  const renderBody = () => {
    if (!canManageProducts) {
      return (
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          商品の登録・管理は、生産者登録が承認されると使えるようになります。
        </p>
      );
    }

    if (hasLoadError) {
      return (
        <div
          role="alert"
          className="box-border rounded-2xl border border-solid border-marche-red/30 bg-white p-5 text-sm"
        >
          <p className="m-0 font-bold text-marche-red">
            入力に必要な情報を読み込めませんでした。
          </p>
          <p className="m-0 mt-1 text-marche-muted">
            時間をおいて、もう一度お試しください。
          </p>
          <DashboardButton variant="secondary" onClick={handleReload} className="mt-4">
            再読み込み
          </DashboardButton>
        </div>
      );
    }

    if (choices === null) {
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

    // 配送方法がないと登録できない（配送設定は必須項目）
    if (choices.shippingSettings.length === 0) {
      return (
        <p className="m-0 box-border rounded-2xl border border-solid border-marche-line bg-white p-5 text-sm">
          商品を登録する前に、配送設定（送料・発送目安）の登録が必要です。
        </p>
      );
    }

    return (
      <DashboardProductForm
        categories={choices.categories}
        shippingSettings={choices.shippingSettings}
        onSubmit={handleSubmit}
        cancelTo={PRODUCT_LIST_PATH}
      />
    );
  };

  return (
    <div className="mx-auto max-w-3xl flex flex-col gap-6">
      <header>
        <Link
          to={PRODUCT_LIST_PATH}
          className="text-sm font-bold text-marche-green no-underline hover:underline"
        >
          ← 商品管理に戻る
        </Link>
        <h1 className="m-0 font-serif mt-2 text-2xl font-bold">商品登録</h1>
      </header>

      {renderBody()}
    </div>
  );
}

export default DashboardProductNewPage;
