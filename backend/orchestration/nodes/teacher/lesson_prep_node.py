"""نقطة دخول تحضير الدرس: تحول بين AgentState و LessonPrepState."""

from collections.abc import Awaitable, Callable

from orchestration.lesson_prep.graph import build_lesson_prep_subgraph
from orchestration.state import AgentState
from retrieval.service import RetrievalService

CallModel = Callable[[str, str, float], Awaitable[str]]


def create_lesson_prep_node(
    *,
    call_model: CallModel,
    retrieval_service: RetrievalService | None,
):
    subgraph = build_lesson_prep_subgraph(
        call_model=call_model,
        retrieval_service=retrieval_service,
    )

    async def lesson_prep_node(state: AgentState) -> dict:
        context = state.get("context", {})
        input_state = {
            "subject": context.get("subject", ""),
            "grade": context.get("grade", ""),
            "topic": context.get("topic") or state["messages"][-1],
            "sections": state.get("sections", {}),
            "retried_sections": state.get("retried_sections", []),
        }
        result = await subgraph.ainvoke(input_state)
        
        subgraph_metadata = result.get("metadata", {})

        return {
            "response": result.get("final_lesson_plan", ""),
            "sections": result.get("sections", {}),
            "retried_sections": result.get("retried_sections", []),
            "metadata": {
                **state.get("metadata", {}),
                "handled_by": "lesson_prep_node",
                "intent": state.get("intent"),
                "subgraph_nodes_executed": subgraph_metadata.get(
                    "nodes_executed", []
                ),
                "retrieval_used": bool(result.get("retrieved_chunks")),
                "final_plan_generated": bool(result.get("final_lesson_plan")),
            },
        }

    return lesson_prep_node
