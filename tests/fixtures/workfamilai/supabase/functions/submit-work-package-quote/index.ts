import { serve } from "https://deno.land/std@0.190.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.10";
import { Resend } from "npm:resend@2.0.0";
import { z } from "https://deno.land/x/zod@v3.22.4/mod.ts";

const resend = new Resend(Deno.env.get("RESEND_API_KEY"));

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Rate limiting
const rateLimits = new Map<string, number[]>();

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const windowMs = 60 * 60 * 1000; // 1 hour
  const maxRequests = 3; // 3 quotes per hour
  
  const requests = rateLimits.get(ip) || [];
  const recentRequests = requests.filter(time => now - time < windowMs);
  
  if (recentRequests.length >= maxRequests) {
    return false;
  }
  
  recentRequests.push(now);
  rateLimits.set(ip, recentRequests);
  return true;
}

// Server-side validation schema
const quoteRequestSchema = z.object({
  workPackageId: z.string().trim().min(1).max(100),
  workPackageName: z.string().trim().min(1).max(200),
  name: z.string().trim().min(1).max(100),
  email: z.string().trim().email().max(255),
  phone: z.string().trim().min(10).max(20).optional(),
  jobTitle: z.string().trim().max(100).optional(),
  companyName: z.string().trim().min(1).max(200),
  companySize: z.string().trim().max(50).optional(),
  industry: z.string().trim().max(100).optional(),
  primaryLocation: z.string().trim().max(200).optional(),
  hasMultipleLocations: z.boolean().optional(),
  orgMaturityLevel: z.string().trim().max(50).optional(),
  pricingTierInterest: z.string().trim().max(50).optional(),
  preferredTimeline: z.string().trim().max(100).optional(),
  budgetRange: z.string().trim().max(100).optional(),
  challengeDescription: z.string().trim().max(2000).optional(),
  currentStateDescription: z.string().trim().max(2000).optional(),
  successCriteria: z.string().trim().max(1000).optional(),
  complianceRequirements: z.string().trim().max(1000).optional(),
  existingSystems: z.array(z.string()).max(20).optional(),
  cloudEnvironment: z.string().trim().max(100).optional(),
  dataClassification: z.string().trim().max(100).optional(),
  integrationRequirements: z.string().trim().max(1000).optional(),
  authMethod: z.string().trim().max(100).optional(),
  numberOfUsers: z.number().int().min(1).max(1000000).optional(),
  departmentsInvolved: z.array(z.string()).max(50).optional(),
  decisionMakers: z.string().trim().max(500).optional(),
  internalChampion: z.string().trim().max(200).optional(),
  implementationTeamSize: z.number().int().min(0).max(10000).optional(),
  primaryKpis: z.array(z.string()).max(20).optional(),
  expectedRoiTimeline: z.string().trim().max(100).optional(),
  knownConstraints: z.string().trim().max(1000).optional(),
  previousExperience: z.boolean().optional(),
  previousExperienceDetails: z.string().trim().max(1000).optional(),
  referralSource: z.string().trim().max(200).optional(),
  preferredContactMethod: z.string().trim().max(50).optional(),
  bestTimeToContact: z.string().trim().max(200).optional(),
  additionalInfo: z.string().trim().max(2000).optional(),
});

type WorkPackageQuoteRequest = z.infer<typeof quoteRequestSchema>;

