// Demo data for "Northwind Gear", a fictional outdoor-equipment store.
// In a real deployment these would be calls to the shop database, the carrier API and the CRM.

export type OrderStatus = 'processing' | 'shipped' | 'delivered' | 'cancelled';

export interface OrderItem {
  sku: string;
  name: string;
  qty: number;
  price: number;
}

export interface Order {
  id: string;
  customer: string;
  email: string;
  status: OrderStatus;
  placedAt: string;
  deliveredAt?: string;
  trackingNumber?: string;
  items: OrderItem[];
}

export interface Product {
  sku: string;
  name: string;
  price: number;
  stock: Record<string, number>; // variant -> units
  restockDate?: string;
}

export interface Article {
  id: string;
  title: string;
  body: string;
}

export const orders: Order[] = [
  {
    id: 'A1001',
    customer: 'Maria Lopez',
    email: 'maria.lopez@example.com',
    status: 'shipped',
    placedAt: '2026-09-20',
    trackingNumber: 'TRK-5501',
    items: [{ sku: 'TR2-42', name: 'Trail Runner 2, size 42', qty: 1, price: 129 }],
  },
  {
    id: 'A1002',
    customer: 'James Carter',
    email: 'james.carter@example.com',
    status: 'delivered',
    placedAt: '2026-09-08',
    deliveredAt: '2026-09-12',
    trackingNumber: 'TRK-5502',
    items: [
      { sku: 'ADJ-M', name: 'Alpine Down Jacket, size M', qty: 1, price: 249 },
      { sku: 'MS3', name: 'Merino Socks 3-pack', qty: 1, price: 24 },
    ],
  },
  {
    id: 'A1003',
    customer: 'Aiko Tanaka',
    email: 'aiko.tanaka@example.com',
    status: 'processing',
    placedAt: '2026-09-24',
    items: [{ sku: 'CS-1', name: 'Compact Camp Stove', qty: 1, price: 89 }],
  },
  {
    id: 'A1004',
    customer: 'Liam Novak',
    email: 'liam.novak@example.com',
    status: 'delivered',
    placedAt: '2026-06-28',
    deliveredAt: '2026-07-02',
    trackingNumber: 'TRK-5504',
    items: [{ sku: 'HL-300', name: 'Headlamp HL-300', qty: 2, price: 39 }],
  },
  {
    id: 'A1005',
    customer: 'Sofia Rossi',
    email: 'sofia.rossi@example.com',
    status: 'shipped',
    placedAt: '2026-09-21',
    // The carrier API for this parcel times out on the first attempt (see tools.ts).
    trackingNumber: 'TRK-5505-SLOW',
    items: [{ sku: 'TP-2', name: 'Ultralight Tent, 2 person', qty: 1, price: 319 }],
  },
];

export const shipments: Record<string, { carrier: string; events: { date: string; status: string; location: string }[]; eta?: string }> = {
  'TRK-5501': {
    carrier: 'UPS',
    eta: '2026-09-27',
    events: [
      { date: '2026-09-21', status: 'Label created', location: 'Portland, OR' },
      { date: '2026-09-22', status: 'Picked up', location: 'Portland, OR' },
      { date: '2026-09-24', status: 'In transit', location: 'Sacramento, CA' },
    ],
  },
  'TRK-5502': {
    carrier: 'FedEx',
    events: [
      { date: '2026-09-09', status: 'Picked up', location: 'Portland, OR' },
      { date: '2026-09-12', status: 'Delivered', location: 'Denver, CO' },
    ],
  },
  'TRK-5504': {
    carrier: 'USPS',
    events: [{ date: '2026-07-02', status: 'Delivered', location: 'Austin, TX' }],
  },
  'TRK-5505-SLOW': {
    carrier: 'DHL',
    eta: '2026-09-26',
    events: [
      { date: '2026-09-22', status: 'Picked up', location: 'Portland, OR' },
      { date: '2026-09-25', status: 'Out for delivery', location: 'Seattle, WA' },
    ],
  },
};

export const products: Product[] = [
  { sku: 'TR2', name: 'Trail Runner 2', price: 129, stock: { '40': 3, '41': 0, '42': 5, '43': 2, '44': 0 }, restockDate: '2026-10-03' },
  { sku: 'ADJ', name: 'Alpine Down Jacket', price: 249, stock: { S: 2, M: 0, L: 4, XL: 1 }, restockDate: '2026-10-06' },
  { sku: 'CS-1', name: 'Compact Camp Stove', price: 89, stock: { default: 14 } },
  { sku: 'HL-300', name: 'Headlamp HL-300', price: 39, stock: { default: 0 }, restockDate: '2026-10-02' },
  { sku: 'TP-2', name: 'Ultralight Tent, 2 person', price: 319, stock: { default: 6 } },
  { sku: 'MS3', name: 'Merino Socks 3-pack', price: 24, stock: { default: 40 } },
];

export const articles: Article[] = [
  {
    id: 'returns-policy',
    title: 'Returns and refunds',
    body: 'Items can be returned within 30 days of delivery if unworn and in original packaging. Refunds go to the original payment method within 5-7 business days after the return is received. Return shipping is free for store credit and $6.95 for a card refund.',
  },
  {
    id: 'exchanges',
    title: 'Exchanges and size changes',
    body: 'Size exchanges are free within 30 days of delivery. If the new size is out of stock we issue a refund or store credit instead.',
  },
  {
    id: 'shipping-times',
    title: 'Shipping times',
    body: 'Orders ship within 1-2 business days. Standard delivery takes 3-5 business days in the continental US, express takes 1-2 business days.',
  },
  {
    id: 'warranty',
    title: 'Warranty',
    body: 'All gear has a 2-year warranty against manufacturing defects. Normal wear and accidental damage are not covered. Warranty claims need the order number and a photo of the defect.',
  },
  {
    id: 'cancellations',
    title: 'Cancelling an order',
    body: 'Orders can be cancelled free of charge while their status is "processing". Once shipped, the order has to be returned instead.',
  },
];

// Phone callback slots offered by the support team, as "YYYY-MM-DD HH:MM".
export const bookedSlots = new Set<string>(['2026-09-26 10:00', '2026-09-26 14:00']);
export const slotTimes = ['10:00', '11:30', '14:00', '16:30'];
