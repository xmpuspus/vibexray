import { db } from "@/lib/db";
import { orders, orderItems, products, customers } from "@/lib/db/schema";
import { eq, or } from "drizzle-orm";
import { jsonError } from "@/lib/validation";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const idOrNumber = params.id;
  const candidate = idOrNumber.toUpperCase().startsWith("ORD-") ? idOrNumber.toUpperCase() : `ORD-${idOrNumber}`;

  const [order] = await db
    .select()
    .from(orders)
    .where(or(eq(orders.id, idOrNumber), eq(orders.orderNumber, candidate), eq(orders.orderNumber, idOrNumber)));

  if (!order) return jsonError("Order not found", 404);

  const [customer] = await db.select().from(customers).where(eq(customers.id, order.customerId));
  const items = await db
    .select({
      quantity: orderItems.quantity,
      unitPrice: orderItems.unitPrice,
      productName: products.name,
    })
    .from(orderItems)
    .leftJoin(products, eq(orderItems.productId, products.id))
    .where(eq(orderItems.orderId, order.id));

  return Response.json({ order, customer, items });
}
