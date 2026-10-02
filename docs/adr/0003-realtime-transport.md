# ADR-0003: اعتماد SSE كنقل أولي + المنافذ والمحولات للبث

## الحالة
معتمد

## السياق
- الرسم (Graph) يجب ألا يعرف تقنية النقل (SSE / مقبس الويب / نست).
- نحتاج بوابة تبديل تسمح بالانتقال إلى نست (NestJS) لاحقًا دون تغيير القلب أو الرسم أو الواجهة.

## القرار
- لغة الأحداث (`EventType` + `StreamEvent`) تسكن القلب: `core/events.py`.
- المنفذ (Port) الوحيد: `RealtimeTransport` (`connect`، `send`، `close`) في `core/ports/transport.py`.
- المحول (Adapter) الوحيد العامل: `SSEAdapter` في `realtime/adapters/`.
- المصنع (Factory): `create_transport(adapter: str)` — يستقبل الاسم حقنًا ولا يقرأ الإعدادات.
- الجذر (Composition Root): `main.py` يقرأ `REALTIME_ADAPTER` مرة واحدة ويبني النقل في `app.state`.

## البدائل المدروسة
- مسارا بث منفصلان (Stream + Non-Stream): مرفوض — يخالف القاعدة 7.
- الرسم يعرف SSE مباشرة: مرفوض — يخالف القاعدة 9.
- بناء محول نست الآن: مرفوض — تجريد مبكر يخالف القاعدة 10.

## النتائج
- إيجابيات: التبديل لنست = ملف محول جديد + قلب متغير بيئة فقط.
- سلبيات: `SSEAdapter.stream()` خاصة بـ SSE وتُستخدم من طبقة الواجهة فقط، لا من القلب.

## خطة الترحيل إلى نست
1. إضافة `realtime/adapters/nestjs_adapter.py` يطبق `RealtimeTransport`.
2. تغيير `REALTIME_ADAPTER=nestjs` في البيئة.
3. لا تغيير في `core/` أو `orchestration/` أو `api/` — أي تغيير فيها يعني كسر هذا القرار.
