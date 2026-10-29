import type { Purpose } from "../../../types/auth";
import Button from "../../../components/ui/Button";

type Props = { purpose: Purpose | ""; onChange: (purpose: Purpose) => void; onNext: () => void };
export default function PurposeStep({ purpose, onChange, onNext }: Props) {
  return (
    <>
      <p className="eyebrow">CREATE YOUR ACCOUNT</p><h1>どのように<br />利用しますか？</h1>
      <p className="muted">はじめに、利用目的を教えてください。</p>
      <form onSubmit={(e) => { e.preventDefault(); if (purpose) onNext(); }}>
        {([
          ["consumer", "🧺", "買う・体験する・働く", "商品の購入、体験への参加、仕事への応募"],
          ["producer", "🌱", "生産者として利用する", "商品販売・体験・求人を掲載したい"],
        ] as const).map(([value, icon, title, description]) => (
          <label className="choice" key={value}>
            <input type="radio" name="purpose" checked={purpose === value} onChange={() => onChange(value)} />
            <span className="choice-icon" aria-hidden="true">{icon}</span>
            <span><b>{title}</b><small>{description}</small></span>
          </label>
        ))}
        <p className="hint">生産者の方も、共通アカウントの作成後に登録申請へ進みます。</p>
        <Button block type="submit" disabled={!purpose}>次へ →</Button>
      </form>
    </>
  );
}
