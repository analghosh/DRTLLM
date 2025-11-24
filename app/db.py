import os
from dotenv import load_dotenv
from sqlalchemy import create_engine,MetaData

load_dotenv()
metadata= MetaData()

#postgresql database connection
DATABASE_URL = (
    f"postgresql+psycopg2://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}"
    f"@{os.environ.get('DB_HOST')}:{int(os.environ.get('DB_PORT', 5432))}/{os.environ.get('DB_NAME')}"
)

#Creating the database engine 
engine = create_engine(DATABASE_URL,echo=True)
