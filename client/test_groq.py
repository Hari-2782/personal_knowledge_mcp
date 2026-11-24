
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not api_key:
    raise RuntimeError("GROQ_API_KEY not found in .env")

client = Groq(api_key=api_key)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "Explain Model Context Protocol (MCP) "
                    "in exactly two sentences."
                )
            }
        ],
        temperature=0.6,
        max_completion_tokens=2048,
        include_reasoning=False,
        stream=False,
    )

    choice = response.choices[0]
    message = choice.message

    print("\n========== GROQ API TEST ==========")
    print("Model:", response.model)
    print("Finish reason:", choice.finish_reason)
    print("Usage:", response.usage)

    if message.content:
        print("\nGenerated answer:")
        print(message.content)
    elif message.tool_calls:
        print("\nTool calls returned:")
        for tool_call in message.tool_calls:
            print(tool_call.function.name)
    else:
        print("\nNo user-facing text or tool call returned.")
        print("Message object:", message.model_dump())

        raise RuntimeError(
            "Groq returned an empty response."
        )

    print("\n========== TEST PASSED ==========")

except Exception as error:
    print("\n========== TEST FAILED ==========")
    print(type(error).__name__, str(error))
    raise