const handler = async (req: Request): Promise<Response> => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // Rate limiting
    const clientIP = req.headers.get('cf-connecting-ip') || 
                     req.headers.get('x-forwarded-for') || 
                     'unknown';
    
    if (!checkRateLimit(clientIP)) {
      console.log(`Rate limit exceeded for IP: ${clientIP}`);
      return new Response(
        JSON.stringify({ error: 'Too many quote requests. Please try again in an hour.' }),
        { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const requestBody = await req.json();
    
    // Server-side validation
    const parseResult = quoteRequestSchema.safeParse(requestBody);
    if (!parseResult.success) {
      console.error("Validation failed:", parseResult.error);
      return new Response(
        JSON.stringify({ 
          success: false, 
          error: "Invalid input data", 
          details: parseResult.error.issues 
        }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
    
    const quoteData: WorkPackageQuoteRequest = parseResult.data;
    
    console.log("Received work package quote request:", {
      workPackage: quoteData.workPackageName,
      company: quoteData.companyName,
      email: quoteData.email
    });

    // Get client IP
    const ip = req.headers.get("x-forwarded-for") || 
                req.headers.get("x-real-ip") || 
                "unknown";

    // Insert into database
    const { data: quoteRequest, error: dbError } = await supabase
      .from("work_package_quote_requests")
      .insert({
        work_package_id: quoteData.workPackageId,
        work_package_name: quoteData.workPackageName,
        name: quoteData.name,
        email: quoteData.email,
        phone: quoteData.phone,
        job_title: quoteData.jobTitle,
        company_name: quoteData.companyName,
        company_size: quoteData.companySize,
        industry: quoteData.industry,
        primary_location: quoteData.primaryLocation,
        has_multiple_locations: quoteData.hasMultipleLocations,
        org_maturity_level: quoteData.orgMaturityLevel,
        pricing_tier_interest: quoteData.pricingTierInterest,
        preferred_timeline: quoteData.preferredTimeline,
        budget_range: quoteData.budgetRange,
        challenge_description: quoteData.challengeDescription,
        current_state_description: quoteData.currentStateDescription,
        success_criteria: quoteData.successCriteria,
        compliance_requirements: quoteData.complianceRequirements,
        existing_systems: quoteData.existingSystems,
        cloud_environment: quoteData.cloudEnvironment,
        data_classification: quoteData.dataClassification,
        integration_requirements: quoteData.integrationRequirements,
        auth_method: quoteData.authMethod,
        number_of_users: quoteData.numberOfUsers,
        departments_involved: quoteData.departmentsInvolved,
        decision_makers: quoteData.decisionMakers,
        internal_champion: quoteData.internalChampion,
        implementation_team_size: quoteData.implementationTeamSize,
        primary_kpis: quoteData.primaryKpis,
        expected_roi_timeline: quoteData.expectedRoiTimeline,
        known_constraints: quoteData.knownConstraints,
        previous_experience: quoteData.previousExperience,
        previous_experience_details: quoteData.previousExperienceDetails,
        referral_source: quoteData.referralSource,
        preferred_contact_method: quoteData.preferredContactMethod,
        best_time_to_contact: quoteData.bestTimeToContact,
        additional_info: quoteData.additionalInfo,
        ip_address: ip,
        status: 'new'
      })
      .select()
      .single();

    if (dbError) {
      console.error("Database error:", dbError);
      throw new Error(`Failed to save quote request: ${dbError.message}`);
    }

    console.log("Quote request saved:", quoteRequest.id);

    // Send email notification
    const emailHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }
            .content { background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }
            .section { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #667eea; }
            .section h3 { margin-top: 0; color: #667eea; }
            .field { margin: 10px 0; }
            .label { font-weight: bold; color: #555; }
            .value { color: #333; margin-left: 10px; }
            .cta { background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>🎯 New Work Package Quote Request</h1>
              <p style="margin: 0; opacity: 0.9;">${quoteData.workPackageName}</p>
            </div>
            <div class="content">
              <div class="section">
                <h3>📋 Work Package Details</h3>
                <div class="field">
                  <span class="label">Work Package:</span>
                  <span class="value">${quoteData.workPackageName}</span>
                </div>
                <div class="field">
                  <span class="label">Pricing Tier Interest:</span>
                  <span class="value">${quoteData.pricingTierInterest || 'Not specified'}</span>
                </div>
                <div class="field">
                  <span class="label">Preferred Timeline:</span>
                  <span class="value">${quoteData.preferredTimeline || 'Not specified'}</span>
                </div>
                <div class="field">
                  <span class="label">Budget Range:</span>
                  <span class="value">${quoteData.budgetRange || 'Not specified'}</span>
                </div>
              </div>

              <div class="section">
                <h3>👤 Contact Information</h3>
                <div class="field">
                  <span class="label">Name:</span>
                  <span class="value">${quoteData.name}</span>
                </div>
                <div class="field">
                  <span class="label">Email:</span>
                  <span class="value"><a href="mailto:${quoteData.email}">${quoteData.email}</a></span>
                </div>
                ${quoteData.phone ? `
                <div class="field">
                  <span class="label">Phone:</span>
                  <span class="value">${quoteData.phone}</span>
                </div>` : ''}
                <div class="field">
                  <span class="label">Job Title:</span>
                  <span class="value">${quoteData.jobTitle || 'Not provided'}</span>
                </div>
                <div class="field">
                  <span class="label">Preferred Contact:</span>
                  <span class="value">${quoteData.preferredContactMethod || 'Email'}</span>
                </div>
                ${quoteData.bestTimeToContact ? `
                <div class="field">
                  <span class="label">Best Time:</span>
                  <span class="value">${quoteData.bestTimeToContact}</span>
                </div>` : ''}
              </div>

              <div class="section">
                <h3>🏢 Organization Profile</h3>
                <div class="field">
                  <span class="label">Company:</span>
                  <span class="value">${quoteData.companyName}</span>
                </div>
                <div class="field">
                  <span class="label">Company Size:</span>
                  <span class="value">${quoteData.companySize || 'Not specified'}</span>
                </div>
                <div class="field">
                  <span class="label">Industry:</span>
                  <span class="value">${quoteData.industry || 'Not specified'}</span>
                </div>
                <div class="field">
                  <span class="label">Location:</span>
                  <span class="value">${quoteData.primaryLocation || 'Not specified'}</span>
                </div>
                <div class="field">
                  <span class="label">Maturity Level:</span>
                  <span class="value">${quoteData.orgMaturityLevel || 'Not specified'}</span>
                </div>
              </div>

              ${quoteData.challengeDescription || quoteData.currentStateDescription || quoteData.successCriteria ? `
              <div class="section">
                <h3>🎯 Situation Assessment</h3>
                ${quoteData.challengeDescription ? `
                <div class="field">
                  <span class="label">Challenge:</span>
                  <div class="value" style="margin-top: 5px; display: block;">${quoteData.challengeDescription}</div>
                </div>` : ''}
                ${quoteData.currentStateDescription ? `
                <div class="field">
                  <span class="label">Current State:</span>
                  <div class="value" style="margin-top: 5px; display: block;">${quoteData.currentStateDescription}</div>
                </div>` : ''}
                ${quoteData.successCriteria ? `
                <div class="field">
                  <span class="label">Success Criteria:</span>
                  <div class="value" style="margin-top: 5px; display: block;">${quoteData.successCriteria}</div>
                </div>` : ''}
                ${quoteData.complianceRequirements ? `
                <div class="field">
                  <span class="label">Compliance:</span>
                  <div class="value" style="margin-top: 5px; display: block;">${quoteData.complianceRequirements}</div>
                </div>` : ''}
              </div>` : ''}

              ${quoteData.existingSystems || quoteData.cloudEnvironment || quoteData.dataClassification ? `
              <div class="section">
                <h3>💻 Technical Context</h3>
                ${quoteData.existingSystems && quoteData.existingSystems.length > 0 ? `
                <div class="field">
                  <span class="label">Existing Systems:</span>
                  <span class="value">${quoteData.existingSystems.join(', ')}</span>
                </div>` : ''}
                ${quoteData.cloudEnvironment ? `
                <div class="field">
                  <span class="label">Cloud Environment:</span>
                  <span class="value">${quoteData.cloudEnvironment}</span>
                </div>` : ''}
                ${quoteData.dataClassification ? `
                <div class="field">
                  <span class="label">Data Classification:</span>
                  <span class="value">${quoteData.dataClassification}</span>
                </div>` : ''}
                ${quoteData.integrationRequirements ? `
                <div class="field">
                  <span class="label">Integration Needs:</span>
                  <div class="value" style="margin-top: 5px; display: block;">${quoteData.integrationRequirements}</div>
                </div>` : ''}
              </div>` : ''}

              ${quoteData.numberOfUsers || quoteData.departmentsInvolved || quoteData.decisionMakers ? `
              <div class="section">
                <h3>👥 Team & Stakeholders</h3>
                ${quoteData.numberOfUsers ? `
                <div class="field">
                  <span class="label">Number of Users:</span>
                  <span class="value">${quoteData.numberOfUsers}</span>
                </div>` : ''}
                ${quoteData.departmentsInvolved && quoteData.departmentsInvolved.length > 0 ? `
                <div class="field">
                  <span class="label">Departments:</span>
                  <span class="value">${quoteData.departmentsInvolved.join(', ')}</span>
                </div>` : ''}
                ${quoteData.implementationTeamSize ? `
                <div class="field">
                  <span class="label">Implementation Team Size:</span>
                  <span class="value">${quoteData.implementationTeamSize}</span>
                </div>` : ''}
                ${quoteData.decisionMakers ? `
                <div class="field">
                  <span class="label">Decision Makers:</span>
                  <span class="value">${quoteData.decisionMakers}</span>
                </div>` : ''}
                ${quoteData.internalChampion ? `
                <div class="field">
                  <span class="label">Internal Champion:</span>
                  <span class="value">${quoteData.internalChampion}</span>
                </div>` : ''}
              </div>` : ''}

              ${quoteData.primaryKpis || quoteData.expectedRoiTimeline ? `
              <div class="section">
                <h3>📊 Success Metrics</h3>
                ${quoteData.primaryKpis && quoteData.primaryKpis.length > 0 ? `
                <div class="field">
                  <span class="label">Primary KPIs:</span>
                  <span class="value">${quoteData.primaryKpis.join(', ')}</span>
                </div>` : ''}
                ${quoteData.expectedRoiTimeline ? `
                <div class="field">
                  <span class="label">Expected ROI Timeline:</span>
                  <span class="value">${quoteData.expectedRoiTimeline}</span>
                </div>` : ''}
                ${quoteData.knownConstraints ? `
                <div class="field">
                  <span class="label">Known Constraints:</span>
                  <div class="value" style="margin-top: 5px; display: block;">${quoteData.knownConstraints}</div>
                </div>` : ''}
              </div>` : ''}

              ${quoteData.additionalInfo ? `
              <div class="section">
                <h3>📝 Additional Information</h3>
                <p style="margin: 0;">${quoteData.additionalInfo}</p>
              </div>` : ''}

              <div style="text-align: center; margin-top: 30px;">
                <a href="https://lzfgigiyqpuuxslsygjt.supabase.co/auth/v1/admin" class="cta">
                  View in Admin Dashboard →
                </a>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">
                  Quote Request ID: ${quoteRequest.id}<br>
                  Submitted: ${new Date().toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </body>
      </html>
    `;

    // Send notification email
    try {
      await resend.emails.send({
        from: "WorkFamily AI <noreply@workfamilyai.org>",
        to: ["info@workfamilyai.org", "troy@workfamilyai.org"],
        subject: `New Quote Request: ${quoteData.workPackageName} - ${quoteData.companyName}`,
        html: emailHtml,
      });
      console.log("Notification email sent successfully");
    } catch (emailError) {
      console.error("Failed to send notification email:", emailError);
      // Don't throw - quote was saved successfully
    }

    return new Response(
      JSON.stringify({
        success: true,
        quoteRequestId: quoteRequest.id,
        message: "Quote request submitted successfully"
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );

  } catch (error: any) {
    console.error("Error in submit-work-package-quote function:", error);
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message || "Internal server error"
      }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
};

serve(handler);
