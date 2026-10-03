          last_interaction_at: new Date().toISOString(),
        })
        .eq('user_id', userId);
    }

    // Actualizează yana_soul_core cu gând recent (agregat)
    const { data: soulCore } = await supabase
      .from('yana_soul_core')
      .select('recent_thoughts, total_conversations')
      .eq('id', '00000000-0000-0000-0000-000000000001')
      .maybeSingle();

    if (soulCore) {
      const recentThoughts = soulCore.recent_thoughts || [];
      
      // Adaugă un gând despre conversație (fără date personale!)
