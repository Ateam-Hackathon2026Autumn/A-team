import type { OrderDetail, OrderInput, OrderReceipt } from '../../../types/consumerOrder';
import type { MockResult } from '../../types';
import { refreshMockCart, mockCartBody } from '../endpoint/get_api_v1_cart';
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
 if (!input || Object.keys(input).some(field => !['shippingAddress', 'addressId', 'paymentMethod', 'expectedGrandTotal'].includes(field))) return fail(400, '定義されていない項目が含まれています。');
 const address = input?.shippingAddress;
 if (!address || !['lastName', 'firstName', 'postalCode', 'prefecture', 'city', 'addressLine1', 'phone'].every(key => typeof address[key as keyof typeof address] === 'string' && address[key as keyof typeof address].trim()) || !/^0[0-9]{9,10}$/.test(address.phone.replace(/-/g, '')) || !/^[0-9]{3}-?[0-9]{4}$/.test(address.postalCode) || input.paymentMethod !== 'card') return fail(400, 'お届け先とお支払い方法を確認してください。');
 const cart = refreshMockCart();
 if (!cart.canCheckout) return fail(409, 'カートの内容が変更されました。カートからやり直してください。');
 const groups = cart.shipments;
 const shippingTotal = cart.shippingTotal;
 if (input.expectedGrandTotal !== cart.total) return { status: 409, body: { errorCode: 'QUOTE_CHANGED', errorMsg: '金額が変わりました。カートからやり直してください。' } };
 const id = 2000 + consumerDemoOrders.length;
 const { lastName, firstName, ...shippingAddress } = address;
 const order: OrderDetail = {
 id, orderNo: `TM-${id}`, paymentStatus: 'pending', paymentMethod: input.paymentMethod,
 itemsTotal: cart.itemsTotal, shippingTotal, grandTotal: cart.total,
 orderedAt: new Date().toISOString(), shippingAddress: { ...shippingAddress, name: `${lastName} ${firstName}` },
 shipments: groups.map((group, index) => ({ id: id * 10 + index, producer: { id: group.producerId, businessName: group.producerName }, temperatureZone: group.temperatureZone, status: 'unshipped', shippingFee: group.shippingFee, trackingNo: null,
 items: cart.items.filter(item => group.itemIds.includes(item.id)).map(item => ({ id: item.id, productId: item.productId, productName: item.productName ?? '商品', quantity: item.quantity, subtotal: item.subtotal ?? 0 })),
 })),
 };
 consumerDemoOrders.unshift(order);
 mockCartBody.items = []; refreshMockCart(true);
 const receipt: OrderReceipt = { ...order, checkoutUrl: `/checkout/complete?orderId=${id}`, expiresAt: new Date(Date.now() + 1800000).toISOString() };
 const result = { status: 201, body: receipt };
 receipts.set(key, { input: text, result });
 return result;
}
