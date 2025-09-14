"""
Command-line tool to generate authentication for Google Classroom.
This handles the OAuth flow in a simpler way than the web app.
"""

import os
import json
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google OAuth scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly',
    'https://www.googleapis.com/auth/classroom.profile.emails',
    'https://www.googleapis.com/auth/classroom.profile.photos',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

def create_token(credentials_file="credentials.json", token_file="classroom_token.json"):
    """Creates a token file using local authorization flow."""
    try:
        # Check if credentials file exists
        if not os.path.exists(credentials_file):
            logger.error(f"Credentials file {credentials_file} not found.")
            return False
            
        # Create the flow using the client secrets file
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        
        # Run the local server flow to get credentials
        logger.info("Starting local authentication flow. Your browser should open automatically.")
        credentials = flow.run_local_server(port=0)
        
        # Save the credentials for future use
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open(token_file, 'w') as f:
            json.dump(token_data, f)
            
        logger.info(f"Authentication successful! Token saved to {token_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        return False

def main():
    """Main function to run the CLI tool."""
    print("Google Classroom Authentication Tool")
    print("===================================")
    print("This tool will help you authenticate with Google Classroom.")
    print("A browser window will open for you to log in and grant permissions.")
    print()
    
    success = create_token()
    
    if success:
        print("\nSuccess! You can now use the web application with your Google Classroom account.")
        print("The token has been saved and will be used automatically.")
    else:
        print("\nAuthentication failed. Please check the error messages above.")

if __name__ == "__main__":
    main()