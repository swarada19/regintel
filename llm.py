from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from pydantic import ValidationError

load_dotenv()

# Groq withdrew llama-3.3-70b-versatile (and llama-3.1-8b-instant) in Aug 2026;
# calls started failing with 404 model_not_found. Check the live list before
# changing this: GET https://api.groq.com/openai/v1/models
MODEL = "openai/gpt-oss-120b"


def get_llm(temperature: float = 0.7) -> ChatGroq:
    """Construct the chat model. Reads GROQ_API_KEY from the environment."""
    return ChatGroq(model=MODEL, temperature=temperature)


def is_schema_failure(error: Exception) -> bool:
    """True if the model produced output that didn't satisfy the response schema.

    Groq validates tool calls server-side and rejects them with a 400 before the
    response reaches us, so most schema failures arrive as BadRequestError rather
    than the ValidationError the LangChain docs lead you to expect. Anything Groq
    does not enforce still falls through to Pydantic, so both count.

    Deliberately narrow: other 400s (oversized context, malformed request) and
    transport errors like rate limits are not retryable this way.
    """
    if isinstance(error, ValidationError):
        return True
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        return body.get("error", {}).get("code") == "tool_use_failed"
    return False


def invoke_with_retry(structured_llm, messages: list[BaseMessage], max_retries: int = 1):
    """Invoke a structured LLM, retrying with error feedback if the output fails validation.

    Retrying blind would just re-roll the dice; feeding the rejection back gives the
    model the one thing it was missing. Capped at one retry — each attempt costs a
    call, and unbounded retry loops are the classic agent failure mode.
    """
    attempt_messages = messages

    for attempt in range(max_retries + 1):
        try:
            return structured_llm.invoke(attempt_messages)
        except Exception as error:
            if attempt == max_retries or not is_schema_failure(error):
                raise
            attempt_messages = messages + [
                HumanMessage(
                    content=(
                        f"Your previous response was rejected because it did not match "
                        f"the required schema: {error}\n\n"
                        f"Respond again, satisfying every field constraint exactly."
                    )
                )
            ]
