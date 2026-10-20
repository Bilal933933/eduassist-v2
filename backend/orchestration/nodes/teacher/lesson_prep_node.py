"""نقطة دخول تحضير الدرس: تحول بين AgentState و LessonPrepState."""

from collections.abc import Awaitable, Callable

from orchestration.lesson_prep.graph import build_lesson_prep_subgraph
from orchestration.state import AgentState, append_node
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
        # التحضير يبدأ من حالة نظيفة: أقسام وتعديلات الدور السابق محفوظة
        # في الحالة الأم للسجل فقط، وبذرها يخلط محتوى دورين في تقييم الناقد.
        input_state = {
            "subject": context.get("subject", ""),
            "grade": context.get("grade", ""),
            "topic": context.get("topic") or state["messages"][-1],
        }
        result = await subgraph.ainvoke(
            input_state,
            config={"recursion_limit": 80},
        )

        subgraph_metadata = result.get("metadata", {})

        return {
            "response": result.get("final_lesson_plan", ""),
            "sections": result.get("sections", {}),
            "retried_sections": result.get("retried_sections", []),
            "metadata": append_node(
                state.get("metadata"),
                "lesson_prep",
                handled_by="lesson_prep_node",
                response_source="subgraph",
                intent=state.get("intent"),
                subgraph_nodes_executed=list(
                    subgraph_metadata.get("nodes_path") or []
                ),
                retrieval_used=bool(result.get("retrieved_chunks")),
                final_plan_generated=bool(result.get("final_lesson_plan")),
                quality_score=subgraph_metadata.get("quality_score"),
                retried_sections=list(result.get("retried_sections", [])),
            ),
        }

    return lesson_prep_node
