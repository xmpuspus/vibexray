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
