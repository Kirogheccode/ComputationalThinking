from dotenv import load_dotenv
import os

load_dotenv()

# --- GOOGLE OAUTH ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# --- FACEBOOK OAUTH ---
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")

# Cấu hình Google OAuth
OAUTH_CONFIG = {
    'google': {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'api_base_url': 'https://www.googleapi.com/',
        'authorize_url': 'https://accounts.google.com/o/oauth2/auth',
        'access_token_url': 'https://accounts.google.com/o/oauth2/token',
        'client_kwargs': {
            'scope': 'openid email profile',
            'token_endpoint_auth_method': 'client_secret_post'
        }
    },
    'facebook': {
        'client_id': FACEBOOK_CLIENT_ID,
        'client_secret': FACEBOOK_CLIENT_SECRET,
        'api_base_url': 'https://graph.facebook.com/v15.0/',
        'authorize_url': 'https://www.facebook.com/v15.0/dialog/oauth',
        'access_token_url': 'https://graph.facebook.com/v15.0/oauth/access_token',
        'client_kwargs': {
            'scope': 'email public_profile'
        }
    }
}
