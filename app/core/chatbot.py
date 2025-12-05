import os
import re
import json
import asyncio
import logging
from typing import List, Tuple

from pydantic import BaseModel
from typing_extensions import TypedDict

from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain

from app.core.llm_factory import create_llm
from app.core.utils.log_utils import log_and_raise
from app.core.chatbot_prompts import (
    SYSTEM_INSTRUCTION_PROMPT,
    WRITE_QUERY_PROMPT,
    MULTI_QUESTION_GENERATE_ANSWER_PROMPT,
    DETECT_INTENT_PROMPT,
)
from app.table_info import TABLE_INFO


# ---------- Simple models for structured output ----------

class QueryItem(BaseModel):
    question: str
    query: str


class QueryOutput(BaseModel):
    queries: List[QueryItem]


class State(TypedDict):
    """State object to maintain query, result, and answer."""
    question: str
    query: str
    result: str
    answer: str


# ---------- DRT‑only Chatbot class ----------

class Chatbot:
    def __init__(self, bot_type: str, shared_db: SQLDatabase):
        # basic setup
        self.bot_type = bot_type
        self.logger = logging.getLogger(f"{self.bot_type}Chatbot")
        self.logger.setLevel(logging.INFO)

        # DB: only your shared PostgreSQL with case_details_2025
        try:
            self.db = shared_db
            self.logger.info("Using shared SQLDatabase instance.")
            self.table_info = TABLE_INFO
            self.logger.info("Cached DRT table schema information.")
        except Exception as e:
            self.logger.error(f"Error using shared SQLDatabase: {str(e)}")
            raise

        # LLM (Ollama / Gemini / Groq via factory)
        self.llm = create_llm()
        if not self.llm:
            raise ValueError("Failed to initialize the LLM. Please check configuration.")

        # optional: SQLDatabaseChain (not strictly required if you always go via prompts)
        self.db_chain = SQLDatabaseChain.from_llm(llm=self.llm, db=self.db)

        # system instruction, already customized for DRT
        self.system_instruction = SYSTEM_INSTRUCTION_PROMPT.format(bot_type=self.bot_type)

    # ---------- General / small‑talk ----------

    async def generate_dynamic_response(self, user_input: str, chat_history: list = None) -> str:
        if chat_history is None:
            chat_history = []
        self.logger.info(f"Generating dynamic response for user input: {user_input}")
        try:
            prompt = f"""
                            System Instruction:
                            {self.system_instruction}

                            User Input: "{user_input}"

                            Chat history (most recent last):
                            {json.dumps(chat_history)}

                            Respond appropriately based on the system instruction, considering the chat history for context.
                        """
            response = await asyncio.to_thread(self.llm.invoke, prompt)
            self.logger.info("Dynamic response generated successfully.")
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"Error generating dynamic response: {str(e)}")
            log_and_raise(e, "Error generating dynamic response.")
            return "Sorry, I encountered an issue while processing your input. Please try again."

    # ---------- Safety: only read‑only queries ----------

    def is_query_retrieval_only(self, query: str) -> bool:
        """Allow only read‑only queries (no INSERT/UPDATE/DELETE/etc.)."""
        self.logger.info(f"Checking if query is retrieval-only: {query}")
        query = query.strip()

        # block queries starting with comments
        if re.match(r"(?i)^\s*(--|#|/\*)", query):
            self.logger.warning("Query starts with a comment — blocked.")
            return False

        forbidden_start = [
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "create",
            "exec",
            "merge",
            "truncate",
            "save",
        ]
        pattern = r"(?i)^\s*(" + "|".join(forbidden_start) + r")\b"
        if re.match(pattern, query):
            self.logger.warning("Query starts with a forbidden keyword.")
            return False

        self.logger.info("Query is safe (retrieval or non-modifying).")
        return True

    def uses_only_case_table(self, sql_query: str) -> bool:
        """
        Ensure the query touches only your single table: case_details_2025.
        """
        self.logger.info(f"Validating tables in query: {sql_query}")
        tables = re.findall(r"from\s+(\w+)", sql_query, re.IGNORECASE)
        tables += re.findall(r"join\s+(\w+)", sql_query, re.IGNORECASE)
        unique_tables = {t.lower() for t in tables}
        self.logger.info(f"Detected tables: {unique_tables or set()}")

        # allow no explicit FROM (e.g., some dialects) or only case_details_2025
        allowed = {"updated_case_details_2025", " case_type"}
        if not unique_tables:
            return True
        return unique_tables.issubset(allowed)
 
    def is_query_allowed(self, sql_query: str) -> bool:
        """
        Single check: read-only + only allowed tables.
        """
        if not self.is_query_retrieval_only(sql_query):
            return False
        if not self.uses_only_case_table(sql_query):
            self.logger.warning("Query uses tables other than allowed tables.")
            return False
        return True
    
    # ---------- Write SQL from NL ----------

    def write_query(self, questions: str, chat_history: list) -> list[QueryItem]:
        self.logger.info(f"Generating SQL queries for questions: {questions}")
        try:
            prompt = WRITE_QUERY_PROMPT.format(
                table_info=self.table_info,
                input=questions,
                dialect=self.db.dialect,
                database_specific_instructions="",  # if you removed this from the prompt, drop this arg
                chat_history=json.dumps(chat_history),
            )

            response = self.llm.invoke(prompt)
            raw_text = response.content if hasattr(response, "content") else str(response)
            self.logger.info(f"Raw LLM output for write_query: {raw_text}")

            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()

            data = json.loads(cleaned)
            queries_list = data.get("queries", [])
            result: list[QueryItem] = []
            for item in queries_list:
                q = item.get("question", "").strip()
                sql = item.get("query", "").strip()
                if not q or not sql:
                    continue
                result.append(QueryItem(question=q, query=sql))

            if not result:
                raise ValueError("No valid queries parsed from model output.")

            self.logger.info(f"Parsed SQL queries: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error generating SQL queries: {str(e)}")
            log_and_raise(
                e,
                "Error generating SQL queries. Please check the input questions and database schema.",
            )

        
    # ---------- Execute query ----------

    async def execute_query(self, query: str) -> Tuple[bool, str]:
        self.logger.info(f"Executing query: {query}")
        try:
            result = self.db._execute(query)
            self.logger.info(f"Query Result: {result}")
            return True, result
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            log_and_raise(e, "Error executing SQL query on the database.")
            return False, f"Error: {str(e)}"

    # ---------- Turn SQL results into user answer ----------

    async def generate_answer(
        self,
        actual_question: str,
        queries: List[QueryItem],
        results: List[str],
        chat_history: list,
    ) -> str:
        self.logger.info(f"Generating answer for question: {actual_question}")
        try:
            combined_data = "\n".join(
                [
                    f"Sub-Question: {item.question}\nQuery: {item.query}\nResult: {result}"
                    for item, result in zip(queries, results)
                ]
            )

            prompt = MULTI_QUESTION_GENERATE_ANSWER_PROMPT.format(
                actual_question=actual_question,
                combined_data=combined_data,
                table_info=self.table_info,
                chat_history=json.dumps(chat_history),
            )

            response = await asyncio.to_thread(self.llm.invoke, prompt)
            self.logger.info("Answer generated successfully.")
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"Error generating answer: {str(e)}")
            log_and_raise(e, "Error generating answers from SQL results.")
            return "Sorry, I encountered an issue while generating the answers. Please try again."

    # ---------- Intent detection ----------

    async def detect_intent(self, user_input: str, chat_history: list) -> str:
        self.logger.info(f"Detecting intent for user input: {user_input}")
        try:
            prompt = DETECT_INTENT_PROMPT.format(
                table_schema=self.table_info,
                user_input=user_input,
                chat_history=json.dumps(chat_history),
            )
            response = await asyncio.to_thread(self.llm.invoke, prompt)
            intent = response.content.strip()
            self.logger.info(f"Intent detected: {intent}")
            return intent
        except Exception as e:
            self.logger.error(f"Error detecting intent: {str(e)}")
            log_and_raise(e, "Error detecting intent.")
            return "general_query"

    # ---------- High‑level handlers ----------

    async def handle_general_query(self, question: str, chat_history: list) -> dict:
        self.logger.info(f"Handling general query: {question}")
        dynamic_response = await self.generate_dynamic_response(question, chat_history)
        return {"success": True, "response": dynamic_response}


    async def handle_database_query(
        self, questions: str, chat_history: list = None,
    ) -> dict:
        if chat_history is None:
            chat_history = []
        self.logger.info(f"Handling database query for questions: {questions}")
        try:
            queries = await asyncio.to_thread(self.write_query, questions, chat_history)

            all_rows = []  # list of dicts from DB
            for item in queries:
                if not self.is_query_allowed(item.query):
                    self.logger.warning(f"Blocked unsafe or invalid query: {item.query}")
                    continue

                ok, result = await self.execute_query(item.query)
                if not ok:
                    self.logger.warning(f"Query execution failed for: {item.query}")
                    continue

                # result from SQLDatabase._execute is usually a list of dicts or rows
                # normalize to list of dicts
                if isinstance(result, list):
                    all_rows.extend(result)

            if not all_rows:
                return {
                    "success": False,
                    "response": "No data was found for this request.",
                    "rows": [],
                }

            return {
                "success": True,
                "response": f"Found {len(all_rows)} row(s).",
                "rows": all_rows,
            }

        except Exception as e:
            self.logger.error(f"Error handling database query: {str(e)}")
            log_and_raise(e, "Error processing database queries.")
            return {
                "success": False,
                "response": "An unexpected error occurred while processing your query.",
                "rows": [],
            }



    async def process_query(self, question: str, chat_history: list = None) -> dict:
        if chat_history is None:
            chat_history = []
        self.logger.info(f"Processing query: {question}")
        return await self.handle_database_query(question, chat_history)






