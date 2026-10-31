import { useAtomValue } from "jotai";
import { Link } from "react-router";
import { loginStatusAtom } from "../../stores/userAtom";

export default function Footer() {
  const isLoggedIn = useAtomValue(loginStatusAtom) === "loggedIn";

  return (
    <footer className="mt-16 border-t border-marche-line">
      <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 font-serif text-lg font-bold text-marche-ink no-underline hover:no-underline"
          >
            <span
              aria-hidden="true"
              className="grid size-8 place-items-center rounded-full bg-marche-green text-white"
            >
              つ
            </span>
            つながるマルシェ
          </Link>

          <nav
            aria-label="フッターメニュー"
            className="flex flex-wrap gap-5 text-sm text-marche-green"
          >
            {isLoggedIn ? (
              <Link to="/mypage" className="hover:underline">
                マイページ
              </Link>
            ) : (
              <>
                <Link to="/signup?purpose=producer" className="hover:underline">
                  生産者の方へ
                </Link>
                <Link to="/signin" className="hover:underline">
                  ログイン
                </Link>
                <Link to="/signup" className="hover:underline">
                  新規登録
                </Link>
              </>
            )}
          </nav>
        </div>

        <p className="mt-6 text-xs text-marche-muted">
          © 2026 つながるマルシェ · Hackathon prototype
        </p>
      </div>
    </footer>
  );
}
