import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { getCategories, getProducts } from "../api/productApi";
import ProductCard from "../components/products/ProductCard";
import Button from "../components/ui/Button";
import type { Category, Product } from "../types/product";

const fieldClass = "min-h-11 w-full rounded-lg border border-marche-line bg-white px-3 py-2 font-sans text-sm text-marche-ink";
const pageSize = 9;

export default function ProductListPage() {
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const q = params.get("q") ?? "";
  const [keywordInput, setKeywordInput] = useState(q);
  const composing = useRef(false);
  const category = params.get("category") ?? "";
  const price = params.get("price") ?? "all";
  const sort = params.get("sort") ?? "popular";
  const subscription = params.get("subscription") === "1";
  const preorder = params.get("preorder") === "1";

  // 戻る・進むや条件リセットを反映する。IME変換中の文字は上書きしない。
  useEffect(() => {
    if (!composing.current) setKeywordInput(q);
  }, [q]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([getProducts(controller.signal), getCategories(controller.signal)])
      .then(([result, categoryResult]) => {
        if (controller.signal.aborted) return;
        setProducts(result.items);
        setCategories(categoryResult.items);
      })
      .catch(() => { if (!controller.signal.aborted) setError("商品を取得できませんでした。時間をおいて再度お試しください。"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [retry]);

  const filtered = useMemo(() => {
    const keyword = q.trim().toLocaleLowerCase("ja-JP");
    const items = products.filter((p) => {
      const searchable = `${p.name} ${p.producer.businessName} ${p.producer.prefectureName} ${p.producer.city}`.toLocaleLowerCase("ja-JP");
      return (!keyword || searchable.includes(keyword))
        && (!category || String(p.category.id) === category)
        && (price === "all" || (price === "under2000" ? p.salePrice < 2000 : price === "2000to4000" ? p.salePrice >= 2000 && p.salePrice < 4000 : p.salePrice >= 4000))
        && (!subscription || p.isSubscription) && (!preorder || p.isPreorder);
    });
    if (sort === "price_asc") items.sort((a, b) => a.salePrice - b.salePrice);
    if (sort === "price_desc") items.sort((a, b) => b.salePrice - a.salePrice);
    if (sort === "rating") items.sort((a, b) => (b.ratingAvg ?? -1) - (a.ratingAvg ?? -1));
    return items;
  }, [products, q, category, price, sort, subscription, preorder]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const requestedPage = Number(params.get("page") ?? 1);
  const page = Number.isInteger(requestedPage) ? Math.min(totalPages, Math.max(1, requestedPage)) : 1;
  const active = Boolean(q || category || price !== "all" || subscription || preorder);
  function update(key: string, value: string) {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      if (value) next.set(key, value); else next.delete(key);
      if (key !== "page") next.delete("page");
      return next;
    }, { replace: true });
  }
  function reset() {
    setKeywordInput("");
    setParams(sort === "popular" ? {} : { sort }, { replace: true });
  }

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-7 sm:px-8">
      <nav aria-label="パンくず" className="flex flex-wrap gap-2 text-xs text-marche-muted">
        <Link to="/" className="text-inherit no-underline hover:underline">ホーム</Link><span aria-hidden="true">/</span><span aria-current="page">商品一覧</span>
      </nav>
      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="m-0 text-xs font-bold tracking-widest text-marche-green">FROM THE PRODUCERS</p>
          <h1 className="m-0 mt-2 font-serif text-3xl font-bold">産地から届く、おいしい出会い。</h1>
          <p aria-live="polite" className="m-0 mt-2 text-sm text-marche-muted">{loading ? "商品を読み込んでいます…" : error ? "取得エラー" : `${filtered.length}件の商品`}</p>
        </div>
        <label className="flex items-center gap-2 text-sm">並び替え
          <select value={sort} onChange={(event) => update("sort", event.target.value)} className={["font-sans", `${fieldClass} w-auto`].join(" ")}>
            <option value="popular">人気順</option><option value="price_asc">価格の安い順</option><option value="price_desc">価格の高い順</option><option value="rating">評価の高い順</option>
          </select>
        </label>
      </div>

      <div className="mt-6 grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside aria-label="商品の絞り込み" className="rounded-2xl border border-marche-line bg-white p-5">
          <button type="button" aria-expanded={filtersOpen} aria-controls="product-filters" onClick={() => setFiltersOpen(!filtersOpen)} className="disabled:cursor-not-allowed flex min-h-11 w-full cursor-pointer items-center justify-between border-0 bg-transparent p-0 font-sans text-base font-bold text-marche-green lg:hidden">絞り込み<span aria-hidden="true">{filtersOpen ? "−" : "＋"}</span></button>
          <h2 className="font-serif m-0 hidden text-base font-bold lg:block">絞り込み</h2>
          <div id="product-filters" className={`${filtersOpen ? "block" : "hidden"} space-y-5 pt-4 lg:block`}>
            <label className="block text-sm font-bold">キーワード
              <input
                type="search"
                value={keywordInput}
                onCompositionStart={() => { composing.current = true; }}
                onCompositionEnd={(event) => {
                  composing.current = false;
                  const value = event.currentTarget.value;
                  setKeywordInput(value);
                  update("q", value);
                }}
                onChange={(event) => {
                  const value = event.currentTarget.value;
                  // URL遷移の完了を待たず、制御入力の値を同期的に更新する。
                  setKeywordInput(value);
                  if (!composing.current && !("isComposing" in event.nativeEvent && event.nativeEvent.isComposing)) update("q", value);
                }}
                placeholder="商品名・生産者・産地"
                className={`${fieldClass} mt-2 font-normal`}
              />
            </label>
            <label className="block text-sm font-bold">カテゴリ<select value={category} onChange={(event) => update("category", event.target.value)} className={["font-sans", `${fieldClass} mt-2 font-normal`].join(" ")}><option value="">すべて</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
            <fieldset className="m-0 min-w-0 border-0 p-0">
              <legend className="mb-2 text-sm font-bold">価格帯（税込）</legend>
              {[["all", "すべて"], ["under2000", "2,000円未満"], ["2000to4000", "2,000円〜4,000円未満"], ["over4000", "4,000円以上"]].map(([value, label]) => <label key={value} className="flex min-h-9 cursor-pointer items-center gap-2 text-sm"><input type="radio" name="price" value={value} checked={price === value} onChange={() => update("price", value)} className="font-sans accent-marche-green" />{label}</label>)}
            </fieldset>
            <fieldset className="m-0 border-0 p-0">
              <legend className="mb-2 text-sm font-bold">こだわり条件</legend>
              <label className="flex min-h-9 cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={subscription} onChange={(event) => update("subscription", event.target.checked ? "1" : "")} className="font-sans accent-marche-green" />定期購入できる</label>
              <label className="flex min-h-9 cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={preorder} onChange={(event) => update("preorder", event.target.checked ? "1" : "")} className="font-sans accent-marche-green" />予約商品</label>
            </fieldset>
            <Button variant="outline" className="w-full" onClick={reset} disabled={!active}>条件をリセット</Button>
          </div>
        </aside>
        <section aria-label="商品一覧" aria-busy={loading} className="min-w-0">
          {loading ? <p role="status" className="m-0 rounded-2xl bg-marche-sage p-8">商品を読み込んでいます…</p>
            : error ? <div role="alert" className="rounded-2xl border border-red-200 bg-white p-6"><p className="m-0 mb-4 text-red-800">{error}</p><Button onClick={() => setRetry((n) => n + 1)}>再試行</Button></div>
              : filtered.length === 0 ? <div className="rounded-2xl border border-dashed border-marche-line bg-white px-5 py-12 text-center"><h2 className="m-0 font-serif text-xl font-bold">条件に合う商品が見つかりませんでした</h2><p className="m-0 my-4 text-sm text-marche-muted">条件を減らすか、キーワードを変えてお試しください。</p><Button onClick={reset}>条件をリセット</Button></div>
                : <>
                  <div className="grid grid-cols-1 gap-4 min-[400px]:grid-cols-2 xl:grid-cols-3">{filtered.slice((page - 1) * pageSize, page * pageSize).map((product) => <ProductCard key={product.id} product={product} />)}</div>
                  {totalPages > 1 && <nav aria-label="商品一覧のページ" className="mt-6 flex items-center justify-center gap-4"><Button variant="outline" disabled={page === 1} onClick={() => update("page", String(page - 1))}>前へ</Button><span>{page} / {totalPages}</span><Button variant="outline" disabled={page === totalPages} onClick={() => update("page", String(page + 1))}>次へ</Button></nav>}
                </>}
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-orange-50 p-6"><div><h2 className="font-serif m-0 text-base font-bold text-orange-900">商品の向こうに、つくる人がいます。</h2><p className="m-0 mt-1 text-sm text-marche-muted">産地の暮らしや、生産者の想いを知ってみませんか。</p></div><Link to="/learn" className="rounded-full bg-white px-5 py-3 text-sm font-bold text-marche-green no-underline hover:underline">ストーリーを読む →</Link></div>
        </section>
      </div>
    </div>
  );
}
