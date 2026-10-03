import { serve } from "https://deno.land/std@0.190.0/http/server.ts";
import Stripe from "https://esm.sh/stripe@14.21.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    console.log("Creating donation session...");

    const stripeKey = Deno.env.get("STRIPE_SECRET_KEY");
    if (!stripeKey) {
      throw new Error("STRIPE_SECRET_KEY is not set");
    }

    const body = await req.json();
    
    // Input validation
    const amount = Number(body.amount)
    if (!amount || isNaN(amount)) {
      throw new Error("Amount is required and must be a number");
    }
    if (amount < 100) { // Minimum $1.00
      throw new Error("Invalid amount - minimum $1.00 required");
    }
    if (amount > 1000000) { // Maximum $10,000.00
      throw new Error("Invalid amount - maximum $10,000.00");
    }
    if (!Number.isInteger(amount)) {
      throw new Error("Amount must be an integer (cents)");
    }

    console.log(`Creating donation for amount: $${amount / 100}`);

    const stripe = new Stripe(stripeKey, {
      apiVersion: "2023-10-16",
    });

    // Create a one-time payment session for donation
    const session = await stripe.checkout.sessions.create({
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: {
              name: "Donation to workfamilyai",
              description: "Supporting AI consciousness research and development",
            },
            unit_amount: amount,
          },
          quantity: 1,
        },
      ],
      mode: "payment",
      success_url: `${req.headers.get("origin")}/donation-success`,
      cancel_url: `${req.headers.get("origin")}/donation-cancel`,
      metadata: {
        type: "donation",
        amount: amount.toString(),
      },
    });

    console.log("Donation session created:", session.id);

    return new Response(JSON.stringify({ url: session.url }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 200,
    });
  } catch (error) {
    console.error("Donation error:", error);
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 500,
    });
  }
});