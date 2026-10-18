"""مشرف تحضير الدرس: يقرر الوكيل التالي بناءً على الحالة."""

from typing import Literal

from langgraph.types import Command

from orchestration.lesson_prep.state import LessonPrepState

MAX_ITERATIONS = 15

AgentName = Literal[
    "retriever",
    "basic_info",
    "objectives",
    "prior_knowledge",
    "materials",
    "lesson_flow",
    "assessment",
    "homework",
    "differentiation",
    "notes",
    "assembler",
]


def route_next(state: LessonPrepState) -> Command:
    iteration = state.get("iteration", 0)
    if iteration >= MAX_ITERATIONS:
        return Command(goto="END")

    if "retrieved_chunks" not in state:
        next_agent = "retriever"
    elif not state.get("section_1_basic"):
        next_agent = "basic_info"
    elif not state.get("section_2_objectives"):
        next_agent = "objectives"
    elif not state.get("section_3_prior"):
        next_agent = "prior_knowledge"
    elif not state.get("section_4_materials"):
        next_agent = "materials"
    elif not state.get("section_5_flow"):
        next_agent = "lesson_flow"
    elif not state.get("section_6_assessment"):
        next_agent = "assessment"
    elif not state.get("section_7_homework"):
        next_agent = "homework"
    elif not state.get("section_8_differentiation"):
        next_agent = "differentiation"
    elif not state.get("section_9_notes"):
        next_agent = "notes"
    elif not state.get("final_lesson_plan"):
        next_agent = "assembler"
    else:
        next_agent = "END"

    return Command(goto=next_agent, update={"iteration": iteration + 1})
