import streamlit as st
import pandas as pd
import requests
import urllib.parse
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# --- 1. App Configuration (MUST BE FIRST) ---
st.set_page_config(page_title="AI Job Agent", page_icon="🤖", layout="wide")

# --- 2. Environment & API Initialization ---
load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
try:
    supabase_client: Client = create_client(supabase_url, supabase_key)
except Exception:
    supabase_client = None

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# We use gemini-1.5-flash because it is fast and we configure it to strictly output JSON
model = genai.GenerativeModel(
    'gemini-1.5-flash',
    generation_config={"response_mime_type": "application/json"}
)
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# --- 3. Session State & Folder Initialization (THIS PREVENTS YOUR ERROR) ---
if 'messages' not in st.session_state:
    st.session_state['messages'] = [{"role": "assistant", "content": "Hello! I am your AI Job Agent. Tell me what role and location you are looking for (e.g., 'Find Data Analyst roles in Taguig')."}]
if 'user_skills' not in st.session_state:
    st.session_state['user_skills'] = ["Python", "SQL", "Tableau", "Power BI", "Excel", "R"]
if not os.path.exists("saved_csvs"):
    os.makedirs("saved_csvs")

# --- 4. Backend Agent Functions ---

def extract_search_params(prompt_text):
    """Uses Gemini to extract the job role and location directly from the user's chat message."""
    prompt = f"""
    Extract the target job role and location from this user request: "{prompt_text}"
    If no location is mentioned, default to "Metro Manila".
    If it does not sound like a job search request, return empty strings.
    Format output STRICTLY as JSON: {{"role": "Data Analyst", "location": "Taguig"}}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        # If this fails now, we will see exactly why!
        st.error(f"Gemini API Error: {e}")
        return {"role": "", "location": ""}

def get_job_urls_from_google(role, location):
    query = f'site:jobstreet.com.ph OR site:indeed.com "{role}" "{location}" "apply"'
    url = f"https://serpapi.com/search.json?q={urllib.parse.quote(query)}&api_key={SERPAPI_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return [result['link'] for result in response.json().get('organic_results', [])]
    except requests.exceptions.RequestException as e:
        st.error(f"Search API Error: {e}")
        return []

def filter_new_urls(url_list):
    if not url_list or not supabase_client: return url_list
    try:
        response = supabase_client.table("processed_jobs").select("url").in_("url", url_list).execute()
        existing_urls = {row['url'] for row in response.data}
        return [url for url in url_list if url not in existing_urls]
    except Exception:
        return url_list 

def scrape_with_firecrawl(url):
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
    payload = {"url": url, "formats": ["markdown"]}
    try:
        response = requests.post("https://api.firecrawl.dev/v1/scrape", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json().get("data", {}).get("markdown", "")
    except Exception:
        return ""

def analyze_job_description(markdown_text, user_skills):
    """Uses Gemini with Chain-of-Thought reasoning to evaluate the job."""
    if not markdown_text: return None
    
    prompt = f"""
    You are a technical career assistant evaluating a job posting. 
    User's target skills: {', '.join(user_skills)}
    Job Description: {markdown_text[:3000]}
    
    Use Chain-of-Thought reasoning.
    1. Identify Job Title, Company, Location.
    2. Identify all technical skills required.
    3. Compare to User's target skills.
    4. Assign a "match_score" (0 to 100).
    
    Format STRICTLY as JSON: {{"title": "...", "company": "...", "location": "...", "tech_skills_found": "...", "reasoning": "...", "match_score": 85}}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception:
        return None

def save_job_to_memory(url, title, company):
    if not supabase_client: return
    try:
        supabase_client.table("processed_jobs").insert({"url": url, "job_title": title, "company_name": company}).execute()
    except:
        pass


# --- 5. Frontend UI Routing ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["💬 Chat with JobSearch AI", "📁 Generated CSVs", "📄 My Resume & Skills"])
st.sidebar.markdown("---")


