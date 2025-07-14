import requests
from bs4 import BeautifulSoup
from groq import Groq
import time
import re
from urllib.parse import urljoin, urlparse
import json
from typing import Optional, Dict, List

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
        print(f"🔍 Trying multiple search methods for {company_name}...")
        
        # Method 1: Try common domain patterns first
        website = self._try_common_domains(company_name)
        if website:
            print(f"✅ Found via domain pattern: {website}")
            return website
        
        # Method 2: Try DuckDuckGo search (more scraping-friendly)
        website = self._search_duckduckgo(company_name)
        if website:
            print(f"✅ Found via DuckDuckGo: {website}")
            return website
        
        # Method 3: Try alternative Google search approach
        website = self._search_google_alternative(company_name)
        if website:
            print(f"✅ Found via Google: {website}")
            return website
        
        return None
    
    def _try_common_domains(self, company_name: str) -> Optional[str]:
        """
        Try common domain patterns for the company
        """
        print("🔗 Trying common domain patterns...")
        
        # Clean company name
        clean_name = company_name.lower().replace(' ', '').replace('.', '').replace(',', '').replace('-', '')
        
        # Common domain patterns
        patterns = [
            f"https://www.{clean_name}.com",
            f"https://{clean_name}.com",
            f"https://www.{clean_name}.ai",
            f"https://{clean_name}.ai",
            f"https://www.{clean_name}.io",
            f"https://{clean_name}.io",
            f"https://www.{clean_name}.co",
            f"https://{clean_name}.co",
            f"https://www.{clean_name}.org",
            f"https://{clean_name}.org",
        ]
        
        # Also try with original spacing replaced by hyphens
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
        Search using DuckDuckGo (more scraping-friendly)
        """
        print("🦆 Searching via DuckDuckGo...")
        try:
            search_query = f"{company_name} official website"
            ddg_url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
            
            response = requests.get(ddg_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find search result links in DuckDuckGo
            links = soup.find_all('a', class_='result__a')
            
            for link in links[:5]:
                if link.get('href'):
                    url = link.get('href')
                    if self._is_likely_company_website(url, company_name):
                        # Test if URL is accessible
                        try:
                            test_response = requests.head(url, headers=self.headers, timeout=5)
                            if test_response.status_code == 200:
                                return url
                        except:
                            continue
            
            return None
            
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return None
    
    def _search_google_alternative(self, company_name: str) -> Optional[str]:
        """
        Alternative Google search approach
        """
        print("🔍 Trying alternative Google search...")
        try:
            # Use a different approach - search for the company and look in the page
            search_query = f"{company_name} company website"
            
            # Try multiple search variations
            variations = [
                f"{company_name} official site",
                f"{company_name} homepage",
                f"{company_name} corporate website",
                company_name
            ]
            
            for query in variations:
                try:
                    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=10"
                    response = requests.get(url, headers=self.headers, timeout=10)
                    
                    if response.status_code == 200:
                        # Look for URLs in the response text using regex
                        import re
                        urls = re.findall(r'https?://[^\s<>"]+', response.text)
                        
                        for found_url in urls:
                            # Clean the URL
                            found_url = found_url.split('&')[0].split('#')[0]
                            if self._is_likely_company_website(found_url, company_name):
                                try:
                                    test_response = requests.head(found_url, headers=self.headers, timeout=5)
                                    if test_response.status_code == 200:
                                        return found_url
                                except:
                                    continue
                    
                    time.sleep(1)  # Be respectful with requests
                    
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Alternative Google search error: {e}")
            return None
    
    def _is_likely_company_website(self, url: str, company_name: str) -> bool:
        """
        Check if URL is likely the company's official website
        """
        # Skip social media, job boards, news sites, etc.
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
        
        # Check if company name appears in domain
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
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            content = {
                'title': '',
                'description': '',
                'about': '',
                'products': '',
                'services': '',
                'main_content': ''
            }
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                content['title'] = title_tag.get_text().strip()
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content['description'] = meta_desc.get('content', '').strip()
            
            # Look for about sections
            about_sections = soup.find_all(['section', 'div'], 
                                         class_=re.compile(r'about|mission|vision|story', re.I))
            about_text = []
            for section in about_sections:
                text = section.get_text().strip()
                if len(text) > 50:  # Filter out short snippets
                    about_text.append(text)
            content['about'] = ' '.join(about_text[:3])  # Limit to first 3 sections
            
            # Look for products/services sections
            product_sections = soup.find_all(['section', 'div'], 
                                           class_=re.compile(r'product|service|solution|feature', re.I))
            product_text = []
            for section in product_sections:
                text = section.get_text().strip()
                if len(text) > 30:
                    product_text.append(text)
            content['products'] = ' '.join(product_text[:3])
            
            # Extract main content from paragraphs
            paragraphs = soup.find_all('p')
            main_text = []
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 20:  # Filter out short paragraphs
                    main_text.append(text)
            content['main_content'] = ' '.join(main_text[:10])  # Limit content
            
            return content
            
        except Exception as e:
            print(f"Error scraping website: {e}")
            return {}
    
    def analyze_with_llm(self, company_name: str, website_content: Dict[str, str]) -> str:
        """
        Use Llama via Groq to analyze website content and generate company summary
        """
        try:
            # Prepare content for LLM
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

            Keep the analysis professional, accurate, and focused on information that would be valuable for tailoring a cover letter. If certain sections cannot be determined from the content, mention that explicitly.
            """
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a professional research assistant helping someone research companies for job applications. Provide accurate, well-structured analysis based on the provided website content."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-70b-8192",  # You can also use "llama3-8b-8192" for faster responses
                max_tokens=1024,
                temperature=0.7
            )
            
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error analyzing with LLM: {e}")
            return f"Error occurred during analysis: {str(e)}"
    
    def research_company(self, company_name: str) -> Dict[str, str]:
        """
        Main method to research a company and generate summary
        """
        print(f"🔍 Researching {company_name}...")
        
        # Step 1: Find company website
        print("📡 Searching for company website...")
        website_url = self.search_company_website(company_name)
        
        if not website_url:
            return {
                'error': f"Could not find official website for {company_name}",
                'company_name': company_name
            }
        
        print(f"✅ Found website: {website_url}")
        
        # Step 2: Scrape website content
        print("🕷️ Scraping website content...")
        website_content = self.scrape_website_content(website_url)
        
        if not website_content:
            return {
                'error': f"Could not scrape content from {website_url}",
                'company_name': company_name,
                'website_url': website_url
            }
        
        # Step 3: Analyze with LLM
        print("🤖 Analyzing content with LLM...")
        analysis = self.analyze_with_llm(company_name, website_content)
        
        return {
            'company_name': company_name,
            'website_url': website_url,
            'analysis': analysis,
            'raw_content': website_content
        }

def main():
    """
    Example usage of the CompanyResearcher with Groq/Llama
    """
    # You need to set your Groq API key here
    GROQ_API_KEY = "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"
    
    # Alternative: Use environment variable
    # import os
    # GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    if not (GROQ_API_KEY == "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"):
        print("⚠️ Please set your Groq API key in the script or environment variable")
        print("📝 Get your free API key at: https://console.groq.com/keys")
        return
    
    researcher = CompanyResearcher(GROQ_API_KEY)
    
    # Get company name from user input
    company_name = input("Enter the startup/company name: ").strip()
    
    if not company_name:
        print("Please enter a valid company name")
        return
    
    # Research the company
    result = researcher.research_company(company_name)
    
    # Display results
    print("\n" + "="*80)
    print(f"📊 RESEARCH RESULTS FOR: {result['company_name'].upper()}")
    print("="*80)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"🌐 Website: {result['website_url']}")
    print("\n📋 COMPANY ANALYSIS:")
    print("-" * 40)
    print(result['analysis'])
    
    # Save results to file
    filename = f"{company_name.replace(' ', '_').lower()}_research.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {filename}")
    print("\n💡 Use this analysis to tailor your cover letter!")

if __name__ == "__main__":
    main()