from html import escape

import resend

from celery import shared_task
from django.conf import settings

BRAND_NAME = "Noshiro DB"
ACCENT_COLOR = "#7F6FB0"
CODE_EXPIRE_MINUTES = 5


def build_verification_text(code: str) -> str:
    return f"""Your {BRAND_NAME} verification code is:

{code}

This code will expire in {CODE_EXPIRE_MINUTES} minutes.

If you did not request this email, you can safely ignore it.
"""


def build_verification_html(code: str) -> str:
    safe_code = escape(code)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your {BRAND_NAME} verification code</title>
  </head>
  <body style="margin:0;padding:0;background:#f4f5f7;color:#17171c;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
      Use this code to continue. It expires in {CODE_EXPIRE_MINUTES} minutes.
    </div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#f4f5f7;">
      <tr>
        <td align="center" style="padding:40px 16px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;max-width:520px;border-collapse:separate;border-spacing:0;background:#ffffff;border:1px solid #e3e5ea;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:24px 28px;background:#17171c;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="vertical-align:middle;">
                      <div style="font-size:18px;line-height:24px;font-weight:700;color:#ffffff;">{BRAND_NAME}</div>
                      <div style="margin-top:4px;font-size:13px;line-height:20px;color:#a9a9b3;">Anime and galgame catalog</div>
                    </td>
                    <td align="right" style="vertical-align:middle;">
                      <div style="display:inline-block;width:36px;height:36px;border-radius:10px;background:{ACCENT_COLOR};"></div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:32px 28px 8px;">
                <h1 style="margin:0;font-size:22px;line-height:30px;font-weight:700;color:#17171c;">Verify your email</h1>
                <p style="margin:12px 0 0;font-size:15px;line-height:24px;color:#5d6470;">
                  Enter the code below to continue signing in to {BRAND_NAME}.
                </p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:24px 28px;">
                <div style="display:inline-block;min-width:240px;padding:18px 24px;border-radius:14px;background:#f7f4ff;border:1px solid #e4ddf6;color:#17171c;font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;font-size:32px;line-height:40px;font-weight:700;letter-spacing:8px;text-align:center;">
                  {safe_code}
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                  <tr>
                    <td style="padding:16px 0;border-top:1px solid #ebecef;border-bottom:1px solid #ebecef;font-size:14px;line-height:22px;color:#5d6470;">
                      This code expires in <strong style="color:{ACCENT_COLOR};">{CODE_EXPIRE_MINUTES} minutes</strong>. Do not share it with anyone.
                    </td>
                  </tr>
                </table>
                <p style="margin:18px 0 0;font-size:13px;line-height:21px;color:#7b8190;">
                  If you did not request this email, no action is needed. Your account remains secure.
                </p>
              </td>
            </tr>
          </table>
          <p style="margin:16px 0 0;font-size:12px;line-height:18px;color:#8a909d;">
            Sent by {BRAND_NAME}
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 3},
)
def send_verification_email(self, email: str, code: str):
    resend.api_key = settings.RESEND_API_KEY

    resend.Emails.send(
        {
            "from": f"{BRAND_NAME} <{settings.EMAIL_FROM}>",
            "to": [email],
            "subject": f"Your {BRAND_NAME} verification code",
            "html": build_verification_html(code),
            "text": build_verification_text(code),
        }
    )
