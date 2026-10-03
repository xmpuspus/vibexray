import { z } from "zod";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth";
import { AppError, handleError } from "@/lib/errors";

const patchSchema = z
  .object({
    status: z.enum(["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]).optional(),
    priority: z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]).optional(),
  })
  .strict()
  .refine((v) => v.status || v.priority, "Nothing to update");

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    await requireRole(["ADMIN", "AGENT"]);
    const { id } = await params;
    if (!z.string().uuid().safeParse(id).success) throw new AppError(404, "NOT_FOUND", "Ticket not found.");
    const data = patchSchema.parse(await req.json());
    const ticket = await db.supportTicket.update({ where: { id }, data, select: { id: true, status: true, priority: true } });
    return Response.json({ ticket });
  } catch (err) {
    return handleError(err);
  }
}
