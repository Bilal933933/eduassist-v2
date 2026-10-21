"""عقدة استكمال الحقول الحاجبة قبل تنفيذ طلب المعلم."""

from orchestration.interactions.schema import Interaction
from orchestration.interactions.slots import (
    build_question_response,
    build_questions,
    resolve_properties,
)
from orchestration.state import AgentState, append_node


def clarify_node(state: AgentState) -> dict:
    """بناء بطاقة أسئلة من الحقول الناقصة دون استدعاء نموذج."""
    intent = state["intent"]
    properties = resolve_properties(state)
    questions = build_questions(state)
    interaction = Interaction(
        intent=intent,
        properties=properties,
        questions=questions,
    ).model_dump(mode="json")
    return {
        "response": build_question_response(intent, questions),
        "interaction": interaction,
        "metadata": append_node(
            state.get("metadata"),
            "clarify",
            intent=intent,
            handled_by="clarify_node",
            response_source="interaction",
            missing_slots=[question.slot for question in questions],
            question_count=len(questions),
        ),
    }
