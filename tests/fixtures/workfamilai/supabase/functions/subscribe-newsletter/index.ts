import { serve } from "https://deno.land/std@0.190.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.10";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

interface SubscribeRequest {
  email: string;
  source?: string;
  courseInterests?: {
    categories?: string[];
    courses?: string[];
  };
  metadata?: Record<string, any>;
}

const handler = async (req: Request): Promise<Response> => {
  // Handle CORS preflight requests
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const { email, source = "free-courses", courseInterests, metadata }: SubscribeRequest = await req.json();

    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
      return new Response(
        JSON.stringify({ error: "Invalid email address" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        }
      );
    }

    console.log("Newsletter subscription request:", { email, source });

    // Check if email already exists
    const { data: existing, error: checkError } = await supabase
      .from("newsletter_subscriptions")
      .select("id, is_active")
      .eq("email", email)
      .single();

    if (checkError && checkError.code !== "PGRST116") {
      console.error("Error checking existing subscription:", checkError);
      throw checkError;
    }

    if (existing) {
      if (existing.is_active) {
        return new Response(
          JSON.stringify({ 
            message: "You're already subscribed!", 
            alreadySubscribed: true 
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json", ...corsHeaders },
          }
        );
      } else {
        // Reactivate subscription
        const { error: updateError } = await supabase
          .from("newsletter_subscriptions")
          .update({ 
            is_active: true,
            course_interests: courseInterests || { categories: [], courses: [] },
            metadata: metadata || {}
          })
          .eq("id", existing.id);

        if (updateError) {
          console.error("Error reactivating subscription:", updateError);
          throw updateError;
        }

        return new Response(
          JSON.stringify({ 
            message: "Welcome back! Your subscription has been reactivated.",
            reactivated: true
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json", ...corsHeaders },
          }
        );
      }
    }

    // Create new subscription
    const { data, error: insertError } = await supabase
      .from("newsletter_subscriptions")
      .insert({
        email,
        source,
        course_interests: courseInterests || { categories: [], courses: [] },
        metadata: metadata || {},
        is_active: true,
      })
      .select()
      .single();

    if (insertError) {
      console.error("Error creating subscription:", insertError);
      throw insertError;
    }

    console.log("Newsletter subscription created successfully:", data.id);

    return new Response(
      JSON.stringify({ 
        message: "Successfully subscribed to AI learning updates!",
        subscribed: true,
        id: data.id
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      }
    );
  } catch (error: any) {
    console.error("Error in subscribe-newsletter function:", error);
    return new Response(
      JSON.stringify({ error: error.message || "Internal server error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      }
    );
  }
};

serve(handler);
