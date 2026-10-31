import { Link } from "react-router";
import type { Purpose } from "../../types/authForm";

type Props = {
  purpose: Purpose;
};

export default function CompleteStep({ purpose }: Props) {
  return (
    <div className="text-center">
      <div
        aria-hidden="true"
        className="mx-auto my-5 grid size-16 place-items-center rounded-full bg-marche-sage text-3xl text-marche-green"
      >
        ✓
      </div>

      <p className="text-xs font-bold tracking-widest text-marche-green">
        FORM VALIDATION COMPLETED
      </p>
      <h1 className="mt-3 text-2xl font-bold sm:text-3xl">
        入力チェックが完了しました！
      </h1>

      <p className="my-5 rounded-xl bg-marche-sage p-4 text-sm leading-7">
        これはフロントエンドだけの画面デモです。
        <br />
        サーバーへの登録・確認メール送信・ログインは行っていません。
      </p>

      <p className="text-sm text-marche-muted">
        {purpose === "producer"
          ? "本番では、共通アカウント登録後に生産者の登録申請へ進みます。"
          : "本番では、登録後に商品の閲覧や各サービスへ進めます。"}
      </p>

      <Link
        to="/"
        className="mt-6 flex min-h-12 items-center justify-center rounded-full bg-marche-green px-6 py-3 text-sm font-bold text-white hover:bg-marche-green-dark"
      >
        ホームへ戻る →
      </Link>
    </div>
  );
}