"""
OAuth authentication endpoints for Google and GitHub
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse
import secrets
import json

router = APIRouter()

# Temporary storage for OAuth state (in production, use Redis or database)
oauth_states = {}

@router.get("/auth/google/login")
async def google_login():
    """Initiate Google OAuth login"""
    # For now, show a message that OAuth is not configured
    # In production, you would redirect to Google OAuth
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google OAuth - Configuration Required</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                text-align: center;
                max-width: 500px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 { color: #667eea; margin-bottom: 20px; }
            p { color: #4a5568; line-height: 1.6; margin-bottom: 15px; }
            .info-box {
                background: #f0f2ff;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: left;
            }
            .info-box strong { color: #667eea; }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }
            button:hover { opacity: 0.9; }
            .demo-section {
                margin-top: 20px;
                padding-top: 20px;
                border-top: 2px solid #e9ecef;
            }
            .demo-button {
                background: #10b981;
                margin: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Google OAuth Setup Required</h1>
            <p>To enable Google login, you need to configure OAuth credentials:</p>
            
            <div class="info-box">
                <p><strong>1. Create Google OAuth Credentials:</strong></p>
                <p>Visit <a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a></p>
                <p><strong>2. Set up environment variables:</strong></p>
                <p>GOOGLE_CLIENT_ID=your_client_id<br>
                GOOGLE_CLIENT_SECRET=your_secret</p>
                <p><strong>3. Add redirect URI:</strong></p>
                <p>http://localhost:8000/auth/google/callback</p>
            </div>
            
            <div class="demo-section">
                <p><strong>For now, use test accounts to login:</strong></p>
                <button class="demo-button" onclick="window.location.href='/frontend/templates/login.html'">
                    ← Back to Login
                </button>
                <p style="margin-top: 15px; font-size: 14px; color: #718096;">
                    Use test account: john@example.com / password123
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/auth/github/login")
async def github_login():
    """Initiate GitHub OAuth login"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GitHub OAuth - Configuration Required</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #24292e 0%, #444d56 100%);
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                text-align: center;
                max-width: 500px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }
            h1 { color: #24292e; margin-bottom: 20px; }
            p { color: #4a5568; line-height: 1.6; margin-bottom: 15px; }
            .info-box {
                background: #f6f8fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: left;
            }
            .info-box strong { color: #24292e; }
            button {
                background: #24292e;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }
            button:hover { opacity: 0.9; }
            .demo-section {
                margin-top: 20px;
                padding-top: 20px;
                border-top: 2px solid #e9ecef;
            }
            .demo-button {
                background: #10b981;
                margin: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 GitHub OAuth Setup Required</h1>
            <p>To enable GitHub login, you need to configure OAuth credentials:</p>
            
            <div class="info-box">
                <p><strong>1. Create GitHub OAuth App:</strong></p>
                <p>Visit <a href="https://github.com/settings/developers" target="_blank">GitHub Developer Settings</a></p>
                <p><strong>2. Set up environment variables:</strong></p>
                <p>GITHUB_CLIENT_ID=your_client_id<br>
                GITHUB_CLIENT_SECRET=your_secret</p>
                <p><strong>3. Add callback URL:</strong></p>
                <p>http://localhost:8000/auth/github/callback</p>
            </div>
            
            <div class="demo-section">
                <p><strong>For now, use test accounts to login:</strong></p>
                <button class="demo-button" onclick="window.location.href='/frontend/templates/login.html'">
                    ← Back to Login
                </button>
                <p style="margin-top: 15px; font-size: 14px; color: #718096;">
                    Use test account: john@example.com / password123
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/auth/google/callback")
async def google_callback():
    """Handle Google OAuth callback"""
    return {"message": "Google OAuth callback - not implemented yet"}

@router.get("/auth/github/callback")
async def github_callback():
    """Handle GitHub OAuth callback"""
    return {"message": "GitHub OAuth callback - not implemented yet"}
