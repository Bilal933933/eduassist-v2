"""نقطة دخول تحضير الدرس: تحول بين AgentState و LessonPrepState."""

import logging
from collections.abc import Awaitable, Callable

from orchestration.lesson_prep.graph import build_lesson_prep_subgraph
from orchestration.lesson_prep.prompts import REFINE_SCOPE_TASK
from orchestration.lesson_prep.state import SECTION_FIELDS, SECTION_LABELS
from orchestration.state import AgentState, append_node
from retrieval.service import RetrievalService
from shared.json_parser import extract_json_object

logger = logging.getLogger("eduassist.lesson_prep.bridge")

CallModel = Callable[[str, str, float], Awaitable[str]]


def _parse_refine_targets(raw: str) -> list[str]:
    """قراءة الأقسام المستهدفة من رد النموذج؛ القائمة الفارغة تعني الخطة كلها."""
    data = extract_json_object(raw)
    values = data.get("sections") if data else None
    if not isinstance(values, list):
        return []
    if any(value == "all" for value in values if isinstance(value, str)):
        return []
    return [
        value
        for value in values
        if isinstance(value, str) and value in SECTION_FIELDS
    ]


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
        properties = state.get("properties") or {}
        is_refine = state.get("intent") == "lesson_refine"
        previous_plan = state.get("lesson_plan", "")
        previous_sections = state.get("lesson_sections") or {}

        # طلب تعديل بلا خطة محفوظة لا يُولّد درسًا عامًا باسم الطلب؛
        # التوضيح أرخص وأدق من خطة لا علاقة لها بالدرس المقصود.
        if is_refine and not previous_plan.strip():
            return {
                "response": (
                    "لا توجد خطة درس محفوظة في هذه المحادثة؛ لم يتم تحضير درس بعد. "
                    "اطلب تحضير درس أولًا ثم اطلب تعديل الجزء الذي تريده."
                ),
                "sections": {},
                "retried_sections": [],
                "failed_sections": [],
                "metadata": append_node(
                    state.get("metadata"),
                    "lesson_prep",
                    handled_by="lesson_prep_node",
                    response_source="clarification",
                    intent=state.get("intent"),
                    lesson_refine=True,
                    refine_missing_plan=True,
                    final_plan_generated=False,
                ),
            }

        # التحضير يبدأ من حالة نظيفة: أقسام وتعديلات الدور السابق محفوظة
        # في الحالة الأم للسجل فقط، وبذرها يخلط محتوى دورين في تقييم الناقد.
        # في التعديل يُقدَّم موضوع الخطة السابقة، ولا يُستخدم نص الطلب عنوانًا.
        if is_refine:
            topic = (
                str(properties.get("topic") or "")
                or state.get("lesson_topic")
                or context.get("topic")
                or ""
            )
        else:
            topic = (
                str(properties.get("topic") or "")
                or context.get("topic")
                or message
            )

        # النطاق ديناميكي: النموذج يحدد الأقسام التي يمسّها الطلب، والباقي يبقى.
        targets: list[str] = []
        structured_targets = properties.get("target_sections")
        if is_refine and isinstance(structured_targets, list):
            selected = [
                value
                for value in structured_targets
                if isinstance(value, str) and value in SECTION_FIELDS
            ]
            targets = [] if "all" in structured_targets else selected
        elif is_refine and previous_sections:
            try:
                scope_raw = await call_model(
                    REFINE_SCOPE_TASK.format(
                        topic=topic,
                        request=message,
                        section_catalog="\n".join(
                            f"- {name}: {label}"
                            for name, label in SECTION_LABELS.items()
                        ),
                    ),
                    "",
                    0.1,
                )
            except Exception:
                logger.exception(
                    "تعذر تحديد نطاق التعديل؛ ستُعاد صياغة الخطة كاملة."
                )
                scope_raw = ""
            targets = _parse_refine_targets(scope_raw)

        input_state: dict[str, str] = {
            "subject": context.get("subject", ""),
            "grade": str(properties.get("grade") or context.get("grade") or ""),
            "topic": topic,
        }
        if is_refine:
            # الخطة السابقة مرجع للتعديل لا بذرة أقسام مستهدفة.
            input_state["request"] = message
            input_state["previous_plan"] = previous_plan
            for name, field in SECTION_FIELDS.items():
                if not targets or name in targets:
                    continue
                previous_value = previous_sections.get(name)
                if previous_value:
                    input_state[field] = previous_value

        result = await subgraph.ainvoke(
            input_state,
            config={"recursion_limit": 120},
        )

        subgraph_metadata = result.get("metadata", {})
        final_plan = result.get("final_lesson_plan", "")
        produced_plan = bool(final_plan.strip())
        generated_sections = {
            name: result[field]
            for name, field in SECTION_FIELDS.items()
            if result.get(field)
        }
        sections = (
            {**previous_sections, **generated_sections}
            if is_refine
            else generated_sections
        )
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
            "lesson_topic": (
                topic if produced_plan else state.get("lesson_topic", topic)
            ),
            "lesson_plan": final_plan if produced_plan else previous_plan,
            "lesson_sections": sections if produced_plan else previous_sections,
            "metadata": append_node(
                state.get("metadata"),
                "lesson_prep",
                handled_by="lesson_prep_node",
                response_source="subgraph",
                intent=state.get("intent"),
                lesson_refine=is_refine,
                refine_targets=(
                    targets if targets else (["all"] if is_refine else [])
                ),
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
