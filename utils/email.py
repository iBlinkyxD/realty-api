from urllib.parse import quote
from config import settings

CODE_EXPIRE_MINUTES = 15


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
