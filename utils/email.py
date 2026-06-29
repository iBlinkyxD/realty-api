from html import escape
from urllib.parse import quote
from config import settings

CODE_EXPIRE_MINUTES = 15


def _send(to_email: str, subject: str, html: str) -> None:
    if not settings.resend_api_key:
        print(f"[DEV] Email to {to_email}: {subject}")
        return
    import resend
    resend.api_key = settings.resend_api_key
    resend.Emails.send({"from": settings.email_from, "to": to_email, "subject": subject, "html": html})


def _email_wrap(header_text: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<body style="margin:0;padding:0;background:#f5f3ef;font-family:sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ef;padding:40px 16px">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.07)">
        <tr>
          <td align="left" style="background:#00102e;padding:20px 28px">
            <img src="{_logo_src()}" alt="I Love DR Realty" style="height:44px;width:auto;display:block" />
          </td>
        </tr>
        <tr><td style="padding:32px 32px 0">{body_html}</td></tr>
        <tr>
          <td style="padding:20px 32px 28px;border-top:1px solid #f0ebe2">
            <p style="margin:0;color:#aaa;font-size:12px;line-height:1.6">
              {header_text} — I Love DR Realty
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_listing_approved_email(to_email: str, display_name: str, listing_title: str, listing_url: str) -> None:
    body = f"""
      <h2 style="margin:0 0 10px;color:#00102e;font-size:21px;font-weight:700">Your listing is live!</h2>
      <p style="margin:0 0 20px;color:#555;font-size:14.5px;line-height:1.6">
        Hi {escape(display_name)}, your listing <strong>{escape(listing_title)}</strong> has been approved and is now publicly visible on I Love DR Realty.
      </p>
      <table cellpadding="0" cellspacing="0" style="margin-bottom:28px">
        <tr><td>
          <a href="{listing_url}" style="display:inline-block;background:#00102e;color:#ffffff;text-decoration:none;font-weight:700;font-size:14.5px;padding:13px 30px;border-radius:8px">
            View Listing &rarr;
          </a>
        </td></tr>
      </table>
    """
    _send(to_email, "Your listing has been approved ✓", _email_wrap("Listing approved", body))


def send_listing_rejected_email(to_email: str, display_name: str, listing_title: str, reason: str) -> None:
    body = f"""
      <h2 style="margin:0 0 10px;color:#00102e;font-size:21px;font-weight:700">Your listing needs revision</h2>
      <p style="margin:0 0 12px;color:#555;font-size:14.5px;line-height:1.6">
        Hi {escape(display_name)}, your listing <strong>{escape(listing_title)}</strong> was not approved.
      </p>
      <div style="background:#fdf2f2;border:1px solid #f5dada;border-radius:10px;padding:16px 20px;margin-bottom:24px">
        <p style="margin:0;color:#b91c1c;font-size:14px;line-height:1.6">{escape(reason)}</p>
      </div>
      <p style="margin:0 0 28px;color:#555;font-size:14px;line-height:1.6">
        Please update your listing and resubmit for review from your dashboard.
      </p>
    """
    _send(to_email, "Your listing needs revision", _email_wrap("Listing not approved", body))


def send_upgrade_approved_email(to_email: str, display_name: str, new_role: str) -> None:
    role_label = escape(new_role.replace("_", " ").title())
    body = f"""
      <h2 style="margin:0 0 10px;color:#00102e;font-size:21px;font-weight:700">Account upgraded to {role_label}</h2>
      <p style="margin:0 0 20px;color:#555;font-size:14.5px;line-height:1.6">
        Hi {escape(display_name)}, your request to become a <strong>{role_label}</strong> on I Love DR Realty has been approved.
        Log in to your dashboard to access your new features.
      </p>
      <table cellpadding="0" cellspacing="0" style="margin-bottom:28px">
        <tr><td>
          <a href="{settings.landing_url}/login" style="display:inline-block;background:#00102e;color:#ffffff;text-decoration:none;font-weight:700;font-size:14.5px;padding:13px 30px;border-radius:8px">
            Go to Dashboard &rarr;
          </a>
        </td></tr>
      </table>
    """
    _send(to_email, f"Your account has been upgraded to {role_label}", _email_wrap("Account upgrade approved", body))


def send_upgrade_rejected_email(to_email: str, display_name: str, reason: str) -> None:
    body = f"""
      <h2 style="margin:0 0 10px;color:#00102e;font-size:21px;font-weight:700">Upgrade request not approved</h2>
      <p style="margin:0 0 12px;color:#555;font-size:14.5px;line-height:1.6">
        Hi {escape(display_name)}, your role upgrade request was not approved at this time.
      </p>
      <div style="background:#fdf2f2;border:1px solid #f5dada;border-radius:10px;padding:16px 20px;margin-bottom:28px">
        <p style="margin:0;color:#b91c1c;font-size:14px;line-height:1.6">{escape(reason)}</p>
      </div>
    """
    _send(to_email, "Your upgrade request was not approved", _email_wrap("Upgrade request", body))


