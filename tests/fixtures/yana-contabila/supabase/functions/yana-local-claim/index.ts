/**
 * yana-local-claim — agentul local schimbă pairing_code pe device_token
 *
 * Public endpoint (no JWT). Body: { pairing_code, os_info }
 * Response: { device_token, device_id }
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders } from "../_shared/cors.ts";

const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseService = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

function genToken(): string {
  const arr = new Uint8Array(32);
  crypto.getRandomValues(arr);
  return Array.from(arr).map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const body = await req.json();
    const code = String(body.pairing_code || "").trim();
    const osInfo = String(body.os_info || "unknown");

    if (!/^\d{6}$/.test(code)) {
      return new Response(JSON.stringify({ error: "Invalid pairing code format" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const admin = createClient(supabaseUrl, supabaseService);

    const { data: device, error } = await admin
      .from("yana_local_devices")
      .select("id, status, pairing_code_expires_at")
      .eq("pairing_code", code)
      .eq("status", "pending")
      .maybeSingle();

    if (error || !device) {
      return new Response(JSON.stringify({ error: "Pairing code invalid sau expirat" }), {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (device.pairing_code_expires_at && new Date(device.pairing_code_expires_at as string) < new Date()) {
      return new Response(JSON.stringify({ error: "Pairing code expirat" }), {
        status: 410,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const token = genToken();
    const { error: upErr } = await admin
      .from("yana_local_devices")
      .update({
        device_token: token,
        status: "active",
        os_info: osInfo,
        pairing_code: null,
        pairing_code_expires_at: null,
        last_seen_at: new Date().toISOString(),
      })
      .eq("id", device.id);

    if (upErr) {
      return new Response(JSON.stringify({ error: upErr.message }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(
      JSON.stringify({
        device_id: device.id,
        device_token: token,
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});