# ==========================================
# TAB 1: Main Chatbot Interface
# ==========================================
if page == "💬 Chat with JobSearch AI":
    st.title("🤖 Job Search AI Assistant")
    
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("E.g., Find me Data Analyst roles in Taguig requiring Python and SQL"):
        
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state['messages'].append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            search_params = extract_search_params(prompt)
            role = search_params.get("role")
            location = search_params.get("location")
            
            if role:
                with st.spinner(f"Agent Action: Searching web for {role} in {location}..."):
                    raw_urls = get_job_urls_from_google(role, location)
                    new_urls = filter_new_urls(raw_urls)
                    
                    if new_urls:
                        final_results = []
                        progress_bar = st.progress(0)
                        
                        for index, url in enumerate(new_urls):
                            markdown = scrape_with_firecrawl(url)
                            parsed_data = analyze_job_description(markdown, st.session_state['user_skills'])
                            
                            if parsed_data and parsed_data.get('match_score', 0) > 40:
                                parsed_data['url'] = url
                                final_results.append(parsed_data)
                                save_job_to_memory(url, parsed_data.get('title', 'Unknown'), parsed_data.get('company', 'Unknown'))
                                
                            progress_bar.progress((index + 1) / len(new_urls))
                        
                        progress_bar.empty()
                        
                        if final_results:
                            df = pd.DataFrame(final_results)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_role = role.replace(" ", "_")
                            filename = f"jobs_{safe_role}_{timestamp}.csv"
                            df.to_csv(os.path.join("saved_csvs", filename), index=False)
                            
                            response_text = f"I scanned the web and found **{len(final_results)}** new postings matching your profile! I have saved the details to the **Generated CSVs** tab."
                            st.markdown(response_text)
                            st.dataframe(df[['title', 'company', 'location', 'match_score', 'url']], column_config={"url": st.column_config.LinkColumn("Apply")})
                        else:
                            response_text = "I processed the latest postings, but none scored high enough to match your skills today."
                            st.markdown(response_text)
                    else:
                        response_text = "No new job URLs found today. Filtered out duplicates via database memory."
                        st.markdown(response_text)
            else:
                response_text = "I'm ready! Just give me a job title and a location to start searching."
                st.markdown(response_text)
                
        st.session_state['messages'].append({"role": "assistant", "content": response_text})


# ==========================================
# TAB 2: Generated CSV Repository
# ==========================================
elif page == "📁 Generated CSVs":
    st.title("📁 Saved Job Matches")
    st.write("Access your daily compiled job postings here.")
    
    csv_files = [f for f in os.listdir("saved_csvs") if f.endswith('.csv')]
    
    if not csv_files:
        st.info("No CSVs generated yet. Run a search in the chat to create one!")
    else:
        for file in sorted(csv_files, reverse=True): 
            file_path = os.path.join("saved_csvs", file)
            df = pd.read_csv(file_path)
            
            with st.expander(f"📄 {file}"):
                st.dataframe(df)
                with open(file_path, "rb") as f:
                    st.download_button(label=f"Download {file}", data=f, file_name=file, mime="text/csv", key=file)


# ==========================================
# TAB 3: Resume & Skill Context
# ==========================================
elif page == "📄 My Resume & Skills":
    st.title("📄 Job Profile")
    st.write("Update your core skills so the agent knows exactly what you are capable of.")
    
    st.subheader("Current Core Skills")
    updated_skills = st.multiselect(
        "Edit the technical skills the agent should match against:",
        ["Python", "SQL", "Tableau", "Power BI", "Excel", "R", "C++", "Apex", "React"],
        default=st.session_state['user_skills']
    )
    
    if updated_skills != st.session_state['user_skills']:
        st.session_state['user_skills'] = updated_skills
        st.success("Skills updated! The agent will use this new context for future searches.")
        
    st.markdown("---")
    st.subheader("Upload Resume (PDF)")
    uploaded_file = st.file_uploader("Upload a PDF to automatically extract skills (Coming Soon).", type=["pdf"])
    
    if uploaded_file is not None:
        with st.spinner("Agent is reading your resume..."):
            st.success("Resume uploaded successfully! (PDF Parsing Logic can be added here)")