import { useRef, useState, type FormEvent } from "react";
import { useAtomValue } from "jotai";
import { Link, useNavigate } from "react-router";
import { getCart } from "../api/cartApi";
import { getProduct } from "../api/productApi";
import { createConsumerOrder } from "../api/consumerOrderApi";
import { usePublicContent } from "../hooks/usePublicContent";
import { loginStatusAtom, userInfoAtom } from "../stores/userAtom";
import { USE_MOCK } from "../config/env";
import { PREFECTURES } from "../utils/prefectures";
import { consumerShippingGroups } from "../utils/consumerCheckout";
import type { ShippingAddress } from "../types/consumerOrder";
import { ContentPage, ContentStatus, EmptyContent, fieldClass, panelClass, textLinkClass, yen, linkClass } from "../components/ui/ContentPage";
import { OrderTotals, temperatureLabels } from "../components/mypage/ConsumerOrderParts";
import Button from "../components/ui/Button";

async function loadCheckout(signal: AbortSignal) {
  const cart = await getCart(signal);
  if (!cart.canCheckout) return { cart, groups: [], shippingTotal: 0 };
  const products = await Promise.all(cart.items.map((item) => getProduct(item.productId, signal)));
  const groups = consumerShippingGroups(cart, products);
  return { cart, groups, shippingTotal: groups.reduce((sum, group) => sum + group.shippingFee, 0) };
}

const addressFields: { key: keyof ShippingAddress; label: string; autoComplete: string; maxLength: number; pattern?: string; type?: string }[] = [
  { key: "lastName", label: "姓", autoComplete: "family-name", maxLength: 50 },
  { key: "firstName", label: "名", autoComplete: "given-name", maxLength: 50 },
  { key: "postalCode", label: "郵便番号（例：123-4567）", autoComplete: "postal-code", maxLength: 8, pattern: "[0-9]{3}-?[0-9]{4}" },
  { key: "city", label: "市区町村", autoComplete: "address-level2", maxLength: 50 },
  { key: "addressLine1", label: "町名・番地", autoComplete: "address-line1", maxLength: 100 },
  { key: "addressLine2", label: "建物名・部屋番号（任意）", autoComplete: "address-line2", maxLength: 100 },
  { key: "phone", label: "電話番号", autoComplete: "tel", maxLength: 20, type: "tel", pattern: "[0-9-]{10,20}" },
];

