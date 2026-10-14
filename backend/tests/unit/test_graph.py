"""اختبارات رسم الترحيب وعقدته."""
from graph import GREETING_TEXT, build_graph, checkpoint_config, greeting_node


def test_greeting_node_is_pure() -> None:
    """عقدة الترحيب لا تعدل الحالة المدخلة."""
    state = {"messages": ["مرحبًا"], "teacher_id": "teacher-1"}
    snapshot = dict(state)
    assert greeting_node(state) == {"response": GREETING_TEXT}
    assert state == snapshot


def test_checkpoint_is_isolated_by_teacher_and_thread() -> None:
    """لا تتشارك المحادثات الحالة بين مستخدمين مختلفين."""
    greeting_graph = build_graph()
    greeting_graph.invoke(
        {"messages": ["الأولى"], "teacher_id": "user-1"},
        checkpoint_config("user-1", "shared"),
    )
    result = greeting_graph.invoke(
        {"messages": ["الثانية"], "teacher_id": "user-2"},
        checkpoint_config("user-2", "shared"),
    )
    assert result["messages"] == ["الثانية"]
