import { useCallback } from 'react';
import { Link, useSearchParams } from 'react-router';
import { getConsumerOrder } from '../api/consumerOrderApi';
import ApiError from '../api/apiError';
import { usePublicContent } from '../hooks/usePublicContent';
import { USE_MOCK } from '../config/env';
import { ContentPage, ContentStatus } from '../components/ui/ContentPage';
import {
  panelClass,
  linkClass,
  textLinkClass,
} from '../components/ui/contentPageValues';
import {
  OrderTotals,
  PaymentBadge,
} from '../components/mypage/ConsumerOrderParts';

export default function CheckoutCompletePage() {
  const [params] = useSearchParams();
  const id = params.get('orderId');
  const loader = useCallback(
    (signal: AbortSignal) => {
      if (!id || !/^[1-9]\d*$/.test(id) || !Number.isSafeInteger(Number(id)))
        return Promise.reject(
          new ApiError(
            404,
            '注文情報を確認できません。注文履歴からご確認ください。',
          ),
        );
      return getConsumerOrder(Number(id), signal);
    },
    [id],
  );
  const state = usePublicContent(loader);
  const order = state.data;
  return (
    <ContentPage
      eyebrow="THANK YOU"
      title={
        order
          ? order.paymentStatus === 'paid'
            ? 'ご購入ありがとうございます'
            : order.paymentStatus === 'pending'
              ? 'ご注文を受け付けました'
              : 'ご注文状況'
          : 'ご注文の確認'
      }
    >
      <ContentStatus {...state} notFoundTo="/mypage/orders" />
      {order && (
        <section className={`${panelClass} mx-auto max-w-2xl`}>
          <p className="text-center text-sm text-marche-muted">注文番号</p>
          <h2 className="text-center font-serif text-3xl">{order.orderNo}</h2>
          <div className="text-center">
            <PaymentBadge status={order.paymentStatus} />
          </div>
          <p className="my-6 text-sm">
            {order.paymentStatus === 'paid'
              ? 'お支払いを確認しました。配送状況は注文履歴からご確認いただけます。'
              : order.paymentStatus === 'pending'
                ? 'お支払いはまだ完了していません。注文受付とお支払い完了は異なります。'
                : '最新の注文状況は注文詳細をご確認ください。'}
          </p>
          {USE_MOCK && (
            <p className="rounded-xl bg-marche-sage p-4 text-sm text-marche-muted">
              デモ注文です。実際の決済・発送は行われません。
            </p>
          )}
          <OrderTotals {...order} />
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to={`/mypage/orders/${order.id}`} className={linkClass}>
              この注文の詳細
            </Link>
            <Link to="/mypage/orders" className={textLinkClass}>
              注文履歴を見る
            </Link>
          </div>
        </section>
      )}
      <div className="mt-8 flex flex-wrap justify-center gap-6">
        <Link to="/products" className={textLinkClass}>
          買い物を続ける
        </Link>
        <Link to="/producers" className={textLinkClass}>
          つくる人を知る
        </Link>
        <Link to="/experiences" className={textLinkClass}>
          体験を探す
        </Link>
      </div>
    </ContentPage>
  );
}
