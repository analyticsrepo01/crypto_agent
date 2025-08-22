# Portfolio Reports Cloud Run App

This directory contains a Flask web application that displays portfolio reports from Google Cloud Storage.

## Setup

1. Replace placeholder values in this template file
2. Set up Google Cloud Project:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

3. Configure OAuth 2.0:
   - Create OAuth 2.0 credentials in Google Cloud Console
   - Download client_secrets.json (use template and add real values)
   - Set redirect URI to: `https://your-domain/oauth2callback`

4. Deploy to Cloud Run:
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

## Configuration

### Environment Variables
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GCS_BUCKET_NAME`: Portfolio reports bucket name
- `FLASK_SECRET_KEY`: Random secret key for sessions

### OAuth Configuration
Replace placeholders in client_secrets.json:
- `YOUR_GOOGLE_CLIENT_ID`
- `YOUR_GOOGLE_CLIENT_SECRET`  
- `YOUR_REDIRECT_URI`

### Cloud Build
Replace placeholders in cloudbuild.yaml:
- `YOUR_PROJECT_ID`
- `YOUR_REGION`
- `YOUR_SERVICE_NAME`

## Security Notes
- Never commit real credentials to version control
- Use Google Secret Manager for production deployments
- Regularly rotate OAuth credentials
- Monitor access logs for suspicious activity

## Deployment
```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# View logs
gcloud logs read --service=your-service-name
```