def send_realtor_assigned_owner_email(to_email: str, realtor_name: str, owner_name: str, owner_email: str) -> None:
    body = f"""
      <h2 style="margin:0 0 10px;color:#00102e;font-size:21px;font-weight:700">You've been assigned a new property owner</h2>
      <p style="margin:0 0 20px;color:#555;font-size:14.5px;line-height:1.6">
        Hi {escape(realtor_name)}, a property owner has been assigned to you on I Love DR Realty.
        Log in to your dashboard to view their details and begin managing their listing.
      </p>
      <div style="background:#f5f9ff;border:1px solid #d0e4f7;border-radius:10px;padding:16px 20px;margin-bottom:24px">
        <p style="margin:0 0 4px;color:#0b63ab;font-size:13px;font-weight:700">{escape(owner_name)}</p>
        <p style="margin:0;color:#555;font-size:13px">{escape(owner_email)}</p>
      </div>
      <table cellpadding="0" cellspacing="0" style="margin-bottom:28px">
        <tr><td>
          <a href="{settings.landing_url}/dashboard" style="display:inline-block;background:#00102e;color:#ffffff;text-decoration:none;font-weight:700;font-size:14.5px;padding:13px 30px;border-radius:8px">
            Go to Dashboard &rarr;
          </a>
        </td></tr>
      </table>
    """
    _send(to_email, f"New owner assigned to you — {owner_name}", _email_wrap("Owner assignment", body))


def send_lead_notification(lead, property_info: dict | None = None, notify_email: str | None = None) -> None:
    email = notify_email or settings.notify_email
    if not email:
        return
    type_labels = {
        "property_inquiry": "Property Inquiry",
        "buyer_interest":   "Buyer Interest",
        "seller_interest":  "Seller Interest",
        "booking":          "Booking Request",
    }
    type_label = type_labels.get(lead.type, escape(lead.type))
    phone_row = f"<tr><td style='padding:4px 0;color:#888;font-size:13px;width:90px'>Phone</td><td style='padding:4px 0;font-size:13px;color:#00102e'>{escape(lead.phone)}</td></tr>" if lead.phone else ""
    message_block = f"""
      <div style="background:#f5f3ef;border-radius:8px;padding:14px 16px;margin:16px 0">
        <p style="margin:0;color:#555;font-size:13.5px;line-height:1.6;white-space:pre-wrap">{escape(lead.message)}</p>
      </div>""" if lead.message else ""
    property_block = ""
    if property_info:
        prop_title = escape(property_info.get("title", ""))
        prop_url = f"{settings.landing_url}/listing/{property_info.get('id', '')}"
        property_block = f"""
      <p style="margin:16px 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em">Property</p>
      <a href="{prop_url}" style="color:#0b63ab;font-size:13.5px;font-weight:600;text-decoration:none">{prop_title} &rarr;</a>"""
    dashboard_url = f"{settings.landing_url}/dashboard"
    body = f"""
      <h2 style="margin:0 0 4px;color:#00102e;font-size:20px;font-weight:700">New lead captured</h2>
      <p style="margin:0 0 20px;color:#888;font-size:13px">{type_label}</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:4px 0;color:#888;font-size:13px;width:90px">Name</td><td style="padding:4px 0;font-size:13.5px;font-weight:600;color:#00102e">{escape(lead.name)}</td></tr>
        <tr><td style="padding:4px 0;color:#888;font-size:13px">Email</td><td style="padding:4px 0;font-size:13px;color:#00102e"><a href="mailto:{escape(lead.email)}" style="color:#0b63ab">{escape(lead.email)}</a></td></tr>
        {phone_row}
      </table>
      {message_block}
      {property_block}
      <table cellpadding="0" cellspacing="0" style="margin-top:24px;margin-bottom:8px">
        <tr><td>
          <a href="{dashboard_url}" style="display:inline-block;background:#00102e;color:#ffffff;text-decoration:none;font-weight:700;font-size:13.5px;padding:11px 26px;border-radius:8px">
            View in Dashboard &rarr;
          </a>
        </td></tr>
      </table>
    """
    _send(email, f"New lead: {lead.name}", _email_wrap("Lead notification", body))


