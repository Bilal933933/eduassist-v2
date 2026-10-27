const { spawn } = require("child_process");
const path = require("path");

const dir = __dirname;
const python = path.join(dir, ".venv", "Scripts", "python.exe");
// psycopg غير المتزامن يرفض حلقة Windows الافتراضية (ProactorEventLoop)
// فينهار الإقلاع — uvicorn يبني حلقته قبل استيراد التطبيق، لذلك نستبدل
// مصنع الحلقة هنا قبل بدء uvicorn (لا تنكير لـ ProactorEventLoop نفسه
// لأن psycopg يفحص isinstance ضده — الترقيع على مصنع uvicorn فقط).
const prelude = [
  "import asyncio",
  "import uvicorn.loops.asyncio as _ula",
  "_ula.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop",
  "from uvicorn import run",
  'run("main:app", host="127.0.0.1", port=5002, reload=True)',
].join("; ");
const child = spawn(python, ["-c", prelude], {
  cwd: dir,
  stdio: "inherit",
  env: { ...process.env, PYTHONUTF8: "1" },
});

child.on("exit", (code) => process.exit(code ?? 1));
child.on("error", (error) => {
  console.error("تعذر تشغيل الواجهة الخلفية:", error.message);
  process.exit(1);
});
process.on("SIGINT", () => child.kill());
process.on("SIGTERM", () => child.kill());
