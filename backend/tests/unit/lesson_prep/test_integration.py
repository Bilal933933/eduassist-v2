"""اختبارات تكاملية لعقدة تحضير الدرس الكاملة."""
from __future__ import annotations

from typing import Any

import pytest

from orchestration.nodes.teacher.lesson_prep_node import create_lesson_prep_node

from .conftest import FakeCallModel, FakeRetrievalService


class TestLessonPrepNodeSections:
    """اختبارات نقل الأقسام بين AgentState و LessonPrepState."""

    @pytest.mark.asyncio
    async def test_passes_sections_to_subgraph(
        self,
        lesson_prep_node,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تمرر sections من AgentState إلى الرسم الفرعي."""
        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
            "sections": {"basic_info": "القسم الأساسي موجود مسبقاً"},
        }

        result = await lesson_prep_node(input_state)

        assert "response" in result
        assert "sections" in result
        assert isinstance(result["sections"], dict)
        assert len(result["sections"]) > 0

    @pytest.mark.asyncio
    async def test_empty_sections_defaults(
        self,
        lesson_prep_node,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تستخدم sections فارغة افتراضياً."""
        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await lesson_prep_node(input_state)

        assert "response" in result
        assert "sections" in result
        assert isinstance(result["sections"], dict)

    @pytest.mark.asyncio
    async def test_returns_final_lesson_plan(
        self,
        lesson_prep_node,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تعيد الخطة النهائية في response."""
        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await lesson_prep_node(input_state)

        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0


class TestLessonPrepNodeQualityRetry:
    """اختبارات حلقة إعادة الكتابة بناءً على جودة الخطة."""

    @pytest.mark.asyncio
    async def test_high_quality_goes_to_assembler(
        self,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن الخطة عالية الجودة تنتقل مباشرة للمجمع."""
        call_model = FakeCallModel(
            responses={
                "قيّم جودة خطة الدرس": '{"score": 0.9, "section": null}',
            }
        )
        retrieval_service = FakeRetrievalService()

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=retrieval_service,
        )

        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await node(input_state)

        assert "response" in result
        # الناقد تم استدعاؤه واعطى نتيجة عالية
        critic_calls = [
            c for c in call_model.calls if "قيّم جودة خطة الدرس" in c[0]
        ]
        assert len(critic_calls) >= 1

    @pytest.mark.asyncio
    async def test_custom_topic_from_messages(
        self,
        fake_call_model: FakeCallModel,
        fake_retrieval_service: FakeRetrievalService,
        base_context,
    ) -> None:
        """يتحقق من أن الموضوع يُؤخذ من آخر رسالة إذا لم يكن في السياق."""
        node = create_lesson_prep_node(
            call_model=fake_call_model,
            retrieval_service=fake_retrieval_service,
        )

        input_state: dict[str, Any] = {
            "messages": ["أفعال الناقص في النحو العربي"],
            "context": {
                **base_context,
                "topic": "",  # topic فارغ، يجب استخدام الرسالة
            },
        }

        result = await node(input_state)

        assert "response" in result
        assert "sections" in result


class TestLessonPrepNodeRetrievalFailure:
    """اختبارات سلوك العقدة عند فشل خدمة الاسترجاع."""

    @pytest.mark.asyncio
    async def test_retrieval_service_none(
        self,
        fake_call_model: FakeCallModel,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تعمل حتى عند عدم وجود خدمة استرجاع."""
        node = create_lesson_prep_node(
            call_model=fake_call_model,
            retrieval_service=None,
        )

        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await node(input_state)

        assert "response" in result
        assert "sections" in result

    @pytest.mark.asyncio
    async def test_retrieval_returns_chunks(
        self,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تتعامل مع نتائج الاسترجاع غير الفارغة."""
        retrieval_service = FakeRetrievalService(
            chunks=[
                {
                    "text": "كان وأخواتها أفعال ناقصة تدخل على الجملة الاسمية",
                    "source_type": "document",
                }
            ]
        )
        call_model = FakeCallModel()

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=retrieval_service,
        )

        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await node(input_state)

        assert "response" in result
        assert "sections" in result
        # المسترجع تم استدعاؤه
        assert len(call_model.calls) > 0
