import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db
from app.routers import auth, employees, projects, costcodes, time, dashboard, photos, reports

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title='PunchPoint API',
    description='Construction time tracking and job costing platform',
    version='1.0.0',
)

# CORS configuration
cors_origins_env = os.environ.get('CORS_ORIGINS', '*')
if cors_origins_env.strip() == '*':
    allow_origins = ['*']
else:
    allow_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include routers
app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(costcodes.router)
app.include_router(time.router)
app.include_router(dashboard.router)
app.include_router(photos.router)
app.include_router(reports.router)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.isdir(static_dir):
    app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.get('/')
def serve_landing():
    landing_path = os.path.join(os.path.dirname(__file__), 'static', 'landing.html')
    if os.path.isfile(landing_path):
        return FileResponse(landing_path)
    return HTMLResponse('<h1>PunchPoint</h1><p>Landing page not found.</p>', status_code=200)

@app.get('/app')
def serve_app():
    index_path = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return HTMLResponse('<h1>PunchPoint API</h1><p>Frontend not yet deployed.</p>', status_code=200)


@app.get('/api/health')
def health_check():
    return {'status': 'ok'}