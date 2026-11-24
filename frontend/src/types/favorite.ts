import type { ProducerSummary } from './producer';
import type { Product } from './publicProduct';

export type FavoriteType = 'product' | 'producer';

export type FavoriteProductItem = {
  product: Product;
  isPublic: boolean;
  favoritedAt: string;
};

export type FavoriteProducerItem = {
  producer: ProducerSummary;
  isPublic: boolean;
  notify: boolean;
  favoritedAt: string;
};
