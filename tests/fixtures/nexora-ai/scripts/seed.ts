import { db } from "@/lib/db";
import { DEMO_PASSWORD, seedDemoCustomers, seedKnowledgeBase } from "@/lib/seed-data";

/** Knowledge base always; demo accounts only outside production (or with SEED_DEMO_DATA=1). Safe to re-run. */
async function main() {
  if (process.env.NODE_ENV !== "production" || process.env.SEED_DEMO_DATA === "1") {
    const d = await seedDemoCustomers();
    console.log(`✓ demo data: admin@example.com (ADMIN), alice@/bob@example.com, ${d.orders} orders — password ${DEMO_PASSWORD}`);
  } else console.log("• skipped demo accounts (production). Create your first admin with: npm run admin:promote -- you@example.com");
  for (const k of await seedKnowledgeBase()) console.log(`✓ ${k.title} (${k.chunks} chunks)`);
}

main().catch((e) => { console.error(e); process.exit(1); }).finally(() => db.$disconnect());
