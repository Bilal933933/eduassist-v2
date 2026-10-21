"""نقطة دخول تحضير الدرس: تحول بين AgentState و LessonPrepState."""

from collections.abc import Awaitable, Callable

from orchestration.lesson_prep.graph import build_lesson_prep_subgraph
from orchestration.lesson_prep.state import SECTION_FIELDS
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
        message = state["messages"][-1]
        is_refine = state.get("intent") == "lesson_refine"

        # التحضير يبدأ من حالة نظيفة: أقسام وتعديلات الدور السابق محفوظة
        # في الحالة الأم للسجل فقط، وبذرها يخلط محتوى دورين في تقييم الناقد.
        topic = context.get("topic")
        if not topic and is_refine:
            topic = state.get("lesson_topic")
        topic = topic or message

        input_state: dict[str, str] = {
            "subject": context.get("subject", ""),
            "grade": context.get("grade", ""),
            "topic": topic,
        }
        if is_refine:
            # الخطة السابقة مرجع للتعديل لا بذرة أقسام: كل قسم يُعاد صياغته.
            input_state["request"] = message
            input_state["previous_plan"] = state.get("lesson_plan", "")

        result = await subgraph.ainvoke(
            input_state,
            config={"recursion_limit": 120},
        )

        subgraph_metadata = result.get("metadata", {})
        final_plan = result.get("final_lesson_plan", "")
        produced_plan = bool(final_plan.strip())
        sections = {
            name: result[field]
            for name, field in SECTION_FIELDS.items()
            if result.get(field)
        }
        failed_sections = list(
            dict.fromkeys(
                name
                for name in result.get("failed_sections", [])
                if not result.get(SECTION_FIELDS.get(name, ""), "")
            )
        )

        return {
            "response": final_plan,
            "sections": sections,
            "retried_sections": result.get("retried_sections", []),
            "failed_sections": failed_sections,
            # لا تُستبدل آخر خطة ناجحة بخطة فاشلة فارغة.
            "lesson_topic": topic if produced_plan else state.get("lesson_topic", topic),
            "lesson_plan": final_plan if produced_plan else state.get("lesson_plan", ""),
            "metadata": append_node(
                state.get("metadata"),
                "lesson_prep",
                handled_by="lesson_prep_node",
                response_source="subgraph",
                intent=state.get("intent"),
                lesson_refine=is_refine,
                subgraph_nodes_executed=list(
                    subgraph_metadata.get("nodes_path") or []
                ),
                retrieval_used=bool(result.get("retrieved_chunks")),
                final_plan_generated=produced_plan,
                quality_score=subgraph_metadata.get("quality_score"),
                retried_sections=list(result.get("retried_sections", [])),
                failed_sections=failed_sections,
            ),
        }

    return lesson_prep_node
