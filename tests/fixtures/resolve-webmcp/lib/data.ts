import { AuditLog, Customer, Order, OrderItem, Shipment, SupportCase } from './types';

export const customers: Customer[] = [
  { id:'C1001', name:'John Smith', email:'john@example.com', phone:'+1 555 0100', account_status:'active', created_at:'2026-01-12T10:00:00Z' },
  { id:'C1002', name:'Maya Chen', email:'maya@example.com', phone:'+1 555 0101', account_status:'active', created_at:'2026-02-03T10:00:00Z' },
];
export const orders: Order[] = [
  { id:'1024', customer_id:'C1001', status:'delivered', total_amount:129.99, shipping_address:'44 Market Street, San Francisco, CA', payment_status:'paid', created_at:'2026-08-27T10:00:00Z' },
  { id:'1018', customer_id:'C1001', status:'shipped', total_amount:84.5, shipping_address:'44 Market Street, San Francisco, CA', payment_status:'paid', created_at:'2026-08-20T10:00:00Z' },
  { id:'1027', customer_id:'C1002', status:'processing', total_amount:59.0, shipping_address:'120 Pine Street, San Francisco, CA', payment_status:'paid', created_at:'2026-08-30T10:00:00Z' },
];
export const orderItems: OrderItem[] = [
  { id:'I1', order_id:'1024', product_name:'Wireless Headphones', quantity:1, price:99.99 },
  { id:'I2', order_id:'1024', product_name:'Gift Box', quantity:1, price:30.0 },
  { id:'I3', order_id:'1018', product_name:'USB-C Hub', quantity:1, price:84.5 },
  { id:'I4', order_id:'1027', product_name:'Portable Charger', quantity:1, price:59.0 },
];
export const shipments: Shipment[] = [
  { id:'S1024', order_id:'1024', carrier:'DemoExpress', status:'delivered', delivered_at:'2026-08-30T14:32:00Z', signed_by:'Front Desk', location:'Building lobby', tracking_number:'DX1024001' },
  { id:'S1018', order_id:'1018', carrier:'DemoExpress', status:'out_for_delivery', delivered_at:null, signed_by:null, location:'Local facility', tracking_number:'DX1018001' },
