import { Outlet } from "react-router";

export default function AuthLayout() {
  return (
    <div className="px-4 py-8 sm:px-6 lg:py-14">
      <div className="mx-auto grid max-w-[1060px] overflow-hidden rounded-3xl border border-marche-line bg-white md:grid-cols-[0.8fr_1.2fr]">
        <aside className="hidden flex-col justify-between bg-marche-sage px-9 py-12 md:flex">
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-marche-green">
              A NEW CONNECTION
            </p>

            <h2 className="mt-6 text-3xl font-bold leading-relaxed">
              つくる人を知る。
              <br />
              暮らしが、変わる。
            </h2>

            <p className="mt-5 text-sm leading-8">
              おいしい出会いも、新しい挑戦も。
              <br />
              あなたと産地をつなぐ場所へ。
            </p>
          </div>

          <div aria-hidden="true" className="py-12 text-center text-8xl">
            🌿
          </div>

          <p className="text-sm text-marche-muted">
            買う ・ 体験する ・ 働く ・ 学ぶ
          </p>
        </aside>

        <section
          aria-label="アカウント手続き"
          className="min-w-0 px-5 py-8 sm:px-8 lg:px-12 lg:py-10"
        >
          <Outlet />
        </section>
      </div>

      <p className="mx-auto mt-5 max-w-3xl text-center text-xs leading-6 text-marche-muted">
        画面確認用デモです。APIは未接続です。
        実際の個人情報や普段使うパスワードは入力しないでください。
      </p>
    </div>
  );
}