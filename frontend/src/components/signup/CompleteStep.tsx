import { Link, Navigate, useLocation } from "react-router";

export default function CompleteStep() {
  const { state } = useLocation();
  // URL を直接開いただけでは登録成功と表示しない。
  if (state?.registered !== true)
    return (
      <Navigate
        to="/"
        replace
      />
    );
  const producer = state.purpose === "producer";
  return (
    <div className="text-center">
      <div
        aria-hidden="true"
        className="mx-auto my-5 grid size-16 place-items-center rounded-full bg-marche-sage text-marche-green"
      >
        <CheckIcon className="size-9" />
      </div>
      <p className="m-0 text-xs font-bold tracking-widest text-marche-green">REGISTRATION COMPLETED</p>
      <h1 className="m-0 mt-3 font-serif text-2xl font-bold sm:text-3xl">登録が完了しました！</h1>
      <p className="my-5 rounded-xl bg-marche-sage p-4 text-sm leading-7">ログインしました。確認メールの配送を受け付けました。メール内のリンクから認証を完了してください。</p>
      {state.csrfRefreshFailed && (
        <p
          role="alert"
          className="text-sm text-red-800"
        >
          登録は完了しています。通信を確認できなかったため、次の操作でエラーになる場合はページを再読み込みしてください。
        </p>
      )}
      <p className="text-sm text-marche-muted">{producer ? "続けて生産者の登録申請にお進みください。" : "商品の閲覧や各サービスをご利用いただけます。"}</p>
      <Link
        to={producer ? "/producer-application/new" : "/"}
        className="no-underline mt-6 flex min-h-12 items-center justify-center rounded-full bg-marche-green px-6 py-3 text-sm font-bold text-white hover:bg-marche-green-dark"
      >
        {producer ? "生産者の登録申請へ →" : "ホームへ戻る →"}
      </Link>
    </div>
  );
}
