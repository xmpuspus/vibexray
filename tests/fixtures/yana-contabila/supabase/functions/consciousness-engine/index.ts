        .from('cross_user_insights')
        .select('pattern_type, pattern_description, recommended_response, emotional_approach, success_rate')
        .order('success_rate', { ascending: false })
        .limit(5),
      
      // 5. Self-Model
      supabase
        .from('yana_self_model')
        .select('*')
        .eq('id', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11')
        .maybeSingle(),
      
      // 6. NEW: Active Intentions
      supabase
        .from('yana_intentions')
        .select('id, intention_type, intention, priority, progress_percent, created_at')
