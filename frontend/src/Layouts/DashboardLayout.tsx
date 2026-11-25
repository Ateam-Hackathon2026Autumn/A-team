import { useCallback, useEffect, useRef, type ComponentType } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
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
import { DashboardScrollContext } from './dashboardScroll';

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
    'flex shrink-0 items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-bold no-underline transition-colors';

  return isActive
    ? `${base} bg-marche-sage text-marche-green hover:text-marche-green`
    : `${base} text-marche-ink hover:bg-marche-canvas hover:text-marche-ink`;
}

// 生産者管理画面の共通レイアウト
// PC: 左にサイドバー / スマホ: 上部にロゴと横スクロールのメニュー
function DashboardLayout() {
  const userInfo = useAtomValue(userInfoAtom);
  // スクロールするのはこの画面全体の div なので、ルート遷移時の先頭移動もこの div に対して行う
  const scrollRef = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  const scrollToTop = useCallback(() => scrollRef.current?.scrollTo({ top: 0 }), []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [pathname]);

  // 審査中は管理画面に入れるが、一部の機能が制限される
  const isUnderReview =
    userInfo !== null &&
    !userInfo.isProducer &&
    userInfo.producerApplicationStatus === 'pending';

  return (
    <DashboardScrollContext.Provider value={scrollToTop}>
      {/* 画面全体に固定してこの中でスクロールする */}
      <div ref={scrollRef} className="fixed inset-0 overflow-y-auto bg-marche-canvas font-sans text-[15px] leading-[1.8] text-marche-ink md:flex">
        <aside className="box-border border-0 border-b border-solid border-marche-line bg-white md:sticky md:top-0 md:flex md:h-dvh md:w-60 md:shrink-0 md:flex-col md:border-r md:border-b-0">
          {/* スマホ: ロゴの右に一般サイトへ戻るリンク（PC ではサイドバー下部に表示） */}
          <div className="flex items-center justify-between gap-3 pr-4 md:block md:pr-0">
            <Link
              to="/dashboard"
              className="flex min-w-0 items-center gap-3 px-5 pt-4 pb-3 text-marche-ink no-underline md:pt-6 md:pb-5"
            >
              <img src="/favicon.svg" alt="" aria-hidden="true" className="size-9 shrink-0 rounded-full" />
              <span className="leading-tight">
                <span className="block text-sm font-bold">つながるマルシェ</span>
                <span className="block text-xs text-marche-muted">
                  生産者管理画面
                </span>
              </span>
            </Link>
            <Link
              to="/"
              className="shrink-0 rounded-full border border-solid border-marche-line px-3 py-1.5 text-xs font-bold text-marche-green no-underline hover:bg-marche-canvas hover:text-marche-green md:hidden"
            >
              サイトを見る
            </Link>
          </div>

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
                <p className="m-0 text-sm font-bold">
                  {userInfo.lastName} {userInfo.firstName}
                </p>
                <p className="m-0 truncate text-xs text-marche-muted">
                  {userInfo.email}
                </p>
              </div>
              <Link
                to="/"
                className="mt-2 block rounded-xl px-4 py-2 text-center no-underline text-xs font-bold text-marche-green hover:bg-marche-canvas hover:text-marche-green"
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
              className="border-0 border-b border-solid border-marche-orange/40 bg-marche-orange/15 px-4 py-3 text-sm md:px-10"
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

          <main className="mx-auto box-border w-full max-w-6xl px-4 py-6 md:px-10 md:py-8">
            <Outlet />
          </main>
        </div>
      </div>
    </DashboardScrollContext.Provider>
  );
}

export default DashboardLayout;
