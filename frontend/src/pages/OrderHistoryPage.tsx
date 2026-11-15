import { useState } from "react";
import { Link } from "react-router";
import { getConsumerOrders } from "../api/consumerOrderApi";
import { usePublicContent } from "../hooks/usePublicContent";
import { ContentPage, ContentStatus, EmptyContent, dateLabel, yen, panelClass, linkClass } from "../components/ui/ContentPage";
import MyPageNavigation from "../components/mypage/MyPageNavigation";
import { PaymentBadge, paymentLabels, shipmentLabels } from "../components/mypage/ConsumerOrderParts";

export default function OrderHistoryPage() {
  const state = usePublicContent(getConsumerOrders);
  const [filter, setFilter] = useState("all");
  const orders = state.data?.filter((order) => filter === "all" || order.paymentStatus === filter);
  return (
    <ContentPage
      eyebrow="ORDERS"
      title="注文履歴"
      intro="産地から届く楽しみと、これまでのお買い物。"
    >
      <MyPageNavigation />
      <label className="mb-6 flex flex-wrap items-center gap-3 text-sm font-bold">
        支払い状況
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="min-h-11 rounded-xl border border-solid border-marche-line bg-white px-4 font-sans text-base"
        >
          <option value="all">すべて</option>
          {Object.entries(paymentLabels).map(([value, text]) => (
            <option
              key={value}
              value={value}
            >
              {text}
            </option>
          ))}
        </select>
      </label>
      <ContentStatus {...state} />
      {orders?.length === 0 && (
        <EmptyContent>
          <p>該当する注文はありません。</p>
          <Link
            to="/products"
            className={linkClass}
          >
            商品を探す
          </Link>
        </EmptyContent>
      )}
      <div className="space-y-5">
        {orders?.map((order) => (
          <article
            key={order.id}
            className={panelClass}
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="m-0 text-sm text-marche-muted">{dateLabel(order.orderedAt)}</p>
                <h2 className="mb-2 mt-1 font-serif text-xl">{order.orderNo}</h2>
              </div>
              <PaymentBadge status={order.paymentStatus} />
            </div>
            <ul className="my-4 list-none space-y-2 p-0">
              {order.shipments.map((box) => (
                <li
                  key={box.id}
                  className="rounded-lg bg-marche-canvas px-4 py-3 text-sm"
                >
                  {box.producerName ?? `生産者 #${box.producerId}`} <span className="ml-3 text-marche-muted">{shipmentLabels[box.status] ?? box.status}</span>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="m-0 font-bold">
                合計（税込） <span className="ml-3 text-xl">{yen(order.grandTotal)}</span>
              </p>
              <Link
                to={`/mypage/orders/${order.id}`}
                className={linkClass}
              >
                注文詳細を見る
              </Link>
            </div>
          </article>
        ))}
      </div>
    </ContentPage>
  );
}
