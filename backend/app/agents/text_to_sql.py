from sqlalchemy import create_engine, text
import pandas as pd
import re
from app.config import AgentConfig
from typing import Optional
from app.agents.base import LLMProvider
from app.agents.providers import (
    ClaudeProvider, OpenAIProvider, GroqProvider,
    OpenRouterProvider, OllamaProvider
)

class TextToSQLAgent:
    def __init__(self, db_url: str, provider: Optional[LLMProvider] = None):
        self.engine = create_engine(db_url)
        self.provider = provider or self._get_provider(AgentConfig.PROVIDER)
    
    def _get_provider(self, provider_type: str) -> LLMProvider:
        providers = {
            "claude": ClaudeProvider,
            "openai": OpenAIProvider,
            "groq": GroqProvider,
            "openrouter": OpenRouterProvider,
            "ollama": OllamaProvider,
        }
        cls = providers.get(provider_type.lower())
        if not cls:
            raise ValueError(f"Unknown provider: {provider_type}. Options: {list(providers.keys())}")
        return cls()

    def _extract_sql(self, response: str) -> str:
        """Extract SQL từ LLM response, bỏ markdown code block nếu có."""
        sql_match = re.search(r"```(?:sql)?\s*(SELECT.*?)```", response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        return response.strip()

    def _validate_sql(self, sql: str) -> tuple[bool, str | None]:
        """Chỉ cho phép một câu SELECT đơn, chặn multi-statement và keyword nguy hiểm.

        Improves validation by removing SQL comments and string literals before
        checking for semicolons and dangerous keywords, reducing bypass via
        comments/strings.
        """
        if not sql or not sql.strip():
            return False, "Query rỗng."

        s = sql.strip()

        # Remove fenced code blocks if LLM included them
        s = re.sub(r"```.*?```", "", s, flags=re.DOTALL)

        # Strip SQL comments (single-line -- and block /* */)
        no_comments = re.sub(r"--.*?$", "", s, flags=re.MULTILINE)
        no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

        # Remove string literals to avoid semicolons or keywords inside quotes
        no_strings = re.sub(r"('(?:''|[^'])*')|(\"(?:\"\"|[^\"])*\")", "", no_comments)

        # Normalize whitespace for checks
        cleaned = no_strings.strip()
        if not cleaned:
            return False, "Query rỗng sau khi loại comments/strings."

        # Allow a single trailing semicolon, but reject any additional semicolon
        # that indicates a multi-statement query.
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].rstrip()

        if ";" in cleaned:
            return False, "Chỉ cho phép một câu lệnh SELECT (không cho phép ';')."

        upper = cleaned.upper()
        if not upper.startswith("SELECT"):
            return False, "Chỉ cho phép SELECT query."

        dangerous = [
            "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE",
            "GRANT", "REVOKE", "EXEC", "EXECUTE", "COPY", "INTO", "MERGE",
            "CALL", "DO", "SET", "SHOW",
        ]
        for kw in dangerous:
            if re.search(rf"\b{kw}\b", upper):
                return False, f"Query chứa từ khoá bị cấm: {kw}"
        return True, None

    def _execute_sql(self, sql: str):
        """Thực thi SQL, chỉ cho phép SELECT."""
        ok, err = self._validate_sql(sql)
        if not ok:
            return False, None, err

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                df = pd.DataFrame(result.mappings().all())
            return True, df, None
        except Exception as e:
            return False, None, str(e)

    def ask(self, question: str) -> dict:
        """Nhận câu hỏi tự nhiên → generate SQL → execute → trả kết quả."""
        from app.agents.promts import build_sql_prompt
        
        # Bước 1: Build prompt
        prompt = build_sql_prompt(question)
        
        # Bước 2: Generate SQL
        try:
            response = self.provider.generate_sql(prompt)
            sql = self._extract_sql(response)
        except Exception as e:
            return {
                "question": question,
                "sql": None,
                "success": False,
                "error": f"LLM error: {str(e)}",
                "data": None,
                "answer": None,
            }
        
        # Bước 3: Execute SQL
        success, df, error = self._execute_sql(sql)
        if not success:
            return {
                "question": question,
                "sql": sql,
                "success": False,
                "error": error,
                "data": None,
                "answer": None,
            }
        
        # Bước 4: Format answer
        if df.empty:
            answer = "Không tìm thấy kết quả phù hợp."
        elif len(df) == 1 and len(df.columns) == 1:
            answer = str(df.iloc[0, 0])
        else:
            rows_text = df.head(AgentConfig.RESULT_LIMIT).to_string(index=False)
            total = len(df)
            answer = rows_text
            if total > AgentConfig.RESULT_LIMIT:
                answer += f"\n\n(Hiển thị {AgentConfig.RESULT_LIMIT}/{total} kết quả)"
        
        return {
            "question": question,
            "sql": sql,
            "success": True,
            "data": df,
            "error": None,
            "answer": answer,
        }