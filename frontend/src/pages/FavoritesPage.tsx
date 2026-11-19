import { useState } from "react";
import { Link } from "react-router";
import MyPageNavigation from "../components/mypage/MyPageNavigation";
import { ContentPage, EmptyContent, linkClass } from "../components/ui/ContentPage";
import Button from "../components/ui/Button";

export default function FavoritesPage() {
  const [kind, setKind] = useState<"products" | "producers">("products");
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
          variant={kind === "products" ? "primary" : "outline"}
          aria-pressed={kind === "products"}
          onClick={() => setKind("products")}
        >
          商品
        </Button>
        <Button
          variant={kind === "producers" ? "primary" : "outline"}
          aria-pressed={kind === "producers"}
          onClick={() => setKind("producers")}
        >
          生産者
        </Button>
      </div>
      <EmptyContent>
        <h2 className="font-serif text-xl">お気に入り機能は準備中です</h2>
        <p className="text-sm text-marche-muted">保存済みの{kind === "products" ? "商品" : "生産者"}は、機能の接続後にここで確認できます。</p>
        <Link
          to={kind === "products" ? "/products" : "/producers"}
          className={linkClass}
        >
          {kind === "products" ? "商品を探す" : "生産者を探す"}
        </Link>
      </EmptyContent>
    </ContentPage>
  );
}
