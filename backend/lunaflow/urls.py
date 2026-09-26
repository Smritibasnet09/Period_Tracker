"""
LunaFlow URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from rest_framework_simplejwt.views import TokenRefreshView


def redirect_to_register(request):
    """Convenience redirect from port 8000 to React register page on port 3000."""
    return redirect('http://localhost:3000/register')


def redirect_to_login(request):
    """Convenience redirect from port 8000 to React login page on port 3000."""
    return redirect('http://localhost:3000/login')


def api_root(request):
    """Root view providing API info, status, and quick links."""
    if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LunaFlow Backend API</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #FFF1F2; margin: 0; padding: 40px 20px; display: flex; justify-content: center; }
        .card { background: white; border-radius: 16px; padding: 32px; max-width: 620px; width: 100%; box-shadow: 0 4px 20px rgba(244, 63, 94, 0.1); }
        h1 { color: #E11D48; margin-top: 0; font-size: 26px; }
        .status { display: inline-block; background: #DCFCE7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 14px; margin-bottom: 20px; }
        p { color: #4B5563; line-height: 1.5; }
        ul { list-style: none; padding: 0; }
        li { margin: 8px 0; }
        a { color: #F43F5E; text-decoration: none; font-weight: 500; }
        a:hover { text-decoration: underline; }
        .btn-group { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
        .btn { display: inline-block; background: #F43F5E; color: white !important; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; }
        .btn:hover { background: #E11D48; }
        .btn-outline { background: white; color: #E11D48 !important; border: 1.5px solid #F43F5E; }
        .btn-outline:hover { background: #FFF1F2; }
        code { background: #F3F4F6; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🌸 LunaFlow API Server</h1>
        <div class="status">● Backend Running (Django 4.2 REST API)</div>
        <p>The backend server is active and ready to accept API requests.</p>
        
        <h3>Web App Navigation:</h3>
        <div class="btn-group">
            <a class="btn" href="http://localhost:3000/register" target="_blank">Register New Account ➔</a>
            <a class="btn btn-outline" href="http://localhost:3000/login" target="_blank">Login Page ➔</a>
            <a class="btn btn-outline" href="http://localhost:3000" target="_blank">Dashboard ➔</a>
        </div>

        <h3>Quick Links:</h3>
        <ul>
            <li>🌐 <strong>Web Application:</strong> <a href="http://localhost:3000" target="_blank">http://localhost:3000</a></li>
            <li>⚙️ <strong>Django Admin:</strong> <a href="/admin/">/admin/</a></li>
            <li>🤖 <strong>ML Microservice:</strong> <a href="http://localhost:8001/docs" target="_blank">http://localhost:8001/docs</a></li>
        </ul>

        <h3>Available API Routes:</h3>
        <ul>
            <li><code>POST /api/auth/register/</code> — User registration</li>
            <li><code>POST /api/auth/login/</code> — User authentication</li>
            <li><code>GET  /api/cycles/</code> — Menstrual cycles</li>
            <li><code>GET  /api/logs/daily/</code> — Daily health logs</li>
            <li><code>POST /api/predictions/generate/</code> — AI Cycle predictions</li>
            <li><code>GET  /api/insights/cycle-stats/</code> — Cycle analytics</li>
            <li><code>POST /api/insights/ask/</code> — Ask Cycle Assistant</li>
            <li><code>GET  /api/reminders/</code> — Reminders</li>
        </ul>
    </div>
</body>
</html>"""
        return HttpResponse(html_content, content_type="text/html")
    
    return JsonResponse({
        "name": "LunaFlow API Backend",
        "status": "online",
        "version": "1.0.0",
        "frontend_url": "http://localhost:3000",
        "register_url": "http://localhost:3000/register",
        "login_url": "http://localhost:3000/login",
        "admin_url": "/admin/",
        "endpoints": {
            "register": "/api/auth/register/",
            "login": "/api/auth/login/",
            "profile": "/api/profile/",
            "cycles": "/api/cycles/",
            "logs": "/api/logs/",
            "predictions": "/api/predictions/",
            "insights": "/api/insights/",
            "reminders": "/api/reminders/",
            "token_refresh": "/api/token/refresh/",
        }
    })


urlpatterns = [
    # Root status page / API overview
    path('', api_root, name='api-root'),

    # Convenience browser redirects to frontend app
    path('register/', redirect_to_register, name='redirect-register'),
    path('login/', redirect_to_login, name='redirect-login'),

    path('admin/', admin.site.urls),

    # JWT token refresh
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App URLs
    path('api/auth/', include('apps.accounts.urls')),
    path('api/profile/', include('apps.accounts.profile_urls')),
    path('api/cycles/', include('apps.cycles.urls')),
    path('api/logs/', include('apps.logs.urls')),
    path('api/predictions/', include('apps.predictions.urls')),
    path('api/insights/', include('apps.cycles.insight_urls')),
    path('api/reminders/', include('apps.reminders.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
