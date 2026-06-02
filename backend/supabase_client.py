from supabase import create_client, Client
from config import settings

# Initialize Supabase Admin client using Service Role Key
# This allows the backend to perform protected operations
# WARNING: Only use this after verifying the user's JWT token
supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def verify_jwt(token: str):
    """
    Verifies the JWT token by fetching the user profile securely directly from Supabase Auth.
    Returns the user object if valid, None otherwise.
    """
    try:
        # get_user validates the token directly against the Supabase Auth server
        res = supabase_admin.auth.get_user(token)
        if res and res.user:
            return res.user
        return None
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None
