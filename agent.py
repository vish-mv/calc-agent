"""
Simple LangChain tool-calling agent powered by OpenAI.

Tools included:
  - Calculator (safe math evaluation)
  - Web search (DuckDuckGo, no API key required)

Run interactively:
    python agent.py

Run a single query (useful for scripting / Docker one-shot runs):
    python agent.py "What is 12345 * 678, and who won the 2022 World Cup?"
"""

import os
import sys

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression, e.g. '2 + 2 * 3' or '(10-4)/2'.
    Only numbers and + - * / ( ) . are allowed."""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "Error: expression contains disallowed characters."
    try:
        # eval is safe here because we've whitelisted the character set above
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as exc:  # noqa: BLE001
        return f"Error evaluating expression: {exc}"


@tool
def web_search(query: str) -> str:
    """Search the web for current information using DuckDuckGo and return
    a short summary of the top results. Useful for questions about recent
    events or facts you are unsure of."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "web_search is unavailable: duckduckgo_search is not installed."

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"- {title}: {body} ({href})")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"Error performing search: {exc}"


TOOLS = [calculator, web_search]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
def build_agent() -> AgentExecutor:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Put it in a .env file or export it "
            "in your environment."
        )

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful, concise assistant. Use the available "
                "tools whenever they would help answer accurately "
                "(math -> calculator, current events / unknown facts -> "
                "web_search). If tools aren't needed, just answer directly.",
            ),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=TOOLS, verbose=True)


def main() -> None:
    executor = build_agent()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = executor.invoke({"input": query})
        print("\n=== FINAL ANSWER ===")
        print(result["output"])
        return

    print("LangChain agent ready. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if query.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not query:
            continue
        result = executor.invoke({"input": query})
        print(f"\nAgent: {result['output']}\n")


if __name__ == "__main__":
    main()
