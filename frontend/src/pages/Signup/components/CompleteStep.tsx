import { Link } from "react-router";
import type { Purpose } from "../../../types/auth";

type Props = { purpose: Purpose };
export default function CompleteStep({ purpose }: Props) {
  return (
    <div className="center">
      <div className="success-icon" aria-hidden="true">✓</div>
      <p className="eyebrow">FORM VALIDATION COMPLETED</p><h1>入力チェックが完了しました！</h1>
      <p className="notice">これはフロントエンドだけの画面デモです。<br />サーバーへの登録・確認メール送信・ログインは行っていません。</p>
      <p>{purpose === "producer" ? "本番では、共通アカウント登録後に生産者の登録申請へ進みます。" : "本番では、登録後に商品の閲覧や各サービスへ進めます。"}</p>
      <Link className="btn block" to="/">ホームへ戻る →</Link>
    </div>
  );
}
