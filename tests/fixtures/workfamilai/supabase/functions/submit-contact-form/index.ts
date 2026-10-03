import { serve } from "https://deno.land/std@0.190.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface ContactFormData {
  name: string;
  email: string;
  company: string;
  interest: string;
  message: string;
  honeypot?: string;
}

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const resendApiKey = Deno.env.get('RESEND_API_KEY');
const slackWebhook = Deno.env.get('SLACK_WEBHOOK_URL');
const discordWebhook = Deno.env.get('DISCORD_WEBHOOK_URL');

// Use service role key to bypass RLS for contact submissions
const supabase = createClient(supabaseUrl, supabaseServiceKey);

// Only initialize Resend if API key is available
let resend: any = null;
if (resendApiKey) {
  const { Resend } = await import("npm:resend@2.0.0");
  resend = new Resend(resendApiKey);
  console.log('✓ Resend email notifications enabled');
} else {
  console.log('⚠ Resend not configured - email notifications disabled');
}

// Rate limiting
const rateLimits = new Map<string, number[]>();

const SPAM_PATTERNS = [
  /\b(viagra|cialis|casino|lottery|winner|click here|buy now|forex|crypto|investment opportunity)\b/i,
  /http[s]?:\/\/[^\s]{50,}/i,
  /(.)\1{15,}/,
  /<script|javascript:|onclick|onerror/i,
];

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const windowMs = 60 * 60 * 1000; // 1 hour
  const maxRequests = 3;

  if (!rateLimits.has(ip)) {
    rateLimits.set(ip, []);
  }

  const requests = rateLimits.get(ip)!;
  const recentRequests = requests.filter(time => now - time < windowMs);
  
  if (recentRequests.length >= maxRequests) {
    return false;
  }

  recentRequests.push(now);
  rateLimits.set(ip, recentRequests);
  return true;
}

function containsSpam(text: string): boolean {
  return SPAM_PATTERNS.some(pattern => pattern.test(text));
}

