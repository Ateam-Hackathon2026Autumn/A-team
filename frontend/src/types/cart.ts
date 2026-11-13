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

export type Cart = {
  items: CartItem[];
  itemsTotal: number;
  canCheckout: boolean;
  quoteToken: string;
};
