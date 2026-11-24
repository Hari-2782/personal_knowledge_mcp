
import asyncio
import json
import os
import tempfile
from pathlib import Path

from groq import AsyncGroq
from mcp import Client

from client import ai_agent
from client.mcp_client import create_server_parameters


# ---------------------------------------------------------
# Evaluation knowledge base
# ---------------------------------------------------------

SEED_NOTES = {
    "python/memory_management.md": """
# Python Memory Management

Python manages memory through reference counting and cyclic garbage
collection. Objects are allocated in a private heap. The garbage
collector identifies reference cycles that reference counting alone
cannot reclaim.
""",
    "research/rag_architecture.md": """
# RAG Architecture

A Retrieval-Augmented Generation architecture contains document
ingestion, text chunking, embedding generation, vector indexing,
retrieval, and LLM generation. Hybrid retrieval combines semantic
search with keyword search to improve retrieval quality.
""",
    "learning/azure_ai_foundry.md": """
# Azure AI Foundry

Azure AI Foundry provides capabilities for building, evaluating,
and deploying generative AI applications. It supports model
catalogues, prompt flow, evaluations, and managed deployments.
""",
    "projects/pothole_detection.md": """
# Pothole Detection Research

The road hazard detection system uses YOLOv8 for visual detection.
Kalman filtering provides temporal validation to reduce false
positive detections. The system also includes a risk assessment
component for road hazards.
""",
    "projects/langgraph_workflow.md": """
# LangGraph Workflow

LangGraph models agent workflows as state graphs. Nodes execute
operations and edges define transitions between nodes. State is
shared across the graph execution.
""",
    "learning/langgraph_notes.md": """
# LangGraph Learning Notes

LangGraph supports cyclic agent workflows, state management,
conditional edges, and multi-step orchestration.
""",
    "learning/dp700_preparation.md": """
# DP-700 Preparation

Microsoft Fabric includes OneLake, Lakehouse, Warehouse,
Data Factory, Direct Lake, and semantic models. OneLake provides
a unified logical data lake for Fabric workloads.
""",
    "research/vector_databases.md": """
# Vector Databases

Vector databases store vector embeddings and support similarity
search. FAISS and pgvector are examples of technologies used
for vector search and retrieval applications.
""",
}


# ---------------------------------------------------------
# Ten evaluation cases
# ---------------------------------------------------------

EVALUATION_CASES = [
    {
        "id": 1,
        "query": (
            "Find my Python memory management note and read "
            "its full contents."
        ),
        "expected_sequence": ["search_notes", "read_note"],
        "evidence": ["reference counting"],
        "type": "read_after_search",
    },
    {
        "id": 2,
        "query": "Find notes about RAG architecture.",
        "expected_sequence": ["search_notes"],
        "evidence": ["rag_architecture.md"],
        "type": "search",
    },
    {
        "id": 3,
        "query": (
            "Create evaluation/mcp_server_development.md with "
            "the title MCP Server Development and this content: "
            "MCP_EVAL_WRITE_01: An MCP server exposes tools "
            "through the Model Context Protocol."
        ),
        "expected_sequence": ["write_note"],
        "evidence": ["MCP_EVAL_WRITE_01"],
        "type": "write",
        "path": "evaluation/mcp_server_development.md",
        "marker": "MCP_EVAL_WRITE_01",
    },
    {
        "id": 4,
        "query": "What did I document about Azure AI Foundry?",
        "expected_sequence": ["search_notes", "read_note"],
        "evidence": ["azure_ai_foundry.md"],
        "type": "search",
    },
    {
        "id": 5,
        "query": (
            "Read the complete note at "
            "projects/pothole_detection.md."
        ),
        "expected_sequence": ["read_note"],
        "evidence": ["YOLOv8"],
        "type": "read",
    },
    {
        "id": 6,
        "query": "Find all my notes mentioning LangGraph.",
        "expected_sequence": ["search_notes"],
        "evidence": ["langgraph_workflow.md"],
        "type": "search",
    },
    {
        "id": 7,
        "query": (
            "Save a note at learning/python_decorators.md "
            "with the title Python Decorators and this content: "
            "PYTHON_DECORATOR_EVAL: Decorators wrap functions "
            "to extend or modify their behaviour."
        ),
        "expected_sequence": ["write_note"],
        "evidence": ["PYTHON_DECORATOR_EVAL"],
        "type": "write",
        "path": "learning/python_decorators.md",
        "marker": "PYTHON_DECORATOR_EVAL",
    },
    {
        "id": 8,
        "query": (
            "Retrieve the complete note at "
            "learning/dp700_preparation.md."
        ),
        "expected_sequence": ["read_note"],
        "evidence": ["OneLake"],
        "type": "read",
    },
    {
        "id": 9,
        "query": "Which documents discuss vector databases?",
        "expected_sequence": ["search_notes"],
        "evidence": ["vector_databases.md"],
        "type": "search",
    },
    {
        "id": 10,
        "query": (
            "Create evaluation/ai_interview_preparation.md "
            "with the title AI Interview Preparation and this "
            "content: AI_INTERVIEW_EVAL: Preparation includes "
            "Python, machine learning, RAG, and system design."
        ),
        "expected_sequence": ["write_note"],
        "evidence": ["AI_INTERVIEW_EVAL"],
        "type": "write",
        "path": "evaluation/ai_interview_preparation.md",
        "marker": "AI_INTERVIEW_EVAL",
    },
]


