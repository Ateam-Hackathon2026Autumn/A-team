import { Link } from "react-router";
import type { Product } from "../../types/product";

export const yen = (value: number) => `¥${value.toLocaleString("ja-JP")}`;

export function ProductImage({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  return (
    <div className={`relative overflow-hidden bg-marche-sage ${className}`}>
      <span className="absolute inset-0 flex items-center justify-center text-sm text-marche-muted">商品画像</span>
      {src && <img key={src} src={src} alt={alt} loading="lazy" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} className="relative block h-full w-full object-cover" />}
    </div>
  );
}

export default function ProductCard({ product }: { product: Product }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-marche-line bg-white">
      <Link to={`/products/${product.id}`} className="group block h-full text-marche-ink no-underline hover:bg-marche-sage/40">
        <div className="relative">
          <ProductImage src={product.thumbnailUrl} alt={product.name} className="aspect-[4/3]" />
          {product.stock === 0 && <span className="absolute left-3 top-3 rounded-full bg-marche-ink px-3 py-1 text-xs font-bold text-white">売り切れ</span>}
          {Boolean(product.discountRate) && <span className="absolute bottom-3 left-3 rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-900">{product.discountRate}% OFF</span>}
        </div>
        <div className="p-4">
          <p className="m-0 text-xs text-marche-muted">{product.producer.prefectureName} · {product.category.name}</p>
          <h2 className="font-serif m-0 mt-2 text-base font-bold leading-relaxed group-hover:underline">{product.name}</h2>
          <p className="m-0 mt-2 text-xs text-marche-muted">{product.producer.businessName}</p>
          <p className="m-0 mt-3 text-xl font-bold">{yen(product.salePrice)} <span className="text-xs font-normal">税込</span></p>
          <p className="m-0 text-xs text-marche-muted">{product.volume}</p>
          <p className="m-0 mt-2 text-xs text-marche-muted">{product.ratingAvg === null ? "レビューはまだありません" : `★ ${product.ratingAvg.toFixed(1)}（${product.reviewCount}件）`}</p>
        </div>
      </Link>
    </article>
  );
}
