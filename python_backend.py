import os
from supabase import create_client
import requests
from openai import OpenAI

# Initialize API Clients (Ensure these are set in your environment variables)
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

def get_job_urls_from_google(role, location):
    """Step 1: Use Google Search API to find job links."""
    query = f'site:jobstreet.com.ph OR site:indeed.com "{role}" "{location}" "apply"'
    url = f"https://serpapi.com/search.json?q={urlencode(query)}&api_key={SERPAPI_KEY}"
    
    response = requests.get(url).json()
    urls = [result['link'] for result in response.get('organic_results', [])]
    return urls

def filter_new_urls(url_list):
    """Step 2: Check Supabase memory to filter out duplicates."""
    if not url_list:
        return []
    
    # Query Supabase for matching URLs
    response = supabase_client.table("processed_jobs").select("url").in_("url", url_list).execute()
    existing_urls = {row['url'] for row in response.data}
    
    # Keep only the URLs that don't exist in the database
    return [url for url in url_list if url not in existing_urls]

def scrape_with_firecrawl(url):
    """Step 3: Scrape website through Firecrawl to bypass anti-bot walls."""
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"url": url, "formats": ["markdown"]}
    response = requests.post("https://api.firecrawl.dev/v1/scrape", json=payload, headers=headers)
    return response.json().get("data", {}).get("markdown", "")

def analyze_job_description(markdown_text, user_skills):
    """Step 4: Use OpenAI to reason, extract skills, and check compatibility."""
    prompt = f"""
    You are a technical career assistant. Analyze this job description:
    ---
    {markdown_text}
    ---
    Tasks:
    1. Extract Job Title, Company, and Location.
    2. Extract all required programming languages and analytics tools.
    3. Determine if the job matches any of these core user skills: {', '.join(user_skills)}.
    
    Format your response strictly as a JSON object with keys: title, company, location, technical_skills, matches_profile (boolean).
    """
    
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def save_job_to_memory(url, title, company):
    """Step 5: Log processed jobs into Supabase long-term memory."""
    supabase_client.table("processed_jobs").insert({
        "url": url,
        "job_title": title,
        "company_name": company
    }).execute()