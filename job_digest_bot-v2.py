import os
import smtplib
import requests
import json
import re
import html # Import the html module for escaping
from bs4 import BeautifulSoup # Not directly used in the provided solution for parsing, but kept as it was in the original file.
from datetime import datetime
from email.mime.text import MIMEText
from openpipe import OpenAI # Assuming OpenPipe setup is handled elsewhere, as per original file.

# --- Configuration (usually loaded from .env or similar) ---
# These would typically be loaded from environment variables for security and flexibility.
# For demonstration, placeholder values are used if not defined.
OPENPIPE_API_KEY = os.getenv("OPENPIPE_API_KEY", "your_openpipe_api_key")
MODEL_ID = os.getenv("MODEL_ID", "your_model_id")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "your_brave_api_key")
FROM_EMAIL = os.getenv("FROM_EMAIL", "your_email@example.com")
TO_EMAIL = os.getenv("TO_EMAIL", "recipient_email@example.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "your_gmail_app_password")

# --------------------------------------------------------------------------------
# 1. Get Raw Job Listings (Simulated for demonstration, would use OpenPipe API)
# --------------------------------------------------------------------------------
def get_job_digest():
    """
    Simulates fetching raw job listings from an OpenPipe model.
    In a real scenario, this would make an API call to OpenPipe.
    """
    # This is the example string you provided.
    # In your actual application, this would come from the OpenPipe API call.
    raw_job_string = """
[1] Artist in Residence at XYZ Gallery — Lead new media projects in HK
[2] Lecturer at ABC University — Teach interactive media
[3] Digital Media Specialist at Creative Hub — Develop immersive experiences & more!
[4] XR Developer at Innovate Studio — Build virtual reality applications <with> complex features
"""
    # The original code had an actual OpenPipe call, which is commented out here
    # for a self-contained example.
    # client = OpenAI(openpipe={"api_key": OPENPIPE_API_KEY})
    # prompt = """You are a job curator specializing in experimental media, digital culture, and XR positions. List 5–10 relevant job opportunities currently open in Hong Kong.
    # For each job, return:
    # - Title
    # - Institution
    # - One-line description (optional)
    # Format each line like this:
    # [1] Title at Institution — Short Description
    # Return each job on a new line."""
    # response = client.chat.completions.create(
    #     model=MODEL_ID,
    #     messages=[{"role": "user", "content": prompt}]
    # )
    # completion = response.choices[0].message.content
    # log_completion(prompt, completion) # Assuming log_completion is defined
    # return completion
    return raw_job_string

# --------------------------------------------------------------------------------
# 2. Parse Raw Text into Structured Job Dictionaries
# --------------------------------------------------------------------------------
def parse_job_lines(job_text: str) -> list[dict]:
    """
    Parses a plain string of job listings into a list of job dictionaries.
    Each dictionary contains 'title', 'description', and an empty 'link' initially.

    Args:
        job_text: A string containing job listings, e.g.,
                  "[1] Title at Institution — Description"

    Returns:
        A list of dictionaries, where each dictionary represents a job.
    """
    jobs = []
    lines = job_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue # Skip empty lines

        try:
            # Use regex to extract parts more robustly
            match = re.match(r"^\[\d+\]\s*(.*?)(?: at (.*?))?\s*(?:—\s*(.*))?$", line)
            if match:
                full_title_part, institution_part, description_part = match.groups()

                title = full_title_part.strip()
                institution = institution_part.strip() if institution_part else ""
                description = description_part.strip() if description_part else ""

                # Reconstruct title if institution exists, to match desired output format
                if institution:
                    title_for_dict = f"{title} at {institution}"
                else:
                    title_for_dict = title

                jobs.append({
                    "title": title_for_dict,
                    "description": description,
                    "link": "",  # Link will be added later
                })
            else:
                print(f"Warning: Could not parse line format: {line}")
        except Exception as e:
            print(f"Error parsing line '{line}': {e}")
    return jobs

# --------------------------------------------------------------------------------
# 3. Search Fallback: Brave API or Google
# --------------------------------------------------------------------------------
def search_brave(query: str) -> str:
    """
    Performs a Brave search for a given query and returns the first relevant URL.
    Falls back to a Google search URL if Brave search fails or no URL is found.

    Args:
        query: The search query string.

    Returns:
        A URL string.
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {
        "q": query,
        "count": 1,  # Only need one result for the link
        "search_lang": "en",
        "country": "HK", # Focusing on Hong Kong as per the prompt
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5) # Added timeout
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        results = data.get("web", {}).get("results", [])
        if results and "url" in results[0] and results[0]["url"].startswith("http"):
            return results[0]["url"]
    except requests.exceptions.RequestException as e:
        print(f"Brave search failed for '{query}': {e}")
    except json.JSONDecodeError:
        print(f"Brave search returned invalid JSON for '{query}'.")

    # Fallback to Google search if Brave fails or no suitable URL is found
    print(f"Falling back to Google search for: {query}")
    return "https://www.google.com/search?q=" + requests.utils.quote(query)

# --------------------------------------------------------------------------------
# 4. Enrich Job Dictionaries with Links
# --------------------------------------------------------------------------------
def enrich_with_links(job_list: list[dict]) -> list[dict]:
    """
    Iterates through a list of job dictionaries and adds a 'link' to each
    using Brave search if the link is missing.

    Args:
        job_list: A list of job dictionaries (e.g., from parse_job_lines).

    Returns:
        The updated list of job dictionaries with 'link' populated.
    """
    for job in job_list:
        if not job.get("link"): # Only search if link is not already present
            # Construct a search query for Brave
            search_query = f"{job['title']} {job['description']} Hong Kong job"
            job["link"] = search_brave(search_query)
    return job_list

# --------------------------------------------------------------------------------
# 5. Render Jobs as HTML List for Email Body
# --------------------------------------------------------------------------------
def render_jobs_to_html_list(job_list: list[dict]) -> str:
    """
    Renders a list of job dictionaries into an HTML unordered list.
    Each job becomes a clickable list item.

    Args:
        job_list: A list of job dictionaries, including 'title', 'description', and 'link'.

    Returns:
        An HTML string representing the list of jobs.
    """
    html_list = '<ul style="list-style: none; padding-left: 0;">' # Remove default list style

    for job in job_list:
        # HTML escape title and description to prevent breaking HTML structure
        # if they contain characters like <, >, &, ", '
        escaped_title = html.escape(job.get("title", "Untitled Position"))
        escaped_description = html.escape(job.get("description", ""))
        # HTML escape the link as well, especially for use in href attribute
        # This is crucial if the URL itself might contain problematic characters like "
        escaped_link = html.escape(job.get("link", "#"))

        # Construct the <li> element parts explicitly to avoid f-string multi-line issues
        li_start = '<li style="margin-bottom: 15px; background-color: #f0f8ff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">'
        anchor_tag = f'<a href="{escaped_link}" style="color: #007bff; text-decoration: none; font-weight: bold; font-size: 16px;" target="_blank" rel="noopener noreferrer">{escaped_title}</a>'
        paragraph_tag = f'<p style="font-size: 14px; color: #555; margin-top: 5px; margin-bottom: 0;">{escaped_description}</p>'
        li_end = '</li>'

        html_list += f"{li_start}{anchor_tag}{paragraph_tag}{li_end}"
    html_list += "</ul>"
    return html_list

# --------------------------------------------------------------------------------
# 6. Assemble Final HTML Email Body
# --------------------------------------------------------------------------------
def get_job_digest_enriched_html() -> str:
    """
    Orchestrates the process of fetching, parsing, enriching, and rendering
    job listings into a complete HTML email body.

    Returns:
        A complete HTML string for the email.
    """
    raw_text = get_job_digest()
    job_data_parsed = parse_job_lines(raw_text)
    job_data_enriched = enrich_with_links(job_data_parsed)
    html_list_content = render_jobs_to_html_list(job_data_enriched)

    current_date = datetime.now().strftime('%B %d, %Y')

    return f"""
    <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9f9f9; padding: 20px; line-height: 1.6;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <h2 style="margin-bottom: 25px; color: #333; text-align: center; font-size: 24px;">🗞️ Your Daily Job Digest</h2>
                {html_list_content}
                <p style="font-size: 12px; color: #777; margin-top: 30px; text-align: center;">
                    This message was generated by your pinkpulse job agent, {current_date}.
                </p>
            </div>
        </body>
    </html>
    """

# --------------------------------------------------------------------------------
# 7. Email via Gmail SMTP
# --------------------------------------------------------------------------------
def send_email(subject: str, body: str, html: bool = False):
    """
    Sends an email using Gmail's SMTP server.

    Args:
        subject: The subject line of the email.
        body: The content of the email (plain text or HTML).
        html: Boolean, True if the body is HTML, False otherwise.
    """
    msg = MIMEText(body, "html" if html else "plain")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(FROM_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# --------------------------------------------------------------------------------
# Main execution block
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating job digest email...")
    digest_html = get_job_digest_enriched_html()
    
    with open("job_digest_email.html", "w", encoding="utf-8") as f:
        f.write(digest_html)
    
    print("HTML email content saved to job_digest_email.html")
    
    # ✅ Actually send the email
    send_email("🗞️ Your Daily Job Digest (with links)", digest_html, html=True)