def send_realtor_lead_assigned_email(
    to_email: str,
    realtor_name: str,
    lead,
    property_info: dict | None = None,
) -> None:
    type_labels = {
        "property_inquiry": "Property Inquiry",
        "buyer_interest":   "Buyer Interest",
        "seller_interest":  "Seller Interest",
        "booking":          "Booking Request",
    }
    type_label = type_labels.get(lead.type, escape(lead.type))
    phone_row = f"<tr><td style='padding:4px 0;color:#888;font-size:13px;width:90px'>Phone</td><td style='padding:4px 0;font-size:13px;color:#00102e'>{escape(lead.phone)}</td></tr>" if lead.phone else ""
    message_block = f"""
      <div style="background:#f5f3ef;border-radius:8px;padding:14px 16px;margin:16px 0">
        <p style="margin:0;color:#555;font-size:13.5px;line-height:1.6;white-space:pre-wrap">{escape(lead.message)}</p>
      </div>""" if lead.message else ""
    property_block = ""
    if property_info:
        prop_title = escape(property_info.get("title", ""))
        prop_url = f"{settings.landing_url}/listing/{property_info.get('id', '')}"
        property_block = f"""
      <p style="margin:16px 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em">Property</p>
      <a href="{prop_url}" style="color:#0b63ab;font-size:13.5px;font-weight:600;text-decoration:none">{prop_title} &rarr;</a>"""
    dashboard_url = f"{settings.landing_url}/dashboard"
    body = f"""
      <h2 style="margin:0 0 4px;color:#00102e;font-size:20px;font-weight:700">You have a new lead</h2>
      <p style="margin:0 0 20px;color:#888;font-size:13px">Hi {escape(realtor_name)}, a lead has been assigned to you.</p>
      <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em">{type_label}</p>
      <table style="border-collapse:collapse;width:100%;margin-bottom:4px">
        <tr><td style="padding:4px 0;color:#888;font-size:13px;width:90px">Name</td><td style="padding:4px 0;font-size:13.5px;font-weight:600;color:#00102e">{escape(lead.name)}</td></tr>
        <tr><td style="padding:4px 0;color:#888;font-size:13px">Email</td><td style="padding:4px 0;font-size:13px;color:#00102e"><a href="mailto:{escape(lead.email)}" style="color:#0b63ab">{escape(lead.email)}</a></td></tr>
        {phone_row}
      </table>
      {message_block}
      {property_block}
      <table cellpadding="0" cellspacing="0" style="margin-top:24px;margin-bottom:8px">
        <tr><td>
          <a href="{dashboard_url}" style="display:inline-block;background:#00102e;color:#ffffff;text-decoration:none;font-weight:700;font-size:13.5px;padding:11px 26px;border-radius:8px">
            View Lead &rarr;
          </a>
        </td></tr>
      </table>
    """
    _send(to_email, f"New lead assigned to you — {lead.name}", _email_wrap("Lead assigned", body))


def _logo_src() -> str:
    # White version for use on the coral header
    base = settings.logo_url or f"{settings.landing_url}/iLoveDRRealty_White.png"
    return base


def send_verification_email(to_email: str, code: str) -> None:
    verify_url = f"{settings.landing_url}/verify?email={quote(to_email)}&code={code}"

    if not settings.resend_api_key:
        print(f"[DEV] Verification code for {to_email}: {code}  |  {verify_url}")
        return

    import resend
    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": settings.email_from,
        "to": to_email,
        "subject": "Your I Love DR Realty verification code",
        "html": f"""
        <!DOCTYPE html>
        <html lang="en">
        <body style="margin:0;padding:0;background:#f5f3ef;font-family:sans-serif">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ef;padding:40px 16px">
            <tr><td align="center">
              <table width="100%" style="max-width:480px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.07)">

                <!-- Header -->
                <tr>
                  <td align="left" style="background:#00102e;padding:20px 28px">
                    <img src="{_logo_src()}" alt="I Love DR Realty" style="height:44px;width:auto;display:block" />
                  </td>
                </tr>

                <!-- Body -->
                <tr>
                  <td style="padding:32px 32px 0">
                    <h2 style="margin:0 0 10px;color:#00102e;font-size:21px;font-weight:700">Verify your email address</h2>
                    <p style="margin:0 0 24px;color:#555;font-size:14.5px;line-height:1.6">
                      Use the code below to verify your account. It expires in <strong>{CODE_EXPIRE_MINUTES} minutes</strong>.
                    </p>

                    <!-- Code box -->
                    <div style="font-size:40px;font-weight:700;letter-spacing:14px;color:#e10f1f;padding:22px 16px;background:#fdf2f2;border-radius:10px;text-align:center;margin-bottom:24px;border:1px solid #f5dada">
                      {code}
                    </div>

                    <p style="margin:0 0 14px;color:#555;font-size:14px">Or click the button to confirm directly:</p>

                    <!-- CTA button -->
                    <table cellpadding="0" cellspacing="0" style="margin-bottom:24px">
                      <tr>
                        <td>
                          <a href="{verify_url}"
                             style="display:inline-block;background:#e10f1f;color:#ffffff;text-decoration:none;font-weight:700;font-size:14.5px;padding:13px 30px;border-radius:8px">
                            Verify Email &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>

                    <p style="margin:0 0 6px;color:#999;font-size:12.5px">If the button doesn't work, copy and paste this link:</p>
                    <p style="margin:0 0 28px;font-size:12px;word-break:break-all">
                      <a href="{verify_url}" style="color:#e10f1f;text-decoration:underline">{verify_url}</a>
                    </p>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td style="padding:20px 32px 28px;border-top:1px solid #f0ebe2">
                    <p style="margin:0;color:#aaa;font-size:12px;line-height:1.6">
                      If you didn't create an I Love DR Realty account, you can safely ignore this email.
                    </p>
                  </td>
                </tr>

              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """,
    })
