import { yen } from '../ui/contentPageValues';
import { paymentLabels } from './consumerOrderLabels';
export function PaymentBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-bold ${status === 'paid' ? 'bg-marche-sage text-marche-green' : 'bg-marche-orange/20 text-marche-ink'}`}
    >
      {paymentLabels[status] ?? status}
    </span>
  );
}
export function OrderTotals({
  itemsTotal,
  shippingTotal,
  grandTotal,
}: {
  itemsTotal: number;
  shippingTotal: number;
  grandTotal: number;
}) {
  return (
    <dl className="m-0 space-y-3">
      <div className="flex justify-between gap-4">
        <dt>商品小計（税込）</dt>
        <dd className="m-0">{yen(itemsTotal)}</dd>
      </div>
      <div className="flex justify-between gap-4">
        <dt>送料</dt>
        <dd className="m-0">{yen(shippingTotal)}</dd>
      </div>
      <div className="flex justify-between gap-4 border-t border-solid border-marche-line pt-4 text-xl font-bold">
        <dt>合計（税込）</dt>
        <dd className="m-0">{yen(grandTotal)}</dd>
      </div>
    </dl>
  );
}
