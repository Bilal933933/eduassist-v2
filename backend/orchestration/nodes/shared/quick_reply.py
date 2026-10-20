"""عقدة الرد السريع الحتمي."""

from orchestration.state import AgentState, append_node, user_is_teacher

QUICK_REPLY_TEXT = "يسعدني ذلك، وأنا جاهز لمساعدتك."
TEACHER_QUICK_REPLY_TEXT = "شكرًا، جاهز لمساعدتك في أي مهمة تعليمية."


def quick_reply_node(state: AgentState) -> dict:
    """إنتاج رد عام لأي صياغة يصنفها النموذج كرد سريع."""
    is_teacher = user_is_teacher(state)
    return {
        "response": TEACHER_QUICK_REPLY_TEXT if is_teacher else QUICK_REPLY_TEXT,
        "metadata": append_node(
            state.get("metadata"),
            "quick_reply",
            handled_by="quick_reply_node",
            response_source="template",
        ),
    }
