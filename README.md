#  Cold Outreach Automation Tool

An intelligent automation tool that streamlines your entire cold outreach process - from company research to personalized email generation and delivery.


##  Features

- **Intelligent Company Research**: Automatically finds company websites and scrapes relevant information
- **Founder Discovery**: Identifies company founders and key personnel using AI
- **AI-Powered Email Generation**: Creates personalized cold emails using Groq's Llama models
- **Gmail Integration**: Send emails directly through the app with secure authentication
- **Resume Processing**: Extracts and analyzes your resume content from PDF files
- **Flexible Input**: Supports both company research mode and manual job description mode

## Deployment
- Deployed using streamlit cloud at https://cold-outreach.streamlit.app/

##  Prerequisites

Before you begin, ensure you have the following:

- **Python 3.8 or higher** installed on your system
- **Git** for cloning the repository
- **A Groq API key** (free from [console.groq.com](https://console.groq.com))
- **Gmail account** with 2FA enabled (for email sending)
- **Code editor** (VS Code, PyCharm, etc.)

##  Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/ayushhsinghhh/Cold-Outreach.git
```

### Step 2: Create Virtual Environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Secrets Configuration

#### 4.1 Create Streamlit Secrets Directory

```bash
mkdir .streamlit
```

#### 4.2 Create Secrets File

Create a file named `secrets.toml` inside the `.streamlit` folder:

**Windows:**
```bash
type nul > .streamlit\secrets.toml
```

**macOS/Linux:**
```bash
touch .streamlit/secrets.toml
```

#### 4.3 Configure Your Secrets

Open `.streamlit/secrets.toml` in your text editor and add the following:

```toml
# Groq API Configuration
GROQ_API_KEY = "your_groq_api_key_here"

# Gmail Configuration (Method 1: App Password - Recommended)
GMAIL_EMAIL = "your_email@gmail.com"
GMAIL_APP_PASSWORD = "your_16_character_app_password"

# Gmail Configuration (Method 2: OAuth - Alternative)
GMAIL_CLIENT_ID = "your_gmail_client_id"
GMAIL_PROJECT_ID = "your_gmail_project_id"
GMAIL_CLIENT_SECRET = "your_gmail_client_secret"
```

##  Getting Your API Keys

### Groq API Key (Required)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to "API Keys"
4. Create a new API key
5. Copy the key and paste it in `secrets.toml`

### Gmail App Password (Recommended Method)

1. **Enable 2-Factor Authentication** on your Gmail account
2. Go to [Google Account Settings](https://myaccount.google.com/)
3. Navigate to **Security** → **2-Step Verification**
4. Scroll down to **App passwords**
5. Click **Select app** → Choose "Mail"
6. Click **Select device** → Choose "Other (custom name)" → Type "Cold Outreach Tool"
7. Click **Generate**
8. Copy the 16-character password (spaces will be removed automatically)
9. Use this in your `secrets.toml` file

### Gmail OAuth (Alternative Method)

If you prefer OAuth instead of app passwords:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download the credentials and extract the required fields

##  Running the Application

### Local Development

1. **Ensure your virtual environment is activated**
2. **Run the Streamlit app:**

```bash
streamlit run app.py
```