export default function CheckoutPage() {
  const state = usePublicContent(loadCheckout);
  const login = useAtomValue(loginStatusAtom);
  const user = useAtomValue(userInfoAtom);
  const navigate = useNavigate();
  const [address, setAddress] = useState<ShippingAddress>({ lastName: user?.lastName ?? "", firstName: user?.firstName ?? "", postalCode: "", prefecture: "", city: "", addressLine1: "", addressLine2: "", phone: "" });
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const key = useRef<string | null>(null);
  const locked = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const data = state.data;
  const grandTotal = data ? data.cart.itemsTotal + data.shippingTotal : 0;
  function changeStep(next: number) {
    setStep(next);
    setError("");
    requestAnimationFrame(() => heading.current?.focus());
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || !data || !data.cart.canCheckout) return;
    if (step === 1) {
      if (!/^0\d{9,10}$/.test(address.phone.replace(/-/g, ""))) {
        setError("電話番号は0から始まる10〜11桁で入力してください。");
        return;
      }
      if (!address.lastName.trim() || !address.firstName.trim() || !address.city.trim() || !address.addressLine1.trim()) {
        setError("空白だけの項目があります。お届け先を確認してください。");
        return;
      }
      changeStep(2);
      return;
    }
    locked.current = true;
    setBusy(true);
    setError("");
    try {
      key.current ??= crypto.randomUUID();
      const receipt = await createConsumerOrder({ shippingAddress: address, paymentMethod: "card", expectedGrandTotal: grandTotal, quoteToken: data.cart.quoteToken }, key.current);
      navigate(`/checkout/complete?orderId=${receipt.id}`, { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "注文を受け付けられませんでした。");
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  return (
    <ContentPage
      eyebrow="CHECKOUT"
      title="購入手続き"
      intro="つくる人のもとから、あなたの食卓へ。"
    >
      <ol
        aria-label="購入のステップ"
        className="mb-8 flex list-none flex-wrap gap-3 p-0 text-sm font-bold"
      >
        {["お届け先・お支払い", "ご注文内容の確認", "注文受付"].map((label, i) => (
          <li
            key={label}
            aria-current={step === i + 1 ? "step" : undefined}
            className={`rounded-full px-4 py-2 ${step === i + 1 ? "bg-marche-green text-white" : "bg-marche-sage text-marche-muted"}`}
          >
            {i + 1}. {label}
          </li>
        ))}
      </ol>
      {login !== "loggedIn" ? (
        <EmptyContent>
          <p>購入手続きにはログインが必要です。</p>
          <Link
            to="/signin"
            state={{ from: { pathname: "/checkout" } }}
            className={linkClass}
          >
            ログインする
          </Link>
        </EmptyContent>
      ) : (
        <>
          <ContentStatus {...state} />
          {data &&
            (!data.cart.canCheckout ? (
              <EmptyContent>
                <p>{data.cart.items.length === 0 ? "カートは空です。" : "購入できない商品が含まれています。カートをご確認ください。"}</p>
                <Link
                  to="/cart"
                  className={linkClass}
                >
                  カートへ戻る
                </Link>
              </EmptyContent>
            ) : (
              <form
                onSubmit={submit}
                aria-busy={busy}
                className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]"
              >
                <div className="min-w-0 space-y-6">
                  <section className={panelClass}>
                    <h2
                      ref={heading}
                      tabIndex={-1}
                      className="mt-0 font-serif text-xl"
                    >
                      {step === 1 ? "お届け先" : "お届け先の確認"}
                    </h2>
                    {step === 1 ? (
                      <fieldset
                        disabled={busy}
                        className="m-0 grid min-w-0 gap-5 border-0 p-0 sm:grid-cols-2"
                      >
                        <legend className="sr-only">お届け先の入力</legend>
                        {addressFields.map((field) => (
                          <label
                            key={field.key}
                            className="text-sm font-bold"
                          >
                            {field.label}
                            {field.key !== "addressLine2" && "（必須）"}
                            <input
                              required={field.key !== "addressLine2"}
                              type={field.type ?? "text"}
                              autoComplete={field.autoComplete}
                              maxLength={field.maxLength}
                              pattern={field.pattern}
                              className={`${fieldClass} mt-2`}
                              value={address[field.key]}
                              onChange={(e) => {
                                setAddress({ ...address, [field.key]: e.target.value });
                                key.current = null;
                              }}
                            />
                          </label>
                        ))}
                        <label className="text-sm font-bold">
                          都道府県（必須）
                          <select
                            required
                            autoComplete="address-level1"
                            className={`${fieldClass} mt-2`}
                            value={address.prefecture}
                            onChange={(e) => {
                              setAddress({ ...address, prefecture: e.target.value });
                              key.current = null;
                            }}
                          >
                            <option value="">選択してください</option>
                            {PREFECTURES.map((p) => (
                              <option key={p.id}>{p.name}</option>
                            ))}
                          </select>
                        </label>
                      </fieldset>
                    ) : (
                      <>
                        <p>
                          〒{address.postalCode}
                          <br />
                          {address.prefecture}
                          {address.city}
                          {address.addressLine1} {address.addressLine2}
                          <br />
                          {address.lastName} {address.firstName} 様<br />
                          {address.phone}
                        </p>
                        <Button
                          onClick={() => changeStep(1)}
                          variant="outline"
                          disabled={busy}
                        >
                          お届け先を変更
                        </Button>
                      </>
                    )}
                  </section>
                  <section className={panelClass}>
                    <h2 className="mt-0 font-serif text-xl">配送・お支払い</h2>
                    <p className="text-sm">生産者・配送温度帯ごとに産地から直送します。配送日時は指定できません。</p>
                    <p className="text-sm">お支払い：クレジットカード</p>
                    <p className="mb-0 text-sm text-marche-muted">{USE_MOCK ? "デモ注文です。カード情報の入力や実際のお支払いは行いません。" : "送料見積り・決済連携は準備中です。現在は注文できません。"}</p>
                  </section>
                </div>
                <aside className={panelClass}>
                  <h2 className="mt-0 font-serif text-xl">ご注文内容</h2>
                  <ul className="list-none space-y-3 p-0 text-sm">
                    {data.cart.items.map((item) => (
                      <li
                        key={item.id}
                        className="flex justify-between gap-3"
                      >
                        <span>
                          {item.productName}
                          <br />
                          数量 {item.quantity}点
                        </span>
                        <strong className="shrink-0">{yen(item.subtotal ?? 0)}</strong>
                      </li>
                    ))}
                  </ul>
                  <ul className="my-5 list-none space-y-2 border-t border-solid border-marche-line p-0 pt-4 text-xs text-marche-muted">
                    {data.groups.map((group) => (
                      <li key={`${group.producerId}:${group.temperatureZone}`}>
                        {group.producerName} · {temperatureLabels[group.temperatureZone] ?? group.temperatureZone}便：{yen(group.shippingFee)}
                      </li>
                    ))}
                  </ul>
                  <OrderTotals
                    itemsTotal={data.cart.itemsTotal}
                    shippingTotal={data.shippingTotal}
                    grandTotal={grandTotal}
                  />
                  {!USE_MOCK && <p className="text-xs text-marche-muted">送料・合計は参考表示です。正式見積り後に確定します。</p>}
                  {error && (
                    <p
                      role="alert"
                      className="text-sm font-bold text-marche-red"
                    >
                      {error}
                    </p>
                  )}
                  <Button
                    type="submit"
                    block
                    disabled={busy || (step === 2 && !USE_MOCK)}
                  >
                    {busy ? "注文を送信中…" : step === 1 ? "注文内容を確認する" : USE_MOCK ? "デモ注文を受け付ける" : "注文受付（準備中）"}
                  </Button>
                  {step === 2 && (
                    <Button
                      variant="outline"
                      block
                      disabled={busy}
                      onClick={() => changeStep(1)}
                    >
                      入力に戻る
                    </Button>
                  )}
                  <Link
                    to="/cart"
                    className={`${textLinkClass} mt-4`}
                  >
                    カートへ戻る
                  </Link>
                </aside>
              </form>
            ))}
        </>
      )}
    </ContentPage>
  );
}
