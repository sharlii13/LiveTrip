# Google OAuth Setup Instructions

## 1. Create Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" in the left sidebar
5. Click "Create Credentials" > "OAuth 2.0 Client IDs"
6. Choose "Web application" as the application type
7. Add authorized redirect URIs:
   - For development: `http://localhost:5000/api/auth/google/callback`
   - For production: `https://yourdomain.com/api/auth/google/callback`

## 2. Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Session Configuration
SESSION_SECRET=your_session_secret_here

# Database Configuration (if using PostgreSQL)
DATABASE_URL=your_database_url_here

# Server Configuration
PORT=5000
NODE_ENV=development
```

## 3. Install Dependencies

The required dependencies have been added to `package.json`:
- `passport-google-oauth20`
- `@types/passport-google-oauth20`

To install them, run:
```bash
npm install
```

## 4. Features Implemented

### Backend
- ✅ Google OAuth authentication with Passport.js
- ✅ Session management with express-session
- ✅ User schema updated to support OAuth fields (googleId, provider)
- ✅ Storage methods for OAuth user creation/retrieval
- ✅ Authentication middleware for protected routes
- ✅ API endpoints:
  - `GET /api/auth/google` - Initiate Google OAuth
  - `GET /api/auth/google/callback` - OAuth callback
  - `POST /api/auth/logout` - Logout user
  - `GET /api/auth/me` - Get current user

### Frontend
- ✅ Login page with Google OAuth button
- ✅ Authentication context and hooks
- ✅ Protected route component
- ✅ Updated navbar with user dropdown
- ✅ User profile display

## 5. Usage

1. Start the development server: `npm run dev`
2. Navigate to `http://localhost:5000`
3. Click "Sign In" to authenticate with Google
4. After successful authentication, you'll be redirected to the home page
5. The navbar will show your user profile with logout option
## 6. Security Notes

- Change the `SESSION_SECRET` to a strong, random string in production
- Use HTTPS in production for secure cookie transmission
- Consider implementing additional security measures like CSRF protection
- Regularly rotate your OAuth credentials


