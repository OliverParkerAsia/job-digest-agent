import os
import smtplib
from email.mime.text import MIMEText
import openai

def get_job_digest():
    import openai
client = openai.OpenAI(
    api_key="your_openpipe_key",
    base_url="https://openpipe.ai/api/v1/"  # ← this is critical
)
    model_id = os.getenv("MODEL_ID")

    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": "List top 3 new media jobs in Hong Kong today."}]
    )

    return response.choices[0].message.content


def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("FROM_EMAIL")
    msg["To"] = os.getenv("TO_EMAIL")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("FROM_EMAIL"), os.getenv("GMAIL_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    digest = get_job_digest()
    send_email("🗞 Your Daily Job Digest", digest)
