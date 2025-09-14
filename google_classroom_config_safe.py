# Google OAuth configuration
# Using credentials from Google Cloud Console

# Client ID from Google Cloud Console
CLIENT_ID = "YOUR_CLIENT_ID.apps.googleusercontent.com"

# Client secret from Google Cloud Console
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

# OAuth 2.0 scopes for Google Classroom API
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly',
    'https://www.googleapis.com/auth/classroom.profile.emails',
    'https://www.googleapis.com/auth/classroom.profile.photos',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# Redirect URI for the OAuth 2.0 flow
# This must match one of the authorized redirect URIs in Google Cloud Console
# Since we're now using port 5001, we need to work with the URI that's already authorized
REDIRECT_URI = "http://localhost"

# Google OAuth endpoints
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"