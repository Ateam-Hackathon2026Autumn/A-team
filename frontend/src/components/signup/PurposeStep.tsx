import Button from "../ui/Button";
import type { Purpose } from "../../types/authForm";

type Props = {
  purpose: Purpose | "";
  onChange: (purpose: Purpose) => void;
  onNext: () => void;
};

const choices = [
  {
    value: "consumer",
    image: "/images/categories/buy.webp",
    title: "買う・体験する・働く",
    description: "商品の購入、体験への参加、仕事への応募",
  },
  {
    value: "producer",
    image: "/images/categories/producer.webp",
    title: "生産者として利用する",
    description: "商品販売・体験・求人を掲載したい",
  },
] as const;

export default function PurposeStep({
  purpose,
  onChange,
  onNext,
}: Props) {
  return (
    <>
      <p className="m-0 text-xs font-bold tracking-widest text-marche-green">
        CREATE YOUR ACCOUNT
      </p>
      <h1 className="m-0 font-serif mt-2 text-3xl font-bold leading-relaxed">
        どのように
        <br />
        利用しますか？
      </h1>
      <p className="m-0 mt-3 text-sm text-marche-muted">
        はじめに、利用目的を教えてください。
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (purpose) onNext();
        }}
      >
        {choices.map(({ value, image, title, description }) => (
          <label
            key={value}
            className={`mt-4 flex cursor-pointer items-center gap-3 rounded-xl border p-4 ${
              purpose === value
                ? "border-marche-green bg-marche-sage ring-1 ring-marche-green"
                : "border-marche-line"
            }`}
          >
            <input
              type="radio"
              name="purpose"
              value={value}
              checked={purpose === value}
              onChange={() => onChange(value)}
              className="font-sans size-4 shrink-0 accent-marche-green"
            />

            <img
              src={image}
              width={512}
              height={512}
              decoding="async"
              alt=""
              className="size-14 shrink-0 rounded-xl object-cover"
            />

            <span>
              <span className="block text-sm font-bold">{title}</span>
              <span className="mt-1 block text-xs text-marche-muted">
                {description}
              </span>
            </span>
          </label>
        ))}

        <p className="m-0 mt-4 text-xs text-marche-muted">
          生産者の方も、共通アカウントの作成後に登録申請へ進みます。
        </p>

        <Button block type="submit" disabled={!purpose}>
          次へ →
        </Button>
      </form>
    </>
  );
}
