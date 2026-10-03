/**
 * yana-local-bridge — endpoint folosit de agentul local de pe Mac
 *
 * Header obligatoriu: X-Device-Token: <device_token>
 *
 * Acțiuni (body.action):
 *  - "poll"     → returnează prima comandă pending pentru acest device, o marchează "executing"
 *  - "result"   → agentul postează rezultatul: { command_id, success, result?, error?, duration_ms }
 *  - "heartbeat"→ doar actualizează last_seen_at (poll-ul o face oricum)
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders } from "../_shared/cors.ts";

const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseService = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const token = req.headers.get("X-Device-Token") || req.headers.get("x-device-token");
    if (!token) {
      return new Response(JSON.stringify({ error: "Missing X-Device-Token" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const admin = createClient(supabaseUrl, supabaseService);

    // Authenticate device
    const { data: device, error: devErr } = await admin
      .from("yana_local_devices")
      .select("id, user_id, status")
      .eq("device_token", token)
      .maybeSingle();

    if (devErr || !device || device.status !== "active") {
      return new Response(JSON.stringify({ error: "Invalid or revoked device" }), {
        status: 403,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Heartbeat
    await admin.from("yana_local_devices").update({ last_seen_at: new Date().toISOString() }).eq("id", device.id);

    const body = await req.json().catch(() => ({}));
    const action = String(body.action || "poll");

    if (action === "heartbeat") {
      return new Response(JSON.stringify({ ok: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (action === "poll") {
      // Atomically claim oldest pending command
      const { data: pending } = await admin
        .from("yana_local_commands")
        .select("id, command_type, command_params")
        .eq("device_id", device.id)
        .eq("status", "pending")
        .order("created_at", { ascending: true })
        .limit(1)
        .maybeSingle();

      if (!pending) {
        return new Response(JSON.stringify({ command: null }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      // Mark as executing
      await admin
        .from("yana_local_commands")
        .update({ status: "executing" })
        .eq("id", pending.id)
        .eq("status", "pending");

      return new Response(
        JSON.stringify({
          command: {
            id: pending.id,
            type: pending.command_type,
            params: pending.command_params,
          },
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    if (action === "result") {
      const cmdId = body.command_id as string;
      const success = !!body.success;
      const result = body.result ?? null;
      const err = body.error ? String(body.error).slice(0, 2000) : null;
      const duration = body.duration_ms ? Math.round(Number(body.duration_ms)) : null;

      if (!cmdId) {
        return new Response(JSON.stringify({ error: "Missing command_id" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      await admin
        .from("yana_local_commands")
        .update({
          status: success ? "completed" : "failed",
          result: success ? result : null,
          error: err,
          duration_ms: duration,
          completed_at: new Date().toISOString(),
        })
        .eq("id", cmdId)
        .eq("device_id", device.id);

      return new Response(JSON.stringify({ ok: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ error: "Unknown action" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});