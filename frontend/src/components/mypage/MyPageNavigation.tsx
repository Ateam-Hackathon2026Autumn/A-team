import { NavLink } from "react-router";

const items = [
  ["/mypage", "マイページ"],
  ["/mypage/favorites", "お気に入り"],
  ["/mypage/orders", "注文履歴"],
  ["/mypage/experiences", "体験予約履歴"],
  ["/mypage/jobs", "求人応募履歴"],
  ["/mypage/profile", "プロフィール編集"],
  ["/mypage/settings", "アカウント設定"],
];

export default function MyPageNavigation() {
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
    </nav>
  );
}
