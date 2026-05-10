import resend

from celery import shared_task
from django.conf import settings


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 3},
)
def send_verification_email(self, email: str, code: str):
    resend.api_key = settings.RESEND_API_KEY

    subject = "Your Verification Code"

    text_content = f"""
Your verification code is: {code}

This code will expire in 5 minutes.

If you did not request this, please ignore this email.
"""

    html_content = f"""
<!DOCTYPE html>
<html>
<body style="
    margin:0;
    background:#0f0f14;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
">
	<table width="100%" cellpadding="0" cellspacing="0" style="padding:48px 16px;">
		<tr>
			<td align="center">
				<table width="420" cellpadding="0" cellspacing="0" style="
    background:#181820;
    border:1px solid rgba(255,255,255,0.06);
    border-radius:10px;
    padding:28px;
">
					<!-- Title -->
					<tr>
						<td style="color:#fff;font-size:15px;font-weight:600;"> Verify your email </td>
					</tr>
					<tr>
						<td height="10"></td>
					</tr>
					<!-- Description -->
					<tr>
						<td style="color:#a0a0b2;font-size:13px;line-height:1.6;"> Enter the verification code below to continue. </td>
					</tr>
					<tr>
						<td height="26"></td>
					</tr>
					<!-- Code -->
					<tr>
						<td align="center" valign="middle" style="
    padding:12px 20px;
    height:52px;

    font-size:26px;
    font-weight:600;
    letter-spacing:6px;
    color:#ffffff;

    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;

    text-align:center;
    line-height:1;
"> {code} </td>
					</tr>
					<tr>
						<td height="22"></td>
					</tr>
					<!-- Expire -->
					<tr>
						<td style="font-size:12px;color:#8a8aa0;"> Expires in <span style="color:#7F6FB0;">5 minutes</span>
						</td>
					</tr>
					<tr>
						<td height="18"></td>
					</tr>
					<!-- Divider -->
					<tr>
						<td>
							<div style="height:1px;background:rgba(255,255,255,0.06);"></div>
						</td>
					</tr>
					<tr>
						<td height="18"></td>
					</tr>
					<!-- Footer -->
					<tr>
						<td style="font-size:12px;color:#6b6b80;line-height:1.6;"> If you didn’t request this email, you can ignore it. </td>
					</tr>
				</table>
		<tr>
			<td align="center" style="padding-top:14px;font-size:11px;color:#5a5a70;"> © Noshiro </td>
		</tr>
		</td>
		</tr>
	</table>
</body>
</html>
"""

    resend.Emails.send(
        {
            "from": f"Noshiro <{settings.EMAIL_FROM}>",
            "to": [email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }
    )
