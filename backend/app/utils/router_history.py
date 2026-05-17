import tiktoken
from langchain_core.messages import HumanMessage,  AIMessage
enc = tiktoken.encoding_for_model("gpt-4o-mini")
def trim_by_tokens(text: str, max_tokens: int):

    tokens = enc.encode(text)

    if len(tokens) <= max_tokens:
        return text

    trimmed = enc.decode(tokens[:max_tokens])
    return trimmed + "..."


def build_router_history(chat_history, human_message_limit: int = 2, human_token_limit: int = 100, ai_char_limit: int = 500):

    human_messages = []
    last_ai_message = None

    for msg in reversed(chat_history):
        if (isinstance(msg, AIMessage) and last_ai_message is None):
            content = msg.content.strip()
            if len(content) > ai_char_limit:
                content = content[:ai_char_limit] + "..."
            last_ai_message = f"Assistant: {content}"

        elif isinstance(msg, HumanMessage):
            content = trim_by_tokens(msg.content.strip(), human_token_limit)
            human_messages.append(f"User: {content}")

            if ( len(human_messages)>= human_message_limit):
                break

    human_messages.reverse()
    result = []
    result.extend(human_messages)

    if last_ai_message:
        result.append(last_ai_message)

    return "\n".join(result)