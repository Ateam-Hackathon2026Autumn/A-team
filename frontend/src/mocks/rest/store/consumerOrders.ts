import type { OrderDetail, OrderInput, OrderReceipt } from '../../../types/consumerOrder';
import type { ProductDetail } from '../../../types/publicProduct';
import type { MockResult } from '../../types';
import { refreshMockCart, mockCartBody } from '../endpoint/get_api_v1_cart';
import { productDetail } from '../endpoint/get_api_v1_products_productId';
import { consumerShippingGroups } from '../../../utils/consumerCheckout';
export const consumerDemoOrders: OrderDetail[] = [];
const receipts = new Map<string, { input: string; result: MockResult }>();
export function createDemoConsumerOrder(_url: URL, init?: RequestInit): MockResult {
 const fail = (status: number, errorMsg: string): MockResult => ({ status, body: { errorMsg } });
 const key = new Headers(init?.headers).get('Idempotency-Key');
 const text = String(init?.body ?? '');
 if (!key) return fail(400, '二重送信防止キーがありません。');
 const previous = receipts.get(key);
 if (previous) return previous.input === text ? previous.result : fail(409, '入力内容が変わりました。もう一度確認してください。');
 let input: OrderInput;
 try { input = JSON.parse(text) as OrderInput; } catch { return fail(400, '入力内容を確認してください。'); }
 const address = input?.shippingAddress;
 if (!address || !['lastName', 'firstName', 'postalCode', 'prefecture', 'city', 'addressLine1', 'phone'].every(key => typeof address[key as keyof typeof address] === 'string' && address[key as keyof typeof address].trim()) || !/^0[0-9]{9,10}$/.test(address.phone.replace(/-/g, '')) || !/^[0-9]{3}-?[0-9]{4}$/.test(address.postalCode) || input.paymentMethod !== 'card') return fail(400, 'お届け先とお支払い方法を確認してください。');
 const cart = refreshMockCart();
 if (!cart.canCheckout || input.quoteToken !== cart.quoteToken) return fail(409, 'カートの内容が変更されました。カートからやり直してください。');
 const products = cart.items.map(item => productDetail.handler!(new URL(`/api/v1/products/${item.productId}`, 'https://mock.local')).body as ProductDetail);
 const groups = consumerShippingGroups(cart, products);
 const shippingTotal = groups.reduce((sum, group) => sum + group.shippingFee, 0);
 if (input.expectedGrandTotal !== cart.itemsTotal + shippingTotal) return fail(409, '金額が変わりました。カートからやり直してください。');
 const id = 2000 + consumerDemoOrders.length;
 const { lastName, firstName, ...shippingAddress } = input.shippingAddress;
 const order: OrderDetail = {
 id, orderNo: `TM-${id}`, paymentStatus: 'pending', paymentMethod: input.paymentMethod,
 itemsTotal: cart.itemsTotal, shippingTotal, grandTotal: cart.itemsTotal + shippingTotal,
 orderedAt: new Date().toISOString(), shippingAddress: { ...shippingAddress, name: `${lastName} ${firstName}` },
 shipments: groups.map((group, index) => ({ id: id * 10 + index, producer: { id: group.producerId, businessName: group.producerName }, temperatureZone: group.temperatureZone, status: 'unshipped', shippingFee: group.shippingFee, trackingNo: null,
 items: cart.items.filter(item => { const product = products.find(p => p.id === item.productId)!; return product.producer.id === group.producerId && product.shipping.temperatureZone === group.temperatureZone; }).map(item => ({ id: item.id, productId: item.productId, productName: item.productName ?? '商品', quantity: item.quantity, subtotal: item.subtotal ?? 0 })),
 })),
 };
 consumerDemoOrders.unshift(order);
 mockCartBody.items = []; refreshMockCart(true);
 const receipt: OrderReceipt = { ...order, checkoutUrl: `/checkout/complete?orderId=${id}`, expiresAt: new Date(Date.now() + 1800000).toISOString() };
 const result = { status: 201, body: receipt };
 receipts.set(key, { input: text, result });
 return result;
}
