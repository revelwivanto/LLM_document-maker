# Deployment Guide for AI Document Generator

## Pre-Deployment Checklist

### ✅ Current Status
- [x] Fixed missing import (`streamlit-gsheets`)
- [x] Removed undefined function calls (`execute_ai_task()`)
- [x] Cleaned up debug statements
- [x] Hardcoded URL moved to configuration

### 🔧 Before Deploying

#### 1. **Configure Environment Secrets**
Create a `.streamlit/secrets.toml` file with:

```toml
GEMINI_API = "your-actual-gemini-api-key"
GSHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
APPS_SCRIPT_WEB_APP_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"

[connections.gsheets]
# Add your Google Service Account credentials here
type = "service_account"
# ... (JSON content from Google Cloud)
```

#### 2. **Set Up Google Integration**
- **Google Gemini API**: Enable in Google Cloud, get API key
- **Google Sheets**: Share with service account email
- **Google Apps Script**: Deploy web app endpoint, add ID to secrets

#### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

#### 4. **Test Locally First**
```bash
streamlit run streamlit_app.py
```

---

## Deployment Options

### Option A: Deploy to Streamlit Cloud (Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Deployment ready"
   git push origin master
   ```

2. **Deploy on Streamlit**
   - Go to https://share.streamlit.io/
   - Connect GitHub repo: `revelwivanto/LLM_document-maker`
   - Set branch to `master`
   - In "Advanced settings", add secrets from `.streamlit/secrets.toml`

3. **Live URL**: `https://share.streamlit.io/revelwivanto/LLM_document-maker/master/streamlit_app.py`

### Option B: Deploy to Azure/AWS

**Azure Container Instances:**
```bash
# Build Docker image
docker build -t document-maker .
docker tag document-maker myregistry.azurecr.io/document-maker:latest

# Push & deploy
docker push myregistry.azurecr.io/document-maker:latest
```

**Dockerfile needed:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
```

---

## Remaining Known Issues

⚠️ **Issues to Address:**

1. **GSheet Feature**: Currently commented out in code. Either enable or remove completely.
   - Decision needed: Keep GSheet project matching or remove?

2. **AI Sequential Processing**: Currently uses user-provided values directly.
   - Consider implementing actual AI processing for AI tasks if needed.

3. **Error Handling**: Add more granular error handling for:
   - Network timeouts
   - API rate limits
   - Missing Google Doc templates

---

## Environment Variables Required (Production)

| Variable | Example | Source |
|----------|---------|--------|
| `GEMINI_API` | `AIzaSy...` | Google Cloud Console |
| `GSHEET_URL` | Sheet URL | Google Sheets |
| `APPS_SCRIPT_WEB_APP_URL` | Apps Script URL | Google Apps Script |

---

## Security Checklist

- [x] No API keys in source code
- [x] Secrets properly configured
- [x] Error messages don't expose sensitive info
- [ ] Rate limiting implemented (consider adding)
- [ ] Input validation enhanced (consider adding)
- [ ] CORS properly configured for Google APIs

---

## Testing Production Deployment

1. Test with small budget values first
2. Verify Google Docs are created correctly
3. Check error handling for edge cases
4. Monitor API quota usage
5. Test with maximum expected file size

**Ready to deploy!** 🚀
