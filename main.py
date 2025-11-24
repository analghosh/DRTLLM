import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.middleware.cors import CORSMiddleware
from langchain_community.utilities import SQLDatabase
from app.db import engine
from app.core.chatbot import Chatbot
from app.shared_resources import shared_db, chatbot_instances
from app.api.router import router as api_router



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


app = FastAPI(title="Judiciary", version="0.1.0")

# Define allowed origins
origins = [
    "*",
]
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specify the allowed origins
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Serve static files and templates from project root
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Test root endpoint
@app.get("/", include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
async def initialize_resources():
    """
    Initialize SQLDatabase and a single chatbot instance at server startup.
    """
    global shared_db, chatbot_instances

    # 1. Initialize the shared SQLDatabase (PostgreSQL)
    shared_db = SQLDatabase(
        engine=engine,
        # Mention only the tables you want LLM to query
        include_tables=["case_details_2025"]  
    )
    print("✅ Shared SQLDatabase initialized successfully.")

    # 2. Initialize only one chatbot (your first phase)
    chatbot_instances.clear()  # reset dictionary
    chatbot_instances["DefaultBot"] = Chatbot(
        bot_type="DefaultBot",
        shared_db=shared_db,
    )
    
    logger.info("Chatbot instance created.")

    print("🤖 Chatbot instance initialized successfully.")



app.include_router(api_router)
