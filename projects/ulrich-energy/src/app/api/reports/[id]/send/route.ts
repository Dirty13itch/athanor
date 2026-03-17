import { NextResponse } from "next/server";
import { queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";

/**
 * POST /api/reports/:id/send
 *
 * Sends the generated report to a client via email.
 * Body: { recipientEmail: string, subject?: string, message?: string }
 *
 * Uses nodemailer-compatible SMTP config from environment variables.
 * Falls back to recording the delivery intent if SMTP is not configured.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.json().catch(() => null);

  if (!body || typeof body.recipientEmail !== "string" || !body.recipientEmail.includes("@")) {
    return NextResponse.json(
      { error: "recipientEmail is required and must be a valid email" },
      { status: 400 },
    );
  }

  const recipientEmail = body.recipientEmail.trim();
  const subject = typeof body.subject === "string" ? body.subject : "Your Energy Inspection Report — Ulrich Energy";
  const message = typeof body.message === "string"
    ? body.message
    : "Please find your energy inspection report attached. Contact us with any questions.";

  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({
      sent: true,
      to: recipientEmail,
      subject,
      reportId: id,
    });
  }

  // Verify report exists
  const report = await queryOne<{
    id: string;
    narrative: string | null;
    status: string;
    inspection_id: string;
  }>("SELECT id, narrative, status, inspection_id FROM reports WHERE id = $1", [id]);

  if (!report) {
    return NextResponse.json({ error: "Report not found" }, { status: 404 });
  }

  if (!report.narrative) {
    return NextResponse.json(
      { error: "Report has no narrative. Generate the report first." },
      { status: 400 },
    );
  }

  // Get inspection address for the email
  const inspection = await queryOne<{ address: string; builder: string }>(
    "SELECT address, builder FROM inspections WHERE id = $1",
    [report.inspection_id],
  );

  const smtpHost = process.env.SMTP_HOST;
  const smtpPort = parseInt(process.env.SMTP_PORT ?? "587");
  const smtpUser = process.env.SMTP_USER;
  const smtpPass = process.env.SMTP_PASS;
  const fromEmail = process.env.SMTP_FROM ?? "reports@ulrichenergy.com";

  if (!smtpHost || !smtpUser) {
    // No SMTP configured — record the delivery intent and mark as delivered
    await queryOne(
      `UPDATE reports SET recipient_email = $1, delivered_at = $2, status = 'delivered' WHERE id = $3 RETURNING id`,
      [recipientEmail, new Date().toISOString(), id],
    );

    return NextResponse.json({
      sent: false,
      queued: true,
      to: recipientEmail,
      subject,
      reportId: id,
      note: "SMTP not configured. Delivery recorded but email not sent. Configure SMTP_HOST, SMTP_USER, SMTP_PASS environment variables.",
    });
  }

  // Dynamic import nodemailer (optional dependency)
  try {
    const nodemailer = await import("nodemailer");
    const transporter = nodemailer.createTransport({
      host: smtpHost,
      port: smtpPort,
      secure: smtpPort === 465,
      auth: { user: smtpUser, pass: smtpPass },
    });

    // Build the PDF URL for attachment
    const baseUrl = process.env.NEXTAUTH_URL ?? process.env.BASE_URL ?? "http://localhost:3003";
    const pdfUrl = `${baseUrl}/api/reports/${id}/pdf`;

    // Fetch the HTML report
    const pdfResp = await fetch(pdfUrl);
    const htmlContent = await pdfResp.text();

    await transporter.sendMail({
      from: `"Ulrich Energy" <${fromEmail}>`,
      to: recipientEmail,
      subject,
      text: `${message}\n\nProperty: ${inspection?.address ?? "N/A"}\nBuilder: ${inspection?.builder ?? "N/A"}\n\nView your full report at: ${pdfUrl}`,
      html: `<p>${message.replace(/\n/g, "<br>")}</p><hr><p>Property: ${inspection?.address ?? "N/A"}<br>Builder: ${inspection?.builder ?? "N/A"}</p><p><a href="${pdfUrl}">View Full Report</a></p>`,
      attachments: [
        {
          filename: `report-${id}.html`,
          content: htmlContent,
          contentType: "text/html",
        },
      ],
    });

    // Update report status
    await queryOne(
      `UPDATE reports SET recipient_email = $1, delivered_at = $2, status = 'delivered' WHERE id = $3 RETURNING id`,
      [recipientEmail, new Date().toISOString(), id],
    );

    return NextResponse.json({
      sent: true,
      to: recipientEmail,
      subject,
      reportId: id,
    });
  } catch (err) {
    console.error("Email delivery failed:", err);

    // Still record the attempt
    await queryOne(
      `UPDATE reports SET recipient_email = $1, status = 'generated' WHERE id = $2 RETURNING id`,
      [recipientEmail, id],
    ).catch(() => {});

    return NextResponse.json(
      {
        error: "Email delivery failed",
        detail: err instanceof Error ? err.message : "Unknown error",
      },
      { status: 502 },
    );
  }
}
