import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth";
import { handleError } from "@/lib/errors";
import { documentSchema } from "@/lib/validations";
import { ingestDocument } from "@/lib/rag/ingest";

export const maxDuration = 60;

/** Add a knowledge-base document (staff only): chunk → embed → store. */
export async function POST(req: Request) {
  try {
    const user = await requireRole(["ADMIN", "AGENT"]);
    const body = documentSchema.parse(await req.json());
    const result = await ingestDocument({ userId: user.id, mimeType: "text/markdown", ...body });
    return Response.json(result, { status: 201 });
  } catch (err) {
    return handleError(err);
  }
}

export async function GET() {
  try {
    await requireRole(["ADMIN", "AGENT"]);
    const documents = await db.document.findMany({
      orderBy: { createdAt: "desc" },
      select: { id: true, title: true, source: true, status: true, createdAt: true, _count: { select: { chunks: true } } },
    });
    return Response.json({ documents });
  } catch (err) {
    return handleError(err);
  }
}
