import { pool } from "@/lib/db";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { OverviewCharts } from "@/components/admin/overview-charts";

/**
 * Server component: queries the same aggregates as /api/analytics/overview
 * directly (avoids a same-origin fetch + auth-cookie dance during SSR) and
 * hands the numbers to a client component for chart rendering.
 */
async function getOverviewData() {
  const [totals] = (
    await pool.query(`
      SELECT
        (SELECT count(*) FROM conversations) as total_conversations,
        (SELECT count(*) FROM conversations WHERE status IN ('AI_HANDLING','RESOLVED')) as ai_resolved,
        (SELECT count(*) FROM conversations WHERE status = 'ESCALATED') as escalated,
        (SELECT count(*) FROM support_tickets WHERE status != 'RESOLVED') as open_tickets,
        (SELECT count(*) FROM knowledge_documents WHERE status = 'INDEXED') as knowledge_documents,
        (SELECT coalesce(avg(latency_ms), 0) FROM agent_runs) as avg_latency_ms
    `)
  ).rows;

  const conversationsPerDay = (
    await pool.query(`
      SELECT to_char(date_trunc('day', created_at), 'Mon DD') as day, count(*) as count
      FROM conversations WHERE created_at > now() - interval '14 days'
      GROUP BY 1, date_trunc('day', created_at) ORDER BY date_trunc('day', created_at)
    `)
  ).rows;

  const resolutionSplit = (
    await pool.query(`SELECT status, count(*) as count FROM conversations GROUP BY status`)
  ).rows;

  const toolUsage = (
    await pool.query(`SELECT tool_name, count(*) as count FROM tool_calls GROUP BY tool_name ORDER BY count DESC`)
  ).rows;

  return {
    totals: {
      totalConversations: Number(totals.total_conversations),
      aiResolved: Number(totals.ai_resolved),
      escalated: Number(totals.escalated),
      openTickets: Number(totals.open_tickets),
      knowledgeDocuments: Number(totals.knowledge_documents),
      avgLatencyMs: Math.round(Number(totals.avg_latency_ms)),
    },
    conversationsPerDay: conversationsPerDay.map((r) => ({ day: r.day, count: Number(r.count) })),
    resolutionSplit: resolutionSplit.map((r) => ({ status: r.status, count: Number(r.count) })),
    toolUsage: toolUsage.map((r) => ({ tool: r.tool_name, count: Number(r.count) })),
  };
}

export default async function AdminOverviewPage() {
  const data = await getOverviewData();
  const resolutionRate =
    data.totals.totalConversations > 0
      ? Math.round((data.totals.aiResolved / data.totals.totalConversations) * 100)
      : 0;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Overview</h1>
          <p className="text-sm text-muted-foreground">Support operations at a glance.</p>
        </div>
        <Badge variant="warning">Demo / sample data</Badge>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Conversations" value={data.totals.totalConversations} />
        <StatCard label="AI Resolution Rate" value={`${resolutionRate}%`} />
        <StatCard label="Human Escalations" value={data.totals.escalated} />
        <StatCard label="Open Tickets" value={data.totals.openTickets} />
        <StatCard label="Knowledge Documents" value={data.totals.knowledgeDocuments} />
        <StatCard label="Avg. Response Time" value={`${data.totals.avgLatencyMs}ms`} />
      </div>

      <OverviewCharts
        conversationsPerDay={data.conversationsPerDay}
        resolutionSplit={data.resolutionSplit}
        toolUsage={data.toolUsage}
      />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
