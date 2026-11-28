export type ShippingAddress = {
  lastName: string;
  firstName: string;
  postalCode: string;
  prefecture: string;
  city: string;
  addressLine1: string;
  addressLine2: string;
  phone: string;
};
export type OrderSummary = {
  id: number;
  orderNo: string;
  paymentStatus: string;
  paymentMethod?: string;
  itemsTotal: number;
  shippingTotal: number;
  grandTotal: number;
  orderedAt: string;
  shipments: {
    id: number;
    producerId: number;
    producerName?: string;
    temperatureZone: string;
    status: string;
    shippingFee: number;
  }[];
};
export type OrderShipment = {
  id: number;
  producer: { id: number; businessName: string };
  temperatureZone: string;
  status: string;
  shippingFee: number;
  trackingNo: string | null;
  items: {
    id: number;
    productId: number | null;
    productName: string;
    quantity: number;
    subtotal: number;
  }[];
};
export type OrderDetail = Omit<OrderSummary, 'shipments'> & {
  shippingAddress: {
    name: string;
    postalCode: string;
    prefecture: string;
    city: string;
    addressLine1: string;
    addressLine2: string | null;
    phone: string;
  };
  shipments: OrderShipment[];
};
export type PaymentStatus = 'pending' | 'paid' | 'failed';
export type OrderQuery = { page?: number; paymentStatus?: PaymentStatus };
export type OrderInput = (
  | { shippingAddress: ShippingAddress; addressId?: never }
  | { addressId: number; shippingAddress?: never }
) & {
  paymentMethod: 'card' | 'konbini';
  expectedGrandTotal: number;
};
export type OrderReceipt = {
  id: number;
  orderNo: string;
  paymentStatus: string;
  itemsTotal: number;
  shippingTotal: number;
  grandTotal: number;
  checkoutUrl: string;
  expiresAt: string;
};
