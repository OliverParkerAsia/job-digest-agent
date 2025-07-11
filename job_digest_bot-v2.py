import os
import smtplib
import time
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from openpipe import OpenAI

def get_job_digest():
    """Original version — returns plain text."""
    client = OpenAI(
        openpipe={"api_key": os.getenv("OPENPIPE_API_KEY")}
    )

    model_id = os.getenv("MODEL_ID")
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": "List top 3 new media jobs in Hong Kong today."}
        ]
    )

    return response.choices[0].message.content

def search_duckduckgo(query):
    """Returns the first result link from DuckDuckGo HTML version."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0"}
    data = {"q": query}

    response = requests.post(url, headers=headers, data=data)
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("a", class_="result__a")

    if results:
        return results[0]["href"]
    return None

def enrich_with_links(job_list_raw):
    """
    Takes model output string and returns an HTML <ul> with clickable job links.
    Assumes format: [1] Title at Institution
    """
    lines = job_list_raw.strip().split("\n")
    html_list = []

    for line in lines:
        try:
            job_text = line.split("]", 1)[1].strip()
            search_query = job_text + " site:.hk"

            url = search_duckduckgo(search_query)
            if url:
                html_list.append(f'<li><a href="{url}">{job_text}</a></li>')
            else:
                html_list.append(f"<li>{job_text}</li>")  # fallback

            time.sleep(1.5)  # avoid getting blocked

        except Exception as e:
            html_list.append(f"<li>{line} (error)</li>")

    return "<ul>" + "\n".join(html_list) + "</ul>"

def get_job_digest_enriched():
    """Extended version — returns HTML with linked job titles."""
    raw = get_job_digest()
    html = enrich_with_links(raw)
    return f"""
    <html>
        <body style="font-family: sans-serif;">
            <h2>🗞️ Your Daily Job Digest</h2>
            {html}
        </body>
    </html>
    """

def send_email(subject, body, html=False):
    msg = MIMEText(body, "html" if html else "plain")
    msg["Subject"] = subject
    msg["From"] = os.getenv("FROM_EMAIL")
    msg["To"] = os.getenv("TO_EMAIL")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("FROM_EMAIL"), os.getenv("GMAIL_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    # Use the enriched version with links:
    digest_html = get_job_digest_enriched()
    send_email("🗞️ Your Daily Job Digest (with links)", digest_html, html=True)

    # Or fallback to plain version:
    # digest_text = get_job_digest()
    # send_email("🗞️ Your Daily Job Digest", digest_text)