# ---------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------

def seed_knowledge_base(root: Path) -> None:
    """Create deterministic notes for evaluation."""

    for relative_path, content in SEED_NOTES.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")


def tool_output_contains(
    tool_calls: list[dict],
    expected_terms: list[str],
) -> bool:
    """Check whether actual MCP results contain expected evidence."""

    combined_output = "\n".join(
        call["output"] for call in tool_calls
    ).casefold()

    return any(
        term.casefold() in combined_output
        for term in expected_terms
    )
def verify_final_answer(case: dict, answer: str) -> bool:
    answer = answer.casefold()

    answer_terms = {
        1: ["reference counting", "garbage collection"],
        2: ["rag", "retrieval"],
        4: ["azure ai foundry"],
        5: ["yolov8", "kalman"],
        6: ["langgraph"],
        8: ["onelake", "lakehouse"],
        9: ["vector database", "vector"],
    }

    if case["type"] == "write":
        path_mentioned = case["path"].casefold() in answer
        confirmation = any(
            word in answer for word in ["created", "saved", "successfully"]
        )
        return path_mentioned and confirmation

    return any(
        term in answer
        for term in answer_terms.get(case["id"], [])
    )

def verify_case(
    case: dict,
    tool_calls: list[dict],
    answer: str,
    knowledge_base: Path,
) -> dict:
    """Evaluate tool selection, execution, and task outcome."""

    actual_sequence = [
        call["tool"] for call in tool_calls
    ]

    expected_sequence = case["expected_sequence"]

    first_tool_correct = (
        bool(actual_sequence)
        and actual_sequence[0] == expected_sequence[0]
    )

    sequence_correct = (
            actual_sequence == expected_sequence
    )
    tool_call_budget = len(expected_sequence)

    efficient_execution = (
            len(tool_calls) <= tool_call_budget
    )
    answer_correct = verify_final_answer(case, answer)
    execution_success = (
        bool(tool_calls)
        and all(call["success"] for call in tool_calls)
    )

    if case["type"] == "write":
        written_file = knowledge_base / case["path"]

        outcome_correct = (
            written_file.is_file()
            and case["marker"] in written_file.read_text(
                encoding="utf-8"
            )
        )

    else:
        outcome_correct = tool_output_contains(
            tool_calls,
            case["evidence"],
        )

    return {
        "id": case["id"],
        "type": case["type"],
        "expected_tools": expected_sequence,
        "actual_tools": actual_sequence,
        "first_tool_correct": first_tool_correct,
        "sequence_correct": sequence_correct,
        "execution_success": execution_success,
        "outcome_correct": outcome_correct,
        "answer": answer,
        "tool_calls": tool_calls,
        "answer_correct": answer_correct,
        "efficient_execution": efficient_execution,
    }


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

