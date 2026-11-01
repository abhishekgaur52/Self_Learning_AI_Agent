"""The ONLY file that talks to Gemini (google-genai SDK). Handles errors and retries."""
import logging
import time

from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """Friendly error the UI can show directly."""


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise GeminiError("GOOGLE_API_KEY is missing. Add it to your .env file.")
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def generate(self, system_prompt: str, history: list[dict], user_text: str, retries: int = 3) -> str:
        """history = [{"role": "user"|"assistant", "content": "..."}, ...]"""
        contents = [
            types.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[types.Part.from_text(text=m["content"])],
            )
            for m in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
        config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.7)

        for attempt in range(retries):
            try:
                resp = self.client.models.generate_content(model=self.model, contents=contents, config=config)
                if not resp.text:
                    raise GeminiError("Gemini returned an empty answer (it may have been blocked). Try rephrasing.")
                return resp.text
            except errors.APIError as e:
                code = getattr(e, "code", None)
                msg = getattr(e, "message", str(e))
                retryable = code in (429, 500, 503)
                if retryable and attempt < retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning("Gemini error %s, retrying in %ss", code, wait)
                    time.sleep(wait)
                    continue
                if code == 429:
                    raise GeminiError("Rate limit reached. Please wait a minute and try again.") from e
                if code in (401, 403):
                    raise GeminiError("API key rejected. Check GOOGLE_API_KEY in .env.") from e
                if code == 404:
                    raise GeminiError(f"Model '{self.model}' not found. Change GEMINI_MODEL in .env.") from e
                raise GeminiError(f"Gemini error ({code}): {msg}") from e
            except GeminiError:
                raise
            except Exception as e:  # network problems etc.
                raise GeminiError(f"Could not reach Gemini: {e}") from e
        raise GeminiError("Gemini did not respond. Please try again.")
