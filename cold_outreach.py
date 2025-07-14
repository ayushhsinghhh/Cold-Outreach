import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
import time
import re
from urllib.parse import urljoin, urlparse
import json
import tempfile
from typing import Optional, Dict, List
import pdfplumber
from docx import Document
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle

# Gmail API Scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class CompanyResearcher:
    def __init__(self, groq_api_key: str):
        """
        Initialize the Company Researcher with Groq API key for Llama models
        """
        self.groq_api_key = groq_api_key
        self.groq_client = Groq(api_key=groq_api_key)
        
        # Headers to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_company_website(self, company_name: str) -> Optional[str]:
        """
        Search for company website using multiple methods
        """
        # Method 1: Try common domain patterns first
        website = self._try_common_domains(company_name)
        if website:
            return website
        
        # Method 2: Try DuckDuckGo search
        website = self._search_duckduckgo(company_name)
        if website:
            return website
        
        return None
    
    def _try_common_domains(self, company_name: str) -> Optional[str]:
        """
        Try common domain patterns for the company
        """
        clean_name = company_name.lower().replace(' ', '').replace('.', '').replace(',', '').replace('-', '')
        
        patterns = [
            f"https://www.{clean_name}.com",
            f"https://{clean_name}.com",
            f"https://www.{clean_name}.ai",
            f"https://{clean_name}.ai",
            f"https://www.{clean_name}.io",
            f"https://{clean_name}.io",
            f"https://www.{clean_name}.co",
            f"https://{clean_name}.co",
        ]
        
        hyphen_name = company_name.lower().replace(' ', '-').replace('.', '').replace(',', '')
        patterns.extend([
            f"https://www.{hyphen_name}.com",
            f"https://{hyphen_name}.com",
            f"https://www.{hyphen_name}.ai",
            f"https://{hyphen_name}.ai",
            f"https://www.{hyphen_name}.io",
            f"https://{hyphen_name}.io",
        ])
        
        for pattern in patterns:
            try:
                response = requests.head(pattern, headers=self.headers, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return pattern
            except:
                continue
        
        return None
    
    def _search_duckduckgo(self, company_name: str) -> Optional[str]:
        """
        Search using DuckDuckGo
        """
        try:
            search_query = f"{company_name} official website"
            ddg_url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
            
            response = requests.get(ddg_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = soup.find_all('a', class_='result__a')
            
            for link in links[:5]:
                if link.get('href'):
                    url = link.get('href')
                    if self._is_likely_company_website(url, company_name):
                        try:
                            test_response = requests.head(url, headers=self.headers, timeout=5)
                            if test_response.status_code == 200:
                                return url
                        except:
                            continue
            
            return None
            
        except Exception as e:
            st.error(f"DuckDuckGo search error: {e}")
            return None
    
    def _is_likely_company_website(self, url: str, company_name: str) -> bool:
        """
        Check if URL is likely the company's official website
        """
        excluded_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'glassdoor.com', 'indeed.com', 'crunchbase.com', 'wikipedia.org',
            'youtube.com', 'bloomberg.com', 'reuters.com', 'techcrunch.com'
        ]
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        for excluded in excluded_domains:
            if excluded in domain:
                return False
        
        company_words = company_name.lower().split()
        for word in company_words:
            if len(word) > 3 and word in domain:
                return True
        
        return True
    
    def scrape_website_content(self, url: str) -> Dict[str, str]:
        """
        Scrape and extract relevant content from company website
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            content = {
                'title': '',
                'description': '',
                'about': '',
                'products': '',
                'main_content': ''
            }
            
            title_tag = soup.find('title')
            if title_tag:
                content['title'] = title_tag.get_text().strip()
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content['description'] = meta_desc.get('content', '').strip()
            
            about_sections = soup.find_all(['section', 'div'], 
                                         class_=re.compile(r'about|mission|vision|story', re.I))
            about_text = []
            for section in about_sections:
                text = section.get_text().strip()
                if len(text) > 50:
                    about_text.append(text)
            content['about'] = ' '.join(about_text[:3])
            
            product_sections = soup.find_all(['section', 'div'], 
                                           class_=re.compile(r'product|service|solution|feature', re.I))
            product_text = []
            for section in product_sections:
                text = section.get_text().strip()
                if len(text) > 30:
                    product_text.append(text)
            content['products'] = ' '.join(product_text[:3])
            
            paragraphs = soup.find_all('p')
            main_text = []
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 20:
                    main_text.append(text)
            content['main_content'] = ' '.join(main_text[:10])
            
            return content
            
        except Exception as e:
            st.error(f"Error scraping website: {e}")
            return {}
    
    def find_founders(self, company_name: str) -> List[str]:
        """
        Search for founder names using multiple search approaches
        """
        try:
            # Try Google first (for AI Overview content)
            search_query = f"{company_name} founder"
            founder_content = self._search_google_for_founders(search_query)
            
            # If Google fails, try DuckDuckGo
            if not founder_content:
                founder_content = self._search_duckduckgo_for_founders(search_query)
            
            if not founder_content:
                return []
            
            # Use AI to extract founder names from search results
            prompt = f"""
            Based on the following search results about {company_name}, identify the founders or co-founders of the company.
            
            Extract the FULL NAMES (first and last name) of people who founded the company. 
            Return ONLY the complete names, one per line, without titles or additional text.
            If you find a first name, try to find the corresponding last name in the content.
            If no clear founder names are found, return "No founders identified".
            
            Examples of good responses:
            - "John Smith"
            - "Jane Doe"
            - "Robert Johnson"
            
            Examples of bad responses:
            - "John" (incomplete)
            - "CEO Smith" (contains title)
            - "The founder" (not a name)
            
            Search Results:
            {founder_content}
            
            Complete founder names only:
            """
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are extracting complete founder names from search results. Always return full names (first and last name together), never just first names."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-70b-8192",
                max_tokens=256,
                temperature=0.3
            )
            
            response = chat_completion.choices[0].message.content.strip()
            
            if "No founders identified" in response:
                return []
            
            # Parse names from response
            names = [name.strip() for name in response.split('\n') if name.strip() and len(name.strip()) > 2]
            
            # More lenient filtering - accept single names if they're reasonable length
            filtered_names = []
            for name in names:
                # Skip if contains common non-name words
                if any(word in name.lower() for word in ['team', 'company', 'founded', 'the', 'inc', 'llc', 'ltd', 'corporation', 'group']):
                    continue
                
                # Remove any titles
                clean_name = re.sub(r'\b(CEO|CTO|CFO|COO|President|Director|Mr\.|Ms\.|Dr\.|Prof\.)\b', '', name, flags=re.IGNORECASE).strip()
                
                if clean_name and len(clean_name) > 2:
                    # Prefer full names (first + last) but accept reasonable single names too
                    if ' ' in clean_name:
                        # Full name - preferred
                        filtered_names.append(clean_name)
                    elif len(clean_name) >= 4 and clean_name.isalpha():
                        # Single name but reasonable length and all letters
                        filtered_names.append(clean_name)
            
            return filtered_names
            
        except Exception as e:
            return []
    
    def _search_google_for_founders(self, query: str) -> Optional[str]:
        """
        Search Google and try to extract content including AI Overview
        """
        try:
            # Use Google search with specific headers
            google_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            google_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            response = requests.get(google_url, headers=google_headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for AI Overview content (multiple possible selectors)
                ai_overview_selectors = [
                    '[data-attrid="kc:/local:one line description"]',
                    '[data-attrid="description"]',
                    'div[data-md]',
                    '.kno-rdesc',
                    '.kno-desc',
                    '.LGOjhe',
                    'div[data-async-context]'
                ]
                
                content = ""
                
                # Try to find AI Overview or knowledge panel content
                for selector in ai_overview_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text().strip()
                        if text and len(text) > 20 and query.split()[0].lower() in text.lower():
                            content += text + " "
                
                # Also look in general search result snippets
                if not content:
                    result_snippets = soup.find_all(['span', 'div'], class_=re.compile(r'st|s3v9rd|VwiC3b'))
                    for snippet in result_snippets[:3]:
                        text = snippet.get_text().strip()
                        if text and len(text) > 20:
                            content += text + " "
                
                # Look for any div that contains the company name and "founder"
                if not content:
                    all_divs = soup.find_all(['div', 'span', 'p'])
                    for div in all_divs:
                        text = div.get_text().strip()
                        if (query.split()[0].lower() in text.lower() and 
                            'founder' in text.lower() and 
                            len(text) > 30 and len(text) < 500):
                            content += text + " "
                            break
                
                return content.strip() if content.strip() else None
            
            return None
            
        except Exception as e:
            print(f"Error searching Google for founders: {e}")
            return None
    
    def _search_duckduckgo_for_founders(self, query: str) -> Optional[str]:
        """
        Search for founder information using DuckDuckGo
        """
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            
            response = requests.get(ddg_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for instant answer or snippet content first
            instant_answer = soup.find('div', class_='zci')
            if instant_answer:
                text = instant_answer.get_text().strip()
                if text and len(text) > 20:
                    return text
            
            # Get first search result content
            results = soup.find_all('a', class_='result__a')[:2]  # Try first 2 results
            
            content = ""
            for result in results:
                if result.get('href'):
                    url = result.get('href')
                    
                    try:
                        # Get the content from this result
                        page_response = requests.get(url, headers=self.headers, timeout=8)
                        page_soup = BeautifulSoup(page_response.content, 'html.parser')
                        
                        # Remove scripts and styles
                        for script in page_soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text content, focusing on paragraphs
                        paragraphs = page_soup.find_all('p')
                        page_text = ' '.join([p.get_text().strip() for p in paragraphs[:5]])
                        
                        if page_text and len(page_text) > 50:
                            content = page_text
                            break
                        
                    except:
                        continue
            
            return content if content else None
            
        except Exception as e:
            print(f"Error searching DuckDuckGo for founders: {e}")
            return None
    
    def analyze_with_llm(self, company_name: str, website_content: Dict[str, str]) -> str:
        """
        Use Llama via Groq to analyze website content and generate company summary
        """
        try:
            content_text = f"""
            Company: {company_name}
            Website Title: {website_content.get('title', '')}
            Meta Description: {website_content.get('description', '')}
            About Section: {website_content.get('about', '')}
            Products/Services: {website_content.get('products', '')}
            Main Content: {website_content.get('main_content', '')}
            """
            
            prompt = f"""
            Based on the following website content about {company_name}, provide a comprehensive analysis in the following format:

            **Company Overview:**
            [2-3 sentences describing what the company does, their mission, and their position in the market]

            **Key Products/Services:**
            [List the main products or services offered, with brief descriptions]

            **Industry & Focus:**
            [What industry they operate in and their main focus areas]

            **Company Culture & Values:**
            [Any insights about their culture, values, or approach to business]

            **Recent Developments:**
            [Any notable achievements, growth, or recent developments mentioned]

            Website Content:
            {content_text}

            Keep the analysis professional, accurate, and focused on information that would be valuable for tailoring a cover letter.
            """
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a professional research assistant helping someone research companies for job applications."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-70b-8192",
                max_tokens=1024,
                temperature=0.7
            )
            
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error occurred during analysis: {str(e)}"

def extract_resume_text(pdf_file):
    """Extract text from uploaded PDF resume"""
    text = ''
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    return text.strip()

def extract_text_from_docx(file):
    """Extract text from uploaded DOCX file"""
    try:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        st.error(f"Error reading DOCX template: {e}")
        return ""

def load_prompt_template(uploaded_template=None):
    """Load the prompt template for email generation"""
    default_prompt = """
    You are an expert cold email writer. Write a professional, compelling cold email for a job application.

    RESUME CONTENT:
    {resume_text}

    COMPANY RESEARCH:
    {company_info}

    JOB DESCRIPTION:
    {jd_text}

    EMAIL TEMPLATE (if provided):
    {email_template}

    IMPORTANT INSTRUCTIONS:
    - Write ONLY the email content - no introductory text, no explanations
    - Start with "SUBJECT:" followed by a compelling, creative subject line
    - Do not include phrases like "Here is a cold email" or "Below is the email"
    - Make the subject line engaging and specific to the company/role
    - Write in clear, well-structured paragraphs
    - Each paragraph should focus on one main point
    - Use proper spacing between paragraphs
    - Keep it professional but conversational
    - Include specific technical skills that match the role
    - End with a clear call-to-action

    Format EXACTLY like this example:
    SUBJECT: Driving AI Innovation at [Company Name] - [Your Value Proposition]

    Hi [Company] Team,

    [Opening paragraph - express interest and connection to company]

    [Second paragraph - highlight relevant experience and achievements]

    [Third paragraph - explain why you're a good fit and what you can contribute]

    [Closing paragraph - call to action]

    Best regards,
    [Candidate Name]

    Remember: 
    - Create compelling, specific subject lines
    - Write in clear paragraphs with proper spacing
    - Make each paragraph focused and purposeful
    - Keep the tone professional yet personable
    """
    
    # If template is uploaded, use it
    if uploaded_template is not None:
        return default_prompt
    
    # Otherwise try to load from prompt.txt file
    try:
        with open("prompt.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return default_prompt

def generate_email(groq_api_key: str, resume_text: str, company_info: str, jd_text: str, email_template: str = ""):
    """Generate cold email using Groq API"""
    try:
        client = Groq(api_key=groq_api_key)
        prompt_template = load_prompt_template()
        
        final_prompt = prompt_template.format(
            resume_text=resume_text,
            company_info=company_info,
            jd_text=jd_text,
            email_template=email_template
        )
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are writing a cold email directly as the job candidate. Write ONLY the email content with subject line. Do not include any introductory text, explanations, or meta-commentary. Start directly with 'SUBJECT:' followed by the email content."},
                {"role": "user", "content": final_prompt}
            ],
            model="llama3-70b-8192",
            max_tokens=1024,
            temperature=0.7
        )
        
        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"Error generating email: {e}")
        return ""

def get_gmail_credentials():
    """Get Gmail credentials from Streamlit secrets"""
    try:
        # Try to get from Streamlit secrets
        gmail_creds = {
            "installed": {
                "client_id": st.secrets["GMAIL_CLIENT_ID"],
                "project_id": st.secrets["GMAIL_PROJECT_ID"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": st.secrets["GMAIL_CLIENT_SECRET"],
                "redirect_uris": ["http://localhost"]
            }
        }
        return gmail_creds
    except Exception as e:
        st.error("❌ Gmail credentials not found in secrets. Please configure them in Streamlit Cloud settings.")
        return None

def authenticate_gmail():
    """Authenticate Gmail API using credentials from secrets"""
    creds = None
    
    # Load existing token if available
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.error(f"Error refreshing Gmail token: {e}")
                creds = None
        
        if not creds:
            # Get credentials from secrets
            gmail_creds_dict = get_gmail_credentials()
            if not gmail_creds_dict:
                return None
            
            try:
                # Create temporary credentials file for OAuth flow
                import tempfile
                import json
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(gmail_creds_dict, temp_file)
                    temp_creds_path = temp_file.name
                
                # Use the temporary file for OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(temp_creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Clean up temporary file
                os.unlink(temp_creds_path)
                
            except Exception as e:
                st.error(f"Error during Gmail authentication: {e}")
                return None

        # Save credentials for future use
        try:
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            st.warning(f"Could not save Gmail token: {e}")

    # Build and return Gmail service
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error building Gmail service: {e}")
        return None

def send_email(service, to_email: str, subject: str, body: str):
    """Send email via Gmail API with proper HTML formatting"""
    try:
        # Convert plain text to HTML with proper formatting
        html_body = body.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <p>{html_body}</p>
        </body>
        </html>
        """
        
        # Create multipart message with both plain text and HTML
        message = MIMEMultipart('alternative')
        message['to'] = to_email
        message['subject'] = subject
        
        # Add plain text version
        text_part = MIMEText(body, 'plain')
        message.attach(text_part)
        
        # Add HTML version
        html_part = MIMEText(html_body, 'html')
        message.attach(html_part)
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        sent = service.users().messages().send(
            userId="me", 
            body={'raw': raw}
        ).execute()
        
        return sent['id']
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return None

def get_groq_api_key():
    """Get Groq API key from secrets or user input"""
    # Try to get from Streamlit secrets first
    try:
        return st.secrets["GROQ_API_KEY"]
    except:
        # If not in secrets, ask user for input
        return st.text_input(
            "Groq API Key", 
            type="password",
            help="Get your free API key at: https://console.groq.com/keys"
        )

def main():
    """
    Main Streamlit application
    """
    st.set_page_config(
        page_title="Cold Outreach Automation Tool",
        page_icon="📧",
        layout="wide"
    )
    
    st.title("📧 Cold Outreach Automation Tool")
    st.markdown("*Automate your entire cold outreach process - from company research to email delivery*")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        groq_api_key = get_groq_api_key()
        
        st.markdown("---")
        st.markdown("### 📋 Process Flow:")
        st.markdown("1. 📄 Upload your resume")
        st.markdown("2. 📧 Upload email template (optional)")
        st.markdown("3. 🏢 Research company OR add JD")
        st.markdown("4. 👥 Find founder contacts")
        st.markdown("5. ✍️ Generate personalized email")
        st.markdown("6. 📧 Send via Gmail")
        
        st.markdown("---")
        st.markdown("### 🔗 External Tools:")
        st.markdown("[Apollo.io](https://apollo.io) - Contact search")
        st.markdown("[RocketReach](https://rocketreach.co) - Email finder")
    
    # Main content area
    tab1, tab2 = st.tabs(["📊 Company Research Mode", "📝 Manual JD Mode"])
    
    with tab1:
        st.header("🔍 Company Research Mode")
        
        # Resume and template upload
        col1, col2 = st.columns([1, 1])
        with col1:
            resume_file = st.file_uploader("📄 Upload Resume (PDF)", type=["pdf"], key="resume1")
        with col2:
            email_template_file = st.file_uploader("📧 Upload Email Template (Optional)", type=["txt", "docx"], key="template1")
            if email_template_file:
                st.success(f"✅ Template uploaded: {email_template_file.name}")
        
        # Company name input
        company_name = st.text_input("🏢 Company Name", placeholder="e.g., OpenAI, Tesla")
        
        if st.button("🚀 Research Company", type="primary", use_container_width=True):
            if not groq_api_key:
                st.error("❌ Please add your Groq API key in the sidebar")
                return
            
            if not resume_file or not company_name:
                st.warning("⚠️ Please upload resume and enter company name")
                return
            
            # Single status placeholder for all progress updates
            status_placeholder = st.empty()
            
            # Initialize researcher
            researcher = CompanyResearcher(groq_api_key)
            
            # Step 1: Research company
            status_placeholder.info("🔍 Searching for company website...")
            website_url = researcher.search_company_website(company_name)
            
            if not website_url:
                status_placeholder.error("❌ Could not find company website")
                return
            
            status_placeholder.success(f"✅ Found website: {website_url}")
            time.sleep(0.5)  # Brief pause for user to see
            
            status_placeholder.info("🕷️ Scraping website content...")
            website_content = researcher.scrape_website_content(website_url)
            if not website_content:
                status_placeholder.error("❌ Could not scrape website content")
                return
            
            status_placeholder.success("✅ Website content scraped successfully!")
            time.sleep(0.5)
            
            status_placeholder.info("🤖 Analyzing content with AI...")
            analysis = researcher.analyze_with_llm(company_name, website_content)
            
            status_placeholder.success("✅ AI analysis completed!")
            time.sleep(0.5)
            
            status_placeholder.info("👥 Searching for founder information...")
            founders = researcher.find_founders(company_name)
            
            # Clear status and show final result
            status_placeholder.success("✅ Research completed!")
            
            # Store results in session state
            st.session_state.company_research = {
                'company_name': company_name,
                'website_url': website_url,
                'analysis': analysis,
                'founders': founders,
                'resume_file': resume_file,
                'email_template_file': email_template_file
            }
            
            # Display results
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info(f"🌐 **Website:** {website_url}")
                
                with st.expander("📊 Company Analysis", expanded=True):
                    st.markdown(analysis)
            
            with col2:
                st.subheader("👥 Founders Found")
                if founders:
                    for founder in founders:
                        st.write(f"• **{founder}**")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            apollo_url = f"https://www.apollo.io/"
                            st.link_button("🔍 Apollo", apollo_url, use_container_width=True)
                        
                        with col_b:
                            rocketreach_url = f"https://rocketreach.co/dashboard"
                            st.link_button("🚀 RocketReach", rocketreach_url, use_container_width=True)
                else:
                    st.info("No founders identified from search")
                    
                    # Manual search links
                    apollo_url = f"https://apollo.io/companies/{company_name.replace(' ', '-').lower()}"
                    rocketreach_url = f"https://rocketreach.co/search?company={company_name.replace(' ', '%20')}"
                    
                    st.link_button("🔍 Search Apollo", apollo_url, use_container_width=True)
                    st.link_button("🚀 Search RocketReach", rocketreach_url, use_container_width=True)
    
    with tab2:
        st.header("📝 Manual Job Description Mode")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            resume_file_manual = st.file_uploader("📄 Upload Resume (PDF)", type=["pdf"], key="resume2")
        with col2:
            email_template_file_manual = st.file_uploader("📧 Upload Email Template (Optional)", type=["txt", "docx"], key="template2")
            if email_template_file_manual:
                st.success(f"✅ Template uploaded: {email_template_file_manual.name}")
        
        company_name_manual = st.text_input("🏢 Company Name (Optional)", key="company_manual")
        
        jd_text = st.text_area("💼 Paste Job Description", height=200, key="jd_manual")
        
        if st.button("💾 Prepare Email Generation", type="primary", use_container_width=True):
            if not resume_file_manual or not jd_text:
                st.warning("⚠️ Please upload resume and add job description")
                return
            
            st.session_state.manual_mode = {
                'resume_file': resume_file_manual,
                'company_name': company_name_manual or "the company",
                'jd_text': jd_text,
                'analysis': f"Job opportunity at {company_name_manual or 'the company'}",
                'email_template_file': email_template_file_manual
            }
    
    # Email generation section
    if 'company_research' in st.session_state or 'manual_mode' in st.session_state:
        st.markdown("---")
        st.header("✍️ Email Generation & Sending")
        
        # Determine which mode we're in
        if 'company_research' in st.session_state:
            data = st.session_state.company_research
            mode = "research"
        else:
            data = st.session_state.manual_mode
            mode = "manual"
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🤖 Generate Cold Email", type="primary", use_container_width=True):
                if not groq_api_key:
                    st.error("❌ Please add your Groq API key")
                    return
                
                # Extract resume text
                resume_text = extract_resume_text(data['resume_file'])
                
                # Extract email template if provided
                email_template = ""
                if data.get('email_template_file'):
                    template_file = data['email_template_file']
                    try:
                        if template_file.name.endswith('.txt'):
                            # For text files, read as string
                            template_file.seek(0)  # Reset file pointer
                            email_template = template_file.read().decode("utf-8")
                        elif template_file.name.endswith('.docx'):
                            # For DOCX files, use the helper function
                            template_file.seek(0)  # Reset file pointer
                            email_template = extract_text_from_docx(template_file)
                    except Exception as e:
                        st.warning(f"Could not read email template: {e}")
                        email_template = ""
                
                # Prepare company info
                if mode == "research":
                    company_info = f"Company: {data['company_name']}\nWebsite: {data['website_url']}\n\nAnalysis:\n{data['analysis']}"
                    jd_text = f"Position at {data['company_name']} - based on company research"
                else:
                    company_info = f"Company: {data['company_name']}\n\nJob posting analysis:\n{data['analysis']}"
                    jd_text = data['jd_text']
                
                # Generate email
                email_content = generate_email(groq_api_key, resume_text, company_info, jd_text, email_template)
                
                if email_content:
                    st.session_state.generated_email = email_content
        
        with col2:
            recipient_email = st.text_input("📧 Recipient Email", placeholder="founder@company.com")
        
        # Display generated email
        if 'generated_email' in st.session_state:
            st.subheader("📧 Generated Email")
            
            email_content = st.session_state.generated_email
            
            # Clean the email content more aggressively
            def clean_email_content(content):
                # Remove common AI artifacts and instruction text
                content = re.sub(r'Here is a cold email.*?:', '', content, flags=re.IGNORECASE)
                content = re.sub(r'Below is.*?email.*?:', '', content, flags=re.IGNORECASE)
                content = re.sub(r'I.*?generated.*?email.*?:', '', content, flags=re.IGNORECASE)
                content = re.sub(r'Based on.*?information.*?:', '', content, flags=re.IGNORECASE)
                content = re.sub(r'Here.*?personalized.*?email.*?:', '', content, flags=re.IGNORECASE)
                
                # Remove any remaining instructional phrases
                content = re.sub(r'^\s*Here.*?:\s*', '', content, flags=re.MULTILINE | re.IGNORECASE)
                content = re.sub(r'^\s*Below.*?:\s*', '', content, flags=re.MULTILINE | re.IGNORECASE)
                
                # Clean up extra whitespace and line breaks
                content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 line breaks
                content = content.strip()
                
                return content
            
            # Clean the content first
            email_content = clean_email_content(email_content)
            
            # Parse subject and body more robustly
            subject_part = ""
            body_part = ""
            
            if "SUBJECT:" in email_content:
                # Split on SUBJECT: and handle the content after it
                lines = email_content.split('\n')
                subject_line = ""
                body_lines = []
                found_subject = False
                skip_next_empty = False
                
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped.startswith("SUBJECT:") and not found_subject:
                        # Extract everything after "SUBJECT:" on this line
                        subject_line = line_stripped.replace("SUBJECT:", "").strip()
                        found_subject = True
                        skip_next_empty = True
                    elif found_subject:
                        if skip_next_empty and not line_stripped:
                            skip_next_empty = False
                            continue
                        if line_stripped:  # Only add non-empty lines
                            body_lines.append(line_stripped)
                        else:
                            body_lines.append("")  # Preserve paragraph breaks
                
                # Use the extracted subject or fallback to default
                subject_part = subject_line if subject_line else f"Application for position at {data['company_name']}"
                body_part = '\n'.join(body_lines).strip()
                
                # Additional check: if no subject found, look for "Subject:" (without colon)
                if not subject_line:
                    for line in lines:
                        line_stripped = line.strip()
                        if line_stripped.lower().startswith("subject"):
                            # Try to extract subject from various formats
                            if ":" in line_stripped:
                                potential_subject = line_stripped.split(":", 1)[1].strip()
                                if potential_subject and len(potential_subject) > 5:
                                    subject_part = potential_subject
                                    break
            else:
                # No SUBJECT: marker found, use default subject and full content as body
                subject_part = f"Application for position at {data['company_name']}"
                body_part = email_content
                
                # Try one more time to find a subject in the content
                lines = email_content.split('\n')
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    if line_stripped.lower().startswith("subject"):
                        if ":" in line_stripped:
                            potential_subject = line_stripped.split(":", 1)[1].strip()
                            if potential_subject and len(potential_subject) > 5:
                                subject_part = potential_subject
                                # Remove this line from body
                                remaining_lines = lines[i+1:]
                                body_part = '\n'.join(remaining_lines).strip()
                                break
            
            # Final cleaning of body content
            body_part = clean_email_content(body_part)
            
            # Remove any remaining EMAIL BODY: markers and subject lines from body
            body_part = re.sub(r'EMAIL BODY:\s*', '', body_part, flags=re.IGNORECASE)
            body_part = re.sub(r'^\s*Email:\s*', '', body_part, flags=re.MULTILINE | re.IGNORECASE)
            body_part = re.sub(r'^\s*Subject:.*$', '', body_part, flags=re.MULTILINE | re.IGNORECASE)
            
            # Ensure proper email formatting with line breaks
            if body_part:
                # Split into paragraphs and clean them up
                paragraphs = body_part.split('\n\n')
                formatted_paragraphs = []
                
                for para in paragraphs:
                    if para.strip():
                        # Clean up each paragraph - remove extra line breaks within paragraphs
                        clean_para = para.replace('\n', ' ').strip()
                        # Remove extra spaces
                        clean_para = re.sub(r'\s+', ' ', clean_para)
                        if clean_para:
                            formatted_paragraphs.append(clean_para)
                
                # Join paragraphs with double line breaks for proper email formatting
                body_part = '\n\n'.join(formatted_paragraphs)
                
                # Ensure it starts with a proper greeting if it doesn't
                if body_part and not body_part.startswith(('Hi ', 'Hello ', 'Dear ', 'Greetings')):
                    # Find the first sentence that looks like a greeting
                    lines = body_part.split('\n')
                    if lines and not any(greeting in lines[0] for greeting in ['Hi ', 'Hello ', 'Dear ']):
                        # If no greeting found, the content is probably fine as-is
                        pass
            
            # Editable fields
            col1, col2 = st.columns([1, 1])
            with col1:
                subject = st.text_input("Subject Line", value=subject_part, key="email_subject")
            
            with col2:
                if st.button("📧 Send Email", type="primary", disabled=not recipient_email):
                    if not recipient_email:
                        st.warning("⚠️ Please enter recipient email")
                    else:
                        # Final cleaning before sending
                        final_body = body_part.strip()
                        
                        gmail_service = authenticate_gmail()
                        
                        if gmail_service:
                            message_id = send_email(gmail_service, recipient_email, subject, final_body)
                            
                            if message_id:
                                st.success(f"✅ Email sent successfully!")
                                
                                # Show what was actually sent
                                with st.expander("📧 Email Sent Details", expanded=False):
                                    st.write(f"**To:** {recipient_email}")
                                    st.write(f"**Subject:** {subject}")
                                    st.text_area("**Body:**", final_body, height=200, disabled=True)
                            else:
                                st.error("❌ Failed to send email")
                        else:
                            st.error("❌ Gmail authentication failed")
            
            # Email preview
            st.text_area("Email Body Preview", value=body_part, height=300, key="email_body")
            
            # Download option
            email_data = f"Subject: {subject_part}\n\nTo: {recipient_email if recipient_email else '[Recipient Email]'}\n\nBody:\n{body_part}"
            st.download_button(
                "📄 Download Email",
                data=email_data,
                file_name=f"cold_email_{data['company_name'].replace(' ', '_').lower()}.txt",
                mime="text/plain"
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "🚀 Automate your cold outreach and land your dream job!"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()