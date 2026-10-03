      const uniqueActiveUsers = new Set(activeUsersData?.map(e => e.user_id)).size;

      // Calculate infrastructure costs
      const baseInfrastructure = 50;
      const perUserCost = 2;
      const estimatedInfrastructure = baseInfrastructure + (uniqueActiveUsers * perUserCost);

      // Calculate daily costs for chart (last 30 days)
      const dailyCosts: { [key: string]: { cost: number; requests: number } } = {};
      aiUsage?.forEach(record => {
        const date = record.created_at.slice(0, 10);
        if (!dailyCosts[date]) {
          dailyCosts[date] = { cost: 0, requests: 0 };
        }
        dailyCosts[date].cost += record.estimated_cost_cents || 0;
        dailyCosts[date].requests += 1;
      });

      const dailyArray: DailyConsumption[] = Object.entries(dailyCosts)
        .map(([date, data]) => ({
          date,
