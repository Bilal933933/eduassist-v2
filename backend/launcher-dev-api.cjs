const { spawn } = require("child_process");
const path = require("path");

const dir = __dirname;
const python = path.join(dir, ".venv", "Scripts", "python.exe");
const child = spawn(
  python,
  ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "5002"],
  { cwd: dir, stdio: "inherit" },
);

child.on("exit", (code) => process.exit(code ?? 1));
child.on("error", (error) => {
  console.error("تعذر تشغيل الواجهة الخلفية:", error.message);
  process.exit(1);
});
process.on("SIGINT", () => child.kill());
process.on("SIGTERM", () => child.kill());
