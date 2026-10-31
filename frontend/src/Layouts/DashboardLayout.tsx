import type { ComponentType } from 'react';
import { Link, NavLink, Outlet } from 'react-router';
import { useAtomValue } from 'jotai';

import {
  ExperienceIcon,
  HomeIcon,
  JobIcon,
  ProductIcon,
  ProfileIcon,
  StoryIcon,
} from '../components/DashboardIcons';
import { userInfoAtom } from '../stores/userAtom';

type NavItem = {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  // /dashboard は配下のページでは選択状態にしない
  end?: boolean;
};

// 画面一覧・URL（Notion「設計」）の生産者向けページ
const navItems: NavItem[] = [
  { to: '/dashboard', label: 'ホーム', icon: HomeIcon, end: true },
  { to: '/dashboard/products', label: '商品', icon: ProductIcon },
  { to: '/dashboard/experiences', label: '体験', icon: ExperienceIcon },
  { to: '/dashboard/jobs', label: '求人', icon: JobIcon },
  { to: '/dashboard/story', label: 'ストーリー', icon: StoryIcon },
  { to: '/dashboard/profile', label: 'プロフィール', icon: ProfileIcon },
];

function navLinkClassName({ isActive }: { isActive: boolean }) {
  const base =
    'flex shrink-0 items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors';

  return isActive
    ? `${base} bg-marche-sage text-marche-green hover:text-marche-green`
    : `${base} text-marche-ink hover:bg-marche-canvas hover:text-marche-ink`;
}

// 生産者管理画面の共通レイアウト
// PC: 左にサイドバー / スマホ: 上部にロゴと横スクロールのメニュー
function DashboardLayout() {
  const userInfo = useAtomValue(userInfoAtom);

  // 審査中は管理画面に入れるが、一部の機能が制限される
  const isUnderReview =
    userInfo !== null &&
    !userInfo.isProducer &&
    userInfo.producerApplicationStatus === 'pending';

  return (
    // 画面全体に固定してこの中でスクロールする
    <div className="fixed inset-0 overflow-y-auto bg-marche-canvas text-marche-ink md:flex">
      <aside className="border-b border-marche-line bg-white md:sticky md:top-0 md:flex md:h-dvh md:w-60 md:shrink-0 md:flex-col md:border-r md:border-b-0">
        <Link
          to="/dashboard"
          className="flex items-center gap-3 px-5 pt-4 pb-3 md:pt-6 md:pb-5"
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-marche-green text-base font-bold text-white">
            つ
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-bold">つながるマルシェ</span>
            <span className="block text-xs text-marche-muted">
              生産者管理画面
            </span>
          </span>
        </Link>

        <nav
          aria-label="生産者メニュー"
          className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-0"
        >
          {navItems.map(({ to, label, icon: NavIcon, end }) => (
            <NavLink key={to} to={to} end={end} className={navLinkClassName}>
              <NavIcon />
              {label}
            </NavLink>
          ))}
        </nav>

        {userInfo !== null && (
          <div className="mt-auto hidden p-3 md:block">
            <div className="rounded-xl bg-marche-canvas px-4 py-3">
              <p className="text-sm font-bold">
                {userInfo.lastName} {userInfo.firstName}
              </p>
              <p className="truncate text-xs text-marche-muted">
                {userInfo.email}
              </p>
            </div>
            <Link
              to="/"
              className="mt-2 block rounded-xl px-4 py-2 text-center text-xs font-bold text-marche-green hover:bg-marche-canvas hover:text-marche-green"
            >
              サイトを見る
            </Link>
          </div>
        )}
      </aside>

      <div className="min-w-0 flex-1">
        {isUnderReview && (
          <div
            role="status"
            className="border-b border-marche-orange/40 bg-marche-orange/15 px-4 py-3 text-sm md:px-10"
          >
            生産者登録の審査中です。承認されるまで、一部の機能は使えません。
            <Link
              to="/producer-application"
              className="ml-2 font-bold text-marche-green underline hover:text-marche-green"
            >
              申請状況を見る
            </Link>
          </div>
        )}

        <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-10 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;
