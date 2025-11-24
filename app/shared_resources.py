from langchain_community.utilities import SQLDatabase

shared_db: SQLDatabase = None

chatbot_instances = {}

def get_chatbot_instance():
    if not chatbot_instances:
        raise RuntimeError("Chatbot instance have not been initializes yet.")
    return chatbot_instances