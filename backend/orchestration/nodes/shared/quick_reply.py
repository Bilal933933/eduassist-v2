"""عقدة الرد السريع الحتمي."""

from orchestration.state import AgentState

QUICK_REPLY_TEXT = "يسعدني ذلك، وأنا جاهز لمساعدتك."
TEACHER_QUICK_REPLY_TEXT = "شكرًا، جاهز لمساعدتك في أي مهمة تعليمية."


def quick_reply_node(state: AgentState) -> dict:
    """إنتاج رد عام لأي صياغة يصنفها النموذج كرد سريع."""
    is_teacher = state.get("role") == "teacher"
    return {"response": TEACHER_QUICK_REPLY_TEXT if is_teacher else QUICK_REPLY_TEXT}
