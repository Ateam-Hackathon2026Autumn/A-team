import type { Cart } from '../types/cart';
import type { ProductDetail } from '../types/publicProduct';
export function consumerShippingGroups(cart: Cart, products: ProductDetail[]) {
 const groups = new Map<string, { producerId: number; producerName: string; temperatureZone: string; subtotal: number; shippingFee: number; threshold: number | null }>();
 for (const item of cart.items) {
 const product = products.find(p => p.id === item.productId);
 if (!product) throw new Error('商品情報が変わりました。カートを確認してください。');
 const key = `${product.producer.id}:${product.shipping.temperatureZone}`;
 const current = groups.get(key) ?? { producerId: product.producer.id, producerName: product.producer.businessName, temperatureZone: product.shipping.temperatureZone, subtotal: 0, shippingFee: product.shipping.shippingFee, threshold: product.shipping.freeShippingThreshold };
 current.subtotal += item.subtotal ?? 0;
 current.shippingFee = Math.max(current.shippingFee, product.shipping.shippingFee);
 groups.set(key, current);
 }
 return [...groups.values()].map(group => ({ ...group, shippingFee: group.threshold !== null && group.subtotal >= group.threshold ? 0 : group.shippingFee }));
}
