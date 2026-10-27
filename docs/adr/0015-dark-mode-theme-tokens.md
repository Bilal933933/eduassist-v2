# ADR-0015: الوضع الداكن ورموز الثيم في الواجهة

## الحالة
معتمد

## السياق
- طُلب مبدّل ثيم وفق توثيق شاد سن (shadcn/ui): `next-themes` + صنف `.dark` على `<html>`
  + مكوّن `ModeToggle` بقائمة منسدلة.
- الواجهة كانت تكتب الألوان صراحةً (`bg-white`, `text-slate-900`, `border-slate-200`)
  في 14 ملفًا ونحو 166 موضعًا؛ لذلك كان تبديل الصنف `.dark` يغيّر القوائم المنسدلة
  وحدها وتبقى الصفحة فاتحة، أي أن أثر المبدّل البصري كان صفرًا.
- قيود المشروع: `@base-ui/react` لا Radix، وتايلويند v4، ونمط شاد سن `base-nova`،
  وواجهة RTL، ورموز ألوان جاهزة في `app/globals.css` (`:root` و`.dark`).
- في Base UI، `DropdownMenuLabel` مبني على `Menu.GroupLabel` ويشترط سياق
  `Menu.Group` أو `Menu.RadioGroup`؛ وضعه شقيقًا للـ`RadioGroup` يُسقط التطبيق برسالة
  `Base UI: MenuGroupContext is missing`.

## القرار
- يبقى `ThemeProvider` في `app/providers.tsx` بـ`attribute="class"`،
  و`defaultTheme="system"`، و`enableSystem` — لا تغيير على الافتراضي.
- `components/theme-toggle.tsx` يتبع نمط شاد سن الرسمي (قائمة منسدلة + `Sun`/`Moon`)
  مُهيَّأً لـBase UI عبر `render={<Button/>}` بدل `asChild`، بثلاثة خيارات
  (فاتح / داكن / النظام) داخل `DropdownMenuRadioGroup`، وبلا `DropdownMenuLabel`.
- حارس الترطيب عبر `useSyncExternalStore` لا `useState` + `useEffect`، التزامًا بقاعدة
  `react-hooks/set-state-in-effect`.
- كل سطح واجهة يستخدم رموز الثيم الدلالية بدل الألوان الصريحة:
  `bg-background`, `bg-muted`, `text-foreground`, `text-muted-foreground`,
  `border-border`, `hover:bg-accent` — مع نظير `dark:` للتمييزات الملوّنة
  (emerald / red / amber) بشفافية (`/10`, `/15`, `/30`) لا بألوان صلبة.
- الوضع الفاتح يبقى مطابقًا بصريًا: قيم `:root` الحالية هي نفس الدرجات السابقة،
  والفرق الوحيد أن المحايد `neutral` حلّ محل `slate` في الرمادي الفاتح.
- الإشعارات (sonner) تتبع الثيم: مكوّن `ThemedToaster` داخل `ThemeProvider` يمرّر
  `resolvedTheme` إلى `Toaster` بدل بقاء الإشعار فاتحًا في الوضع الداكن.
- استثناءات مقصودة: `app/page.tsx`, `app/login`, `app/register` تصميمها داكن أصلاً
  (`bg-slate-950`)، وكتلة الكود في `features/chat/components/rich-text.tsx`
  (`bg-slate-900`) داكنة بطبعها في الوضعين.

## البدائل المدروسة
- إبقاء الألوان الصريحة وإضافة `dark:` لكل موضع يدويًا: مرفوض؛ نحو 166 موضعًا بلا
  مصدر واحد، وأي تعديل لاحق يتطلب تكراره.
- `defaultTheme="dark"`: مرفوض؛ يفرض على المستخدم تجربة غير مطلوبة.
- `asChild` كما في توثيق شاد سن: غير متاح في Base UI.
- `DropdownMenuLabel` داخل `DropdownMenuGroup` لإبقاء عنوان «المظهر»: مرفوض؛ حشو
  بلا وظيفة مقابل ثلاثة عناصر واضحة أصلاً.
- تحويل صفحات الهبوط الداكنة إلى رموز ثيم: مرفوض حاليًا؛ داكنها قرار تصميمي لا سهو.

## النتائج
- 166 موضعًا محوَّلاً في 14 ملفًا، إضافةً إلى `components/theme-toggle.tsx` (جديد)
  و`app/providers.tsx` (مزوّد الإشعارات).
- `npx tsc --noEmit` = 0، و`npx eslint .` = 0 خطأ (يبقى تحذيران قديمان غير متعلقين:
  `handledBy` في `response-metadata.tsx` و`Separator` في `conversation-list.tsx`).
- تحقق بصري في متصفح حقيقي للوضعين: `/chat/new`, `/chat/[id]`, `/profile`,
  القائمة المنسدلة، والإشعارات — بلا أخطاء كونسول، وتبديل «داكن» يضبط
  `class="dark"` و`theme=dark` في `localStorage`.
- سلبيات: الرمادي الفاتح صار محايدًا (`neutral`) بدل `slate`، وفرقه بصري طفيف جدًا.

## خطة الترحيل
لا ترحيل بيانات ولا هجرة مخطط. أي سطح جديد يلتزم برموز الثيم، ويُمنع استخدام
`bg-white` أو `text-slate-*` أو `bg-slate-*` في `app/` و`features/` خارج الاستثناءات
المذكورة أعلاه؛ تُضاف التمييزات الملوّنة بنظير `dark:` من البداية.