const handler = async (req: Request): Promise<Response> => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { 
        status: 405, 
        headers: { 'Content-Type': 'application/json', ...corsHeaders } 
      }
    );
  }

  try {
    const clientIP = req.headers.get('cf-connecting-ip') || 
                    req.headers.get('x-forwarded-for') || 
                    'unknown';

    if (!checkRateLimit(clientIP)) {
      console.log(`❌ Rate limit exceeded: ${clientIP}`);
      return new Response(
        JSON.stringify({ error: 'Too many requests. Please try again in an hour.' }),
        { 
          status: 429, 
          headers: { 'Content-Type': 'application/json', ...corsHeaders } 
        }
      );
    }

    const formData: ContactFormData = await req.json();

    // Input validation
    if (!formData.name || formData.name.trim().length === 0) {
      return new Response(
        JSON.stringify({ error: 'Name is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    if (formData.name.length > 100) {
      return new Response(
        JSON.stringify({ error: 'Name too long (max 100 characters)' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    if (!formData.email || formData.email.trim().length === 0) {
      return new Response(
        JSON.stringify({ error: 'Email is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    if (formData.email.length > 255) {
      return new Response(
        JSON.stringify({ error: 'Email too long (max 255 characters)' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    if (!formData.message || formData.message.trim().length === 0) {
      return new Response(
        JSON.stringify({ error: 'Message is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    if (formData.message.length > 5000) {
      return new Response(
        JSON.stringify({ error: 'Message too long (max 5000 characters)' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    if (formData.company && formData.company.length > 200) {
      return new Response(
        JSON.stringify({ error: 'Company name too long (max 200 characters)' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    // Honeypot check
    if (formData.honeypot && formData.honeypot.trim() !== '') {
      console.log('🍯 Honeypot triggered - blocking spam');
      return new Response(
        JSON.stringify({ error: 'Invalid submission' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    // Spam detection
    if (containsSpam(formData.message) || containsSpam(formData.name) || (formData.company && containsSpam(formData.company))) {
      console.log(`🚫 Spam detected: ${formData.email}`);
      return new Response(
        JSON.stringify({ error: 'Message rejected due to spam detection' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    if (!formData.interest) {
      return new Response(
        JSON.stringify({ error: 'Area of interest is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      return new Response(
        JSON.stringify({ error: 'Invalid email format' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    console.log(`📝 Processing submission: ${formData.email}`);

    // Store in database
    const { error: dbError } = await supabase
      .from('contact_submissions')
      .insert([
        {
          name: formData.name.trim(),
          email: formData.email.toLowerCase().trim(),
          company: formData.company?.trim() || null,
          inquiry_type: formData.interest,
          message: formData.message.trim(),
          ip_address: clientIP,
          status: 'new'
        }
      ]);

    if (dbError) {
      console.error('❌ Database error:', {
        code: dbError.code,
        message: dbError.message,
        details: dbError.details,
        hint: dbError.hint
      });
      return new Response(
        JSON.stringify({ error: 'Failed to store submission' }),
        { 
          status: 500, 
          headers: { 'Content-Type': 'application/json', ...corsHeaders } 
        }
      );
    }

    console.log(`✓ Stored in database: ${formData.email}`);

    // Send notifications (non-blocking)
    const interestLabels: Record<string, string> = {
      'enterprise': 'Enterprise Solutions',
      'partnership': 'Partnership Opportunities', 
      'demo': 'Live Demo Access',
      'integration': 'AI Agent Integration',
      'consultation': 'Strategic Consultation',
      'other': 'Other Inquiry'
    };

    const notifications: Promise<void>[] = [];

    // Email notification
    if (resend) {
      const emailHtml = `
        <h2>New Contact Form Submission - workfamilyai</h2>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
          <h3>Contact Details</h3>
          <p><strong>Name:</strong> ${formData.name}</p>
          <p><strong>Email:</strong> ${formData.email}</p>
          <p><strong>Company:</strong> ${formData.company || 'Not provided'}</p>
          <p><strong>Area of Interest:</strong> ${interestLabels[formData.interest] || formData.interest}</p>
        </div>
        <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
          <h3>Message</h3>
          <p style="white-space: pre-wrap;">${formData.message}</p>
        </div>
        <div style="background: #f1f8e9; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 14px;">
          <p><strong>Timestamp:</strong> ${new Date().toLocaleString()}</p>
          <p><strong>IP Address:</strong> ${clientIP}</p>
        </div>
      `;

      notifications.push(
        resend.emails.send({
          from: 'WorkFamily AI <noreply@workfamilyai.org>',
          to: ['info@workfamilyai.org', 'troy@workfamilyai.org'],
          subject: `New Contact: ${formData.name} - ${interestLabels[formData.interest] || formData.interest}`,
          html: emailHtml,
        })
        .then(() => console.log('✓ Email sent'))
        .catch((err: Error) => console.error('✗ Email failed:', err.message))
      );
    }

    // Slack notification
    if (slackWebhook) {
      notifications.push(
        fetch(slackWebhook, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: `🔔 New Contact Form Submission`,
            blocks: [{
              type: "section",
              text: {
                type: "mrkdwn",
                text: `*New Contact*\n*Name:* ${formData.name}\n*Email:* ${formData.email}\n${formData.company ? `*Company:* ${formData.company}\n` : ''}*Interest:* ${interestLabels[formData.interest]}\n*Message:* ${formData.message}`
              }
            }]
          })
        })
        .then(() => console.log('✓ Slack sent'))
        .catch((err: Error) => console.error('✗ Slack failed:', err.message))
      );
    }

    // Discord notification
    if (discordWebhook) {
      notifications.push(
        fetch(discordWebhook, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            embeds: [{
              title: "🔔 New Contact Form Submission",
              color: 0x00ff00,
              fields: [
                { name: "Name", value: formData.name, inline: true },
                { name: "Email", value: formData.email, inline: true },
                ...(formData.company ? [{ name: "Company", value: formData.company, inline: true }] : []),
                { name: "Interest", value: interestLabels[formData.interest], inline: false },
                { name: "Message", value: formData.message.substring(0, 1024), inline: false }
              ],
              timestamp: new Date().toISOString()
            }]
          })
        })
        .then(() => console.log('✓ Discord sent'))
        .catch((err: Error) => console.error('✗ Discord failed:', err.message))
      );
    }

    // Fire notifications but don't wait for them
    if (notifications.length > 0) {
      Promise.allSettled(notifications);
    }

    return new Response(
      JSON.stringify({ 
        success: true, 
        message: 'Contact form submitted successfully' 
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      }
    );

  } catch (error: any) {
    console.error('❌ Error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      }
    );
  }
};

serve(handler);
