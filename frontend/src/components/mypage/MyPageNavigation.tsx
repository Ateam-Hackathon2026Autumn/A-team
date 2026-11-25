import { useAtomValue } from "jotai";
import { Link, NavLink } from "react-router";
import { userInfoAtom } from "../../stores/userAtom";
import type { UserInfo } from "../../types/user";

const items = [
  ["/mypage", "マイページ"],
  ["/mypage/favorites", "お気に入り"],
  ["/mypage/orders", "注文履歴"],
  ["/mypage/experiences", "体験予約履歴"],
  ["/mypage/jobs", "求人応募履歴"],
  ["/mypage/profile", "プロフィール編集"],
  ["/mypage/settings", "アカウント設定"],
];

// 生産者登録の導線。生産者として利用中の会員には出さない。
function producerApplicationLink(user: UserInfo | null): { to: string; label: string } | null {
  if (user === null || user.isProducer) return null;
  if (user.producerApplicationStatus === "not_applied") return { to: "/producer-application/new", label: "生産者として登録申請する" };
  if (user.producerApplicationStatus === "pending" || user.producerApplicationStatus === "returned" || user.producerApplicationStatus === "rejected") {
    return { to: "/producer-application", label: "生産者申請の状況" };
  }
  return null;
}

export default function MyPageNavigation() {
  const userInfo = useAtomValue(userInfoAtom);
  const producerLink = producerApplicationLink(userInfo);
  return (
    <nav
      aria-label="マイページメニュー"
      className="mb-8 flex flex-wrap gap-2"
    >
      {items.map(([to, label]) => (
        <NavLink
          key={to}
          to={to}
          end
          className={({ isActive }) => `inline-flex min-h-11 items-center rounded-full border border-solid px-4 py-2 text-sm font-bold no-underline ${isActive ? "border-marche-green bg-marche-green text-white" : "border-marche-line bg-white text-marche-ink hover:bg-marche-sage"}`}
        >
          {label}
        </NavLink>
      ))}
      {producerLink && (
        <Link
          to={producerLink.to}
          className="inline-flex min-h-11 items-center rounded-full border border-solid border-marche-green bg-white px-4 py-2 text-sm font-bold text-marche-green no-underline hover:bg-marche-sage"
        >
          {producerLink.label}
        </Link>
      )}
    </nav>
  );
}
