import { useCallback, useState } from 'react';
import { Link } from 'react-router';

import {
  getFavoriteProducers,
  getFavoriteProducts,
  removeFavoriteProducer,
  removeFavoriteProduct,
} from '../api/favoriteApi';
import MyPageNavigation from '../components/mypage/MyPageNavigation';
import ProducerSummaryCard, { producerGenres } from '../components/producers/ProducerSummaryCard';
import ProductCard, { ProductImage, yen } from '../components/products/ProductCard';
import Button from '../components/ui/Button';
import {
  ContentImage,
  ContentPage,
  ContentStatus,
  EmptyContent,
  dateLabel,
  linkClass,
  panelClass,
} from '../components/ui/ContentPage';
import { usePublicContent } from '../hooks/usePublicContent';
import type { FavoriteProducerItem, FavoriteProductItem } from '../types/favorite';

export default function FavoritesPage() {
  const [kind, setKind] = useState<'products' | 'producers'>('products');
  const [page, setPage] = useState(1);
  const [removedProductIds, setRemovedProductIds] = useState<number[]>([]);
  const [removedProducerIds, setRemovedProducerIds] = useState<number[]>([]);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');

  const productLoader = useCallback(
    (signal: AbortSignal) => getFavoriteProducts({ page }, signal),
    [page],
  );
  const producerLoader = useCallback(
    (signal: AbortSignal) => getFavoriteProducers({ page }, signal),
    [page],
  );

  const productState = usePublicContent(productLoader);
  const producerState = usePublicContent(producerLoader);

  const activeState = kind === 'products' ? productState : producerState;
  const totalPages = activeState.data?.totalPages ?? 0;

  const switchKind = (next: 'products' | 'producers') => {
    if (next === kind) return;
    setKind(next);
    setPage(1);
    setActionError('');
  };

  const handleRemoveProduct = async (item: FavoriteProductItem) => {
    const key = `product-${item.product.id}`;
    if (removingId !== null) return;
    setRemovingId(key);
    setActionError('');
    try {
      await removeFavoriteProduct(item.product.id);
      setRemovedProductIds((prev) => [...prev, item.product.id]);
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : '商品のお気に入りを解除できませんでした。',
      );
    } finally {
      setRemovingId(null);
    }
  };

  const handleRemoveProducer = async (item: FavoriteProducerItem) => {
    const key = `producer-${item.producer.id}`;
    if (removingId !== null) return;
    setRemovingId(key);
    setActionError('');
    try {
      await removeFavoriteProducer(item.producer.id);
      setRemovedProducerIds((prev) => [...prev, item.producer.id]);
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : '生産者のお気に入りを解除できませんでした。',
      );
    } finally {
      setRemovingId(null);
    }
  };

  const productItems =
    productState.data?.items.filter((item) => !removedProductIds.includes(item.product.id)) ?? [];
  const producerItems =
    producerState.data?.items.filter((item) => !removedProducerIds.includes(item.producer.id)) ?? [];

  return (
    <ContentPage
      eyebrow="FAVORITES"
      title="お気に入り"
      intro="お気に入りの一品と、応援したいつくり手。"
    >
      <MyPageNavigation />
      <div
        role="group"
        aria-label="お気に入りの種類"
        className="mb-6 flex gap-3"
      >
        <Button
          variant={kind === 'products' ? 'primary' : 'outline'}
          aria-pressed={kind === 'products'}
          onClick={() => switchKind('products')}
        >
          商品
        </Button>
        <Button
          variant={kind === 'producers' ? 'primary' : 'outline'}
          aria-pressed={kind === 'producers'}
          onClick={() => switchKind('producers')}
        >
          生産者
        </Button>
      </div>

      {actionError && (
        <p role="alert" className="mb-4 text-sm font-bold text-marche-red">
          {actionError}
        </p>
      )}

      <ContentStatus {...activeState} />

      {kind === 'products' && productState.data && (
        productItems.length > 0 ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {productItems.map((item) => {
              const isRemoving = removingId === `product-${item.product.id}`;
              return (
                <div key={item.product.id} className="flex flex-col gap-2">
                  {item.isPublic ? (
                    <ProductCard product={item.product} />
                  ) : (
                    <article className={`${panelClass} flex-1 opacity-75`}>
                      <ProductImage
                        src={item.product.thumbnailUrl}
                        alt={item.product.name}
                        className="aspect-[4/3] rounded-xl"
                      />
                      <span className="mt-3 inline-block rounded-full bg-marche-canvas px-3 py-1 text-xs font-bold text-marche-muted">
                        現在非公開
                      </span>
                      <h2 className="mb-1 mt-2 font-serif text-lg">{item.product.name}</h2>
                      <p className="m-0 text-xs text-marche-muted">
                        {item.product.producer.businessName} · {yen(item.product.salePrice)}
                      </p>
                    </article>
                  )}
                  <div className="flex items-center justify-between px-1">
                    <span className="text-xs text-marche-muted">
                      登録日：{dateLabel(item.favoritedAt)}
                    </span>
                    <Button
                      variant="outline"
                      disabled={isRemoving}
                      onClick={() => void handleRemoveProduct(item)}
                      className="min-h-10 px-4 py-1.5 text-xs"
                    >
                      {isRemoving ? '解除中…' : 'お気に入り解除'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyContent>
            <h2 className="font-serif text-xl">お気に入りの商品はまだありません</h2>
            <p className="text-sm text-marche-muted">
              気になる商品を見つけたら、お気に入りに登録してここからいつでも確認できます。
            </p>
            <Link to="/products" className={linkClass}>
              商品を探す
            </Link>
          </EmptyContent>
        )
      )}

      {kind === 'producers' && producerState.data && (
        producerItems.length > 0 ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {producerItems.map((item) => {
              const isRemoving = removingId === `producer-${item.producer.id}`;
              return (
                <div key={item.producer.id} className="flex flex-col gap-2">
                  {item.isPublic ? (
                    <ProducerSummaryCard producer={item.producer} />
                  ) : (
                    <article className={`${panelClass} flex-1 opacity-75`}>
                      <ContentImage
                        src={item.producer.coverImageUrl ?? item.producer.profileImageUrl}
                        alt={item.producer.businessName}
                        className="aspect-[16/9] rounded-xl"
                      />
                      <span className="mt-3 inline-block rounded-full bg-marche-canvas px-3 py-1 text-xs font-bold text-marche-muted">
                        現在非公開
                      </span>
                      <h2 className="mb-1 mt-2 font-serif text-lg">{item.producer.businessName}</h2>
                      <p className="m-0 text-xs text-marche-muted">
                        {item.producer.prefectureName} {item.producer.city} ·{' '}
                        {producerGenres[item.producer.genre] ?? item.producer.genre}
                      </p>
                    </article>
                  )}
                  <div className="flex items-center justify-between px-1">
                    <span className="text-xs text-marche-muted">
                      登録日：{dateLabel(item.favoritedAt)}
                    </span>
                    <Button
                      variant="outline"
                      disabled={isRemoving}
                      onClick={() => void handleRemoveProducer(item)}
                      className="min-h-10 px-4 py-1.5 text-xs"
                    >
                      {isRemoving ? '解除中…' : 'お気に入り解除'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyContent>
            <h2 className="font-serif text-xl">お気に入りの生産者はまだありません</h2>
            <p className="text-sm text-marche-muted">
              応援したい生産者をお気に入り（フォロー）に登録すると、ここに一覧表示されます。
            </p>
            <Link to="/producers" className={linkClass}>
              生産者を探す
            </Link>
          </EmptyContent>
        )
      )}

      {totalPages > 1 && (
        <nav
          aria-label="お気に入りのページ移動"
          className="mt-6 flex items-center justify-center gap-4"
        >
          <Button
            variant="outline"
            disabled={activeState.loading || page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            前へ
          </Button>
          <span className="text-sm">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            disabled={activeState.loading || page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            次へ
          </Button>
        </nav>
      )}
    </ContentPage>
  );
}
