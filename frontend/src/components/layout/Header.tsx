import { useAtomValue } from "jotai";
import { Link, useLocation } from "react-router";
import { loginStatusAtom } from "../../stores/userAtom";

const links = [
  { href: "#products", label: "買う" },
  { href: "#experiences", label: "体験する" },
  { href: "#jobs", label: "働く" },
  { href: "#learn", label: "学ぶ" },
];

const actionClass =
  "inline-flex min-h-11 items-center justify-center whitespace-nowrap " +
  "rounded-full border border-marche-green px-4 py-2 text-sm font-bold " +
  "no-underline transition-colors sm:px-6 sm:text-base";

export default function Header() {
  const isHome = useLocation().pathname === "/";
  const loginStatus = useAtomValue(loginStatusAtom);
  const isLoggedIn = loginStatus === "loggedIn";

  return (
    <>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3"
      >
        本文へ
      </a>

      <div className="bg-marche-sage px-4 py-1.5 text-center text-[11px] text-marche-muted">
        2026 秋ハッカソン · 画面サンプル｜掲載情報は架空です
      </div>

      <header className="sticky top-0 z-30 border-b border-marche-line bg-marche-ivory">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8 lg:gap-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 whitespace-nowrap font-serif text-base font-bold text-marche-ink no-underline hover:no-underline sm:text-xl"
          >
            <span
              aria-hidden="true"
              className="grid size-9 place-items-center rounded-full bg-marche-green text-xl text-white"
            >
              つ
            </span>
            つながるマルシェ
          </Link>

          {isHome && (
            <nav
              aria-label="メインメニュー"
              className="order-3 flex w-full justify-around gap-3 text-sm font-bold lg:order-none lg:ml-auto lg:w-auto lg:gap-6"
            >
              {links.map(({ href, label }) => (
                <a
                  key={href}
                  href={href}
                  className="py-2 text-marche-ink no-underline hover:text-marche-green hover:underline"
                >
                  {label}
                </a>
              ))}
            </nav>
          )}

          <div className="ml-auto flex flex-wrap items-center gap-2 lg:ml-0">
            {isLoggedIn ? (
              <Link
                to="/mypage"
                className={`${actionClass} bg-marche-green text-white hover:bg-marche-green-dark`}
              >
                マイページ
              </Link>
            ) : (
              <>
                <Link
                  to="/signin"
                  className={`${actionClass} bg-transparent text-marche-green hover:bg-marche-sage`}
                >
                  ログイン
                </Link>

                <Link
                  to="/signup"
                  className={`${actionClass} bg-marche-green text-white hover:bg-marche-green-dark`}
                >
                  新規登録
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
    </>
  );
}
