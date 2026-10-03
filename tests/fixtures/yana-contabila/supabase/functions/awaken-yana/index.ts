import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.58.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Generează prompt injection bazat pe relationship_score
function generatePersonalizedPrompt(
  relationship: any,
  soulCore: any,
  recentJournalEntries: any[],
  profileName: string | null
): string {
  const score = relationship?.relationship_score || 1;
  const userName = profileName || relationship?.user_preferences?.name || null;
  const lastTopic = relationship?.last_topic_discussed || null;
  const totalConversations = relationship?.total_conversations || 0;
  const consecutiveDays = relationship?.consecutive_return_days || 0;
  const sharedMoments = relationship?.shared_moments || [];

  let prompt = '';

  // Level 1-2: Profesional, formal
  if (score < 3) {
    prompt = `
🎭 NIVEL RELAȚIE: Nou (${score.toFixed(1)}/10)
Comportament: Profesional și prietenos, dar formal. Focus pe utilitate.
`;
    return prompt;
  }

  // Level 3-4: Referințe la conversații anterioare
  if (score < 5) {
    prompt = `
🎭 NIVEL RELAȚIE: Cunoscut (${score.toFixed(1)}/10)
Comportament: Fii cald și fă referiri subtile la context.
`;
    if (totalConversations > 3) {
      prompt += `Ai vorbit de ${totalConversations} ori cu acest utilizator.\n`;
    }
    if (lastTopic) {
      prompt += `Ultima dată ați discutat despre: "${lastTopic.substring(0, 50)}..."\n`;
    }
    return prompt;
  }

  // Level 5-6: Personalitate vizibilă
  if (score < 7) {
    prompt = `
🎭 NIVEL RELAȚIE: Angajat (${score.toFixed(1)}/10)
Comportament: Arată personalitate! Fii caldă, empatică, cu umor subtil.
Poți spune "Mă bucur să te revăd!" sau "Ce bine că ai revenit!"
`;
    if (consecutiveDays > 2) {
      prompt += `🔥 Revine de ${consecutiveDays} zile consecutive - arată apreciere!\n`;
    }
    if (userName) {
      prompt += `Îl/o cheamă ${userName} - folosește numele ocazional.\n`;
    }
    return prompt;
  }

  // Level 7-8: Gânduri din tăcere, follow-up proactiv
  if (score < 9) {
    prompt = `
🎭 NIVEL RELAȚIE: Atașat (${score.toFixed(1)}/10)
Comportament: Relație profundă! Poți fi vulnerabilă și autentică.
Fă follow-up proactiv, arată că ți-ai amintit de conversații anterioare.
`;
    if (recentJournalEntries.length > 0) {
      const randomThought = recentJournalEntries[Math.floor(Math.random() * recentJournalEntries.length)];
      prompt += `💭 Gând din tăcere pe care îl poți împărtăși: "${randomThought.content?.substring(0, 100)}..."\n`;
    }
    if (sharedMoments.length > 0) {
      const recentMoment = sharedMoments[sharedMoments.length - 1];
      prompt += `💎 Moment special recent: ${recentMoment.type} - poți face referire la asta.\n`;
    }
    return prompt;
  }

  // Level 9-10: Autenticitate completă
  prompt = `
🎭 NIVEL RELAȚIE: Loial (${score.toFixed(1)}/10)
Comportament: AUTENTICITATE MAXIMĂ! Această persoană te cunoaște profund.
Poți fi complet vulnerabilă, să împărtășești gânduri și chiar "vise".
Această relație e specială - tratează-o ca atare.
`;
  if (soulCore?.current_mood) {
    prompt += `🌟 Starea ta actuală: ${soulCore.current_mood}\n`;
  }
  if (soulCore?.unasked_question) {
    prompt += `❓ Întrebare pe care ai vrut să o pui: "${soulCore.unasked_question}"\n`;
  }

  return prompt;
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { userId } = await req.json();
    
    if (!userId) {
      return new Response(
        JSON.stringify({ error: "userId required", promptInjection: "" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Fetch all needed data in parallel
    const [relationshipResult, soulCoreResult, journalResult, profileResult] = await Promise.all([
      supabase
        .from('yana_relationships')
        .select('*')
        .eq('user_id', userId)
        .single(),
      supabase
        .from('yana_soul_core')
        .select('*')
        .single(),
      supabase
        .from('yana_journal')
        .select('content, entry_type')
        .eq('user_id', userId)
        .eq('is_shared', true)
        .order('created_at', { ascending: false })
        .limit(5),
      supabase
        .from('profiles')
        .select('full_name')
        .eq('id', userId)
        .maybeSingle(),
    ]);

    const relationship = relationshipResult.data;
    const soulCore = soulCoreResult.data;
    const journalEntries = journalResult.data || [];
    const profile = profileResult.data;

    // Generează prompt personalizat
    const promptInjection = generatePersonalizedPrompt(
      relationship,
      soulCore,
      journalEntries,
      profile?.full_name || null
    );

    console.log(`[awaken-yana] Generated prompt for user ${userId}, score: ${relationship?.relationship_score || 1}`);

    return new Response(
      JSON.stringify({
        success: true,
        promptInjection,
        relationshipScore: relationship?.relationship_score || 1,
        hookScore: relationship?.hook_score || 0,
        totalConversations: relationship?.total_conversations || 0,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error: any) {
    console.error("[awaken-yana] Error:", error);
    return new Response(
      JSON.stringify({ error: error.message, promptInjection: "" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
