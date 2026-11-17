export type CartItem = {
  id: number;
  productId: number;
  productName: string | null;
  quantity: number;
  unitPrice: number | null;
  subtotal: number | null;
  purchasable: boolean;
  unavailableReason: string | null;
};

export type CartShipment = {
  producerId: number;
  producerName: string;
  temperatureZone: string;
  itemIds: number[];
  itemsTotal: number;
  shippingFee: number;
  freeShippingThreshold: number | null;
};

export type Cart = {
  items: CartItem[];
  shipments: CartShipment[];
  itemsTotal: number;
  shippingTotal: number;
  total: number;
  canCheckout: boolean;
};
