"""عقد الردود الحتمية البسيطة."""

from orchestration.state import AgentState

GREETING_TEXT = "مرحبًا بك في مساعدك التعليمي."

QUICK_REPLY_TEXT = "يسعدني ذلك، وأنا جاهز لمساعدتك."


def greeting_node(state: AgentState) -> dict:
    """إنتاج رد التحية دون تعديل الحالة المدخلة."""
    _ = state
    return {"response": GREETING_TEXT}


def quick_reply_node(state: AgentState) -> dict:
    """إنتاج رد عام لأي صياغة يصنفها النموذج كرد سريع."""
    _ = state
    return {"response": QUICK_REPLY_TEXT}