async def run_evaluation():
    if not ai_agent.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not found in .env")

    results = []

    with tempfile.TemporaryDirectory(
        prefix="knowledge_mcp_eval_"
    ) as temporary_directory:

        knowledge_base = Path(temporary_directory)
        seed_knowledge_base(knowledge_base)

        # Explicitly isolate the MCP subprocess from the real KB.
        server_env = os.environ.copy()
        server_env["KNOWLEDGE_BASE_PATH"] = str(knowledge_base)

        groq_client = AsyncGroq(
            api_key=ai_agent.GROQ_API_KEY
        )

        try:
            server_parameters = create_server_parameters(
                env=server_env
            )

            async with Client(server_parameters) as mcp_client:

                mcp_response = await mcp_client.list_tools()
                mcp_tools = mcp_response.tools

                groq_tools = (
                    ai_agent.convert_mcp_tools_to_groq(
                        mcp_tools
                    )
                )

                allowed_tools = {
                    tool.name for tool in mcp_tools
                }

                print("\nDiscovered MCP tools:")
                for tool in mcp_tools:
                    print("-", tool.name)

                # Instrument the existing MCP execution function.
                original_execute = (
                    ai_agent.execute_mcp_tool
                )

                async def traced_execute_mcp_tool(
                    mcp_client,
                    tool_name,
                    arguments,
                    allowed_tools,
                ):
                    output = await original_execute(
                        mcp_client=mcp_client,
                        tool_name=tool_name,
                        arguments=arguments,
                        allowed_tools=allowed_tools,
                    )

                    current_calls = active_trace["calls"]

                    success = not output.startswith((
                        "Error:",
                        "MCP tool execution failed:",
                        "Tool execution failed:",
                    ))

                    current_calls.append({
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": success,
                        "output": output,
                    })

                    return output

                ai_agent.execute_mcp_tool = (
                    traced_execute_mcp_tool
                )

                try:
                    for case in EVALUATION_CASES:

                        print("\n" + "=" * 65)
                        print(
                            f"TEST {case['id']}/"
                            f"{len(EVALUATION_CASES)}"
                        )
                        print("Query:", case["query"])

                        active_trace = {"calls": []}

                        conversation = [{
                            "role": "system",
                            "content": ai_agent.SYSTEM_PROMPT,
                        }]

                        answer = (
                            await ai_agent.process_user_message(
                                user_message=case["query"],
                                conversation=conversation,
                                groq_client=groq_client,
                                mcp_client=mcp_client,
                                groq_tools=groq_tools,
                                allowed_tools=allowed_tools,
                            )
                        )

                        case_result = verify_case(
                            case=case,
                            tool_calls=active_trace["calls"],
                            answer=answer,
                            knowledge_base=knowledge_base,
                        )

                        results.append(case_result)

                        print("Expected:", case_result["expected_tools"])
                        print("Actual:", case_result["actual_tools"])
                        print(
                            "First tool correct:",
                            case_result["first_tool_correct"],
                        )
                        print(
                            "Sequence correct:",
                            case_result["sequence_correct"],
                        )
                        print(
                            "Execution successful:",
                            case_result["execution_success"],
                        )
                        print(
                            "Task outcome correct:",
                            case_result["outcome_correct"],
                        )
                        print("Answer:", answer)

                finally:
                    ai_agent.execute_mcp_tool = original_execute

        finally:
            await groq_client.close()

    # -----------------------------------------------------
    # Summary and report
    # -----------------------------------------------------

    total = len(results)

    first_tool_score = sum(
        result["first_tool_correct"]
        for result in results
    )

    sequence_score = sum(
        result["sequence_correct"]
        for result in results
    )

    execution_score = sum(
        result["execution_success"]
        for result in results
    )

    outcome_score = sum(
        result["outcome_correct"]
        for result in results
    )

    answer_score = sum(
        result["answer_correct"] for result in results
    )

    overall_score = sum(
        result["first_tool_correct"]
        and result["sequence_correct"]
        and result["execution_success"]
        and result["outcome_correct"]
        for result in results
    )
    efficiency_score = sum(
        result["efficient_execution"]
        for result in results
    )
    efficiency_accuracy = (
        efficiency_score / len(results) * 100
        if results else 0
    )
    summary = {
        "model": ai_agent.GROQ_MODEL,
        "total_cases": total,
        "first_tool_accuracy": f"{first_tool_score}/{total}",
        "sequence_accuracy": f"{sequence_score}/{total}",
        "tool_execution_success": f"{execution_score}/{total}",
        "task_outcome_accuracy": f"{outcome_score}/{total}",
        "overall_passed": f"{overall_score}/{total}",
        "target": "8/10",
        "target_met": overall_score >= 8,
        "results": results,
        "final_answer_accuracy": f"{answer_score}/{total}",

    }

    report_path = Path("evaluation_results.json")
    report_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("AI AGENT EVALUATION SUMMARY")
    print("=" * 65)
    print("Model:", summary["model"])
    print("First tool accuracy:", summary["first_tool_accuracy"])
    print("Sequence accuracy:", summary["sequence_accuracy"])
    print("Tool execution:", summary["tool_execution_success"])
    print("Task outcome:", summary["task_outcome_accuracy"])
    print("Overall passed:", summary["overall_passed"])
    print("Target met:", summary["target_met"])
    print("Report:", report_path.resolve())
    print(f"Efficiency: {efficiency_score}/{len(results)}")
    print(f"Efficiency accuracy: {efficiency_accuracy:.1f}%")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
