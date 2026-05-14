import tiktoken
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from app.utils.llm import llm
from app.graph.workflow import graph

# Thresholds
MIN_MESSAGES_TO_SUMMARIZE = 6
TRIGGER_MESSAGE_COUNT     = 8
TRIGGER_TOKEN_COUNT       = 4_000

_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def count_history_tokens(chat_history: list[BaseMessage]) -> int:
    """Sum tokens across all messages in history."""
    return sum(count_tokens(msg.content) for msg in chat_history)


def should_summarize(chat_history: list[BaseMessage]) -> tuple[bool, str]:
    """
    Returns (True, reason) if summarization should run, else (False, "").
    Two triggers:
      1. Message count  >= TRIGGER_MESSAGE_COUNT
      2. Total tokens   >= TRIGGER_TOKEN_COUNT
    """
    msg_count    = len(chat_history)
    total_tokens = count_history_tokens(chat_history)

    if msg_count >= TRIGGER_MESSAGE_COUNT:
        return True, f"message count ({msg_count} >= {TRIGGER_MESSAGE_COUNT})"

    if total_tokens >= TRIGGER_TOKEN_COUNT:
        return True, f"token count ({total_tokens} >= {TRIGGER_TOKEN_COUNT})"

    return False, ""


async def run_summarizer_background(state: dict, config: dict):

    chat_history = state.get("chat_history", [])

    triggered, reason = should_summarize(chat_history)

    if not triggered:
        return

    total_tokens = count_history_tokens(chat_history)

    if total_tokens >= TRIGGER_TOKEN_COUNT:
        collapse_count = min(8, len(chat_history))
    else:
        collapse_count = min(MIN_MESSAGES_TO_SUMMARIZE, len(chat_history))

    messages_to_summarize = chat_history[:collapse_count]
    remaining_messages    = chat_history[collapse_count:]

    conversation_text = ""
    for msg in messages_to_summarize:
        role = "User" if isinstance(msg, HumanMessage) else "AI"
        conversation_text += f"{role}: {msg.content}\n\n"

    prev_summary = state.get("summary", "")

    system_prompt = """
    You are a conversation summarizer.
    Summarize the conversation concisely.
    Preserve all key facts, decisions, file names, and technical details.
    If a previous summary exists, merge it with the new conversation.
    """

    human_message = f"""
    Previous Summary:
    {prev_summary if prev_summary else "None"}

    Conversation to summarize:
    {conversation_text}

    Concise merged summary:
    """

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message)
    ])

    new_summary = response.content

    await graph.aupdate_state(
        config,
        {
            "summary":      new_summary,
            "chat_history": remaining_messages
        }
    )