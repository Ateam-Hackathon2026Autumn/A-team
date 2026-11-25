import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { getConsumerOrder } from "../api/consumerOrderApi";
import ApiError from "../api/apiError";
import { usePublicContent } from "../hooks/usePublicContent";
import { ContentPage, ContentStatus, panelClass, textLinkClass, dateLabel, yen } from "../components/ui/ContentPage";
import MyPageNavigation from "../components/mypage/MyPageNavigation";
import { PaymentBadge, OrderTotals, shipmentLabels, temperatureLabels } from "../components/mypage/ConsumerOrderParts";

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const loader = useCallback(
    (signal: AbortSignal) => {
      if (!orderId || !/^[1-9]\d*$/.test(orderId) || !Number.isSafeInteger(Number(orderId))) return Promise.reject(new ApiError(404, "注文が見つかりません。"));
      return getConsumerOrder(Number(orderId), signal);
    },
    [orderId],
  );

  const state = usePublicContent(loader);
  const order = state.data;
  return (
    <ContentPage
      eyebrow="ORDER DETAIL"
      title="注文詳細"
    >
      <MyPageNavigation />
      <Link
        to="/mypage/orders"
        className={textLinkClass}
      >
        ← 注文履歴へ
      </Link>
      <ContentStatus
        {...state}
        notFoundTo="/mypage/orders"
      />
      {order && (
        <div className="mt-6 space-y-6">
          <section className={panelClass}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="m-0 font-serif text-2xl">{order.orderNo}</h2>
              <PaymentBadge status={order.paymentStatus} />
            </div>
            <p className="text-sm text-marche-muted">注文日：{dateLabel(order.orderedAt)}</p>
            <OrderTotals {...order} />
          </section>
          {order.shipments.map((box) => (
            <section
              key={box.id}
              className={panelClass}
            >
              <div className="flex flex-wrap justify-between gap-3">
                <h2 className="m-0 font-serif text-xl">{box.producer.businessName}</h2>
                <span className="text-sm font-bold text-marche-green">{shipmentLabels[box.status] ?? box.status}</span>
              </div>
              <p className="text-sm text-marche-muted">
                {temperatureLabels[box.temperatureZone] ?? box.temperatureZone}便 · 送料 {yen(box.shippingFee)}
              </p>
              <ul className="list-none space-y-4 p-0">
                {box.items.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap justify-between gap-2 border-t border-solid border-marche-line pt-4"
                  >
                    <div>
                      {item.productId ? (
                        <Link
                          className={textLinkClass}
                          to={`/products/${item.productId}`}
                        >
                          {item.productName}
                        </Link>
                      ) : (
                        item.productName
                      )}
                      <p className="m-0 text-sm">数量 {item.quantity}点</p>
                    </div>
                    <strong>{yen(item.subtotal)}</strong>
                  </li>
                ))}
              </ul>
              {box.trackingNo && <p className="text-sm">お問い合わせ番号：{box.trackingNo}</p>}
            </section>
          ))}
          
          <section className={panelClass}>
            <h2 className="mt-0 font-serif text-xl">お届け先</h2>
            <p className="m-0">
              〒{order.shippingAddress.postalCode}
              <br />
              {order.shippingAddress.prefecture}
              {order.shippingAddress.city}
              {order.shippingAddress.addressLine1} {order.shippingAddress.addressLine2}
              <br />
              {order.shippingAddress.name} 様<br />
              {order.shippingAddress.phone}
            </p>
          </section>
        </div>
      )}
    </ContentPage>
  );
}
