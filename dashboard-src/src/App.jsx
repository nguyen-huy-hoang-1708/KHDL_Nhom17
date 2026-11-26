import { useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, BarChart3, Brain, CalendarClock, CheckCircle2,
  CloudDownload, CloudRain, Database, Droplets, Gauge, Layers, LineChart as LineIcon, Moon,
  Rocket, ScanSearch, Sparkles, Sun, Thermometer, Wand2, Wind,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, Brush, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const D = window.PM25_DATA;
const LIMIT = 50;
const ACCENT = "#6366f1";

/* ---------------------------------------------------------------- helpers */
const fmt = (v, n = 1) => (v == null ? "–" : Number(v).toLocaleString("vi-VN", { maximumFractionDigits: n, minimumFractionDigits: n }));
const fmtDate = (s, opt = { day: "2-digit", month: "2-digit", year: "numeric" }) => new Date(s).toLocaleDateString("vi-VN", opt);
const pad = (n) => String(n).padStart(2, "0");
const dm = (s) => { const d = new Date(s); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`; };
const my = (s) => { const d = new Date(s); return `${pad(d.getMonth() + 1)}/${String(d.getFullYear()).slice(2)}`; };
const levelOf = (pm) =>
  pm <= 25 ? { name: "Tốt", color: "#22c55e" } :
  pm <= 50 ? { name: "Trung bình", color: "#eab308" } :
  pm <= 80 ? { name: "Kém", color: "#f97316" } :
  pm <= 150 ? { name: "Xấu", color: "#ef4444" } : { name: "Rất xấu", color: "#a855f7" };

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  return [dark, setDark];
}

const chartTheme = (dark) => ({
  grid: dark ? "#27272a" : "#e4e4e7",
  axis: dark ? "#71717a" : "#a1a1aa",
  text: dark ? "#d4d4d8" : "#3f3f46",
  primary: dark ? "#818cf8" : "#6366f1",
  secondary: dark ? "#fb923c" : "#f97316",
  muted: dark ? "#52525b" : "#d4d4d8",
});

/* ---------------------------------------------------------------- ui primitives */
function Card({ className = "", children, ...p }) {
  return (
    <div
      className={`rounded-2xl border border-zinc-200/80 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] backdrop-blur
        dark:border-zinc-800/80 dark:bg-zinc-900/60 dark:shadow-none ${className}`}
      {...p}
    >
      {children}
    </div>
  );
}

function CardHeader({ icon: Icon, title, subtitle, right }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="grid size-8 shrink-0 place-items-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
            <Icon size={16} strokeWidth={2} />
          </div>
        )}
        <div>
          <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

function Segmented({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-zinc-200 bg-zinc-100/70 p-0.5 text-xs dark:border-zinc-800 dark:bg-zinc-900">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`whitespace-nowrap rounded-md px-2.5 py-1 font-medium transition-all ${
            value === o.value
              ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-white"
              : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Pill({ color, children }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ borderColor: color + "55", background: color + "18", color }}>
      <span className="size-1.5 rounded-full" style={{ background: color }} />
      {children}
    </span>
  );
}

function ChartTooltip({ active, payload, label, labelFormat = (l) => l, unit = " µg/m³" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-zinc-200 bg-white/95 px-3 py-2 text-xs shadow-lg backdrop-blur dark:border-zinc-700 dark:bg-zinc-900/95">
      <div className="mb-1 font-medium text-zinc-500 dark:text-zinc-400">{labelFormat(label)}</div>
      {payload.filter((p) => p.value != null).map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: p.color || p.payload?.fill }} />
            {p.name}
          </span>
          <span className="font-mono font-semibold tabular-nums">{fmt(p.value)}{unit}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- sections */
function Header({ dark, setDark }) {
  return (
    <header className="sticky top-0 z-30 border-b border-zinc-200/70 bg-zinc-50/70 backdrop-blur-xl dark:border-zinc-800/70 dark:bg-zinc-950/70">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid size-7 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm">
            <Wind size={15} strokeWidth={2.5} />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold tracking-tight">PM2.5 Hà Nội</span>
            <span className="text-zinc-300 dark:text-zinc-700">/</span>
            <span className="text-zinc-500 dark:text-zinc-400">Nhóm 17</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden items-center gap-1.5 rounded-full border border-zinc-200 px-2.5 py-1 text-xs text-zinc-500 sm:inline-flex dark:border-zinc-800 dark:text-zinc-400">
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex size-1.5 rounded-full bg-emerald-500" />
            </span>
            Cập nhật {D.generated}
          </span>
          <button
            onClick={() => setDark(!dark)}
            aria-label="Đổi giao diện sáng/tối"
            className="grid size-8 place-items-center rounded-lg border border-zinc-200 bg-white text-zinc-600 transition hover:bg-zinc-100 hover:text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white"
          >
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
          <Sparkles size={12} /> Project Nhập môn Khoa học dữ liệu
        </div>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Chất lượng không khí Hà Nội</h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-500 dark:text-zinc-400">
          Phân tích {D.kpi.hours.toLocaleString("vi-VN")} bản ghi theo giờ ({fmtDate(D.range[0])} – {fmtDate(D.range[1])})
          và dự báo nồng độ bụi mịn PM2.5 ngày hôm sau bằng học máy.
        </p>
      </div>
      <div className="flex gap-2 text-xs text-zinc-500 dark:text-zinc-400">
        <span className="rounded-md border border-zinc-200 px-2 py-1 dark:border-zinc-800">Nguồn: Open-Meteo · CAMS · ERA5</span>
        <span className="rounded-md border border-zinc-200 px-2 py-1 dark:border-zinc-800">QCVN 05:2023 · 50 µg/m³</span>
      </div>
    </div>
  );
}

function KpiCard({ icon: Icon, label, value, unit, delta, deltaGood, hint, tone = "indigo" }) {
  const tones = {
    indigo: "from-indigo-500/15 text-indigo-600 dark:text-indigo-400",
    orange: "from-orange-500/15 text-orange-600 dark:text-orange-400",
    rose: "from-rose-500/15 text-rose-600 dark:text-rose-400",
    emerald: "from-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  };
  return (
    <Card className="group relative overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:border-zinc-300 hover:shadow-lg hover:shadow-zinc-200/50 dark:hover:border-zinc-700 dark:hover:shadow-black/30">
      <div className={`pointer-events-none absolute -right-10 -top-10 size-32 rounded-full bg-gradient-to-br ${tones[tone]} to-transparent opacity-60 blur-2xl transition-opacity duration-500 group-hover:opacity-100`} />
      <div className="relative flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</span>
        <Icon size={16} className={tones[tone].split(" ").slice(1).join(" ")} />
      </div>
      <div className="relative mt-3 flex items-baseline gap-1.5">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">{value}</span>
        {unit && <span className="text-sm text-zinc-500 dark:text-zinc-400">{unit}</span>}
      </div>
      <div className="relative mt-2 flex items-center gap-1.5 text-xs">
        {delta && (
          <span className={`inline-flex items-center gap-0.5 font-medium ${deltaGood ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
            {deltaGood ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}{delta}
          </span>
        )}
        <span className="text-zinc-500 dark:text-zinc-400">{hint}</span>
      </div>
    </Card>
  );
}

function TimeSeriesCard({ t }) {
  const [range, setRange] = useState("1y");
  const data = useMemo(() => {
    if (range === "all") return D.series;
    const end = new Date(D.range[1]);
    const start = new Date(end);
    start.setFullYear(end.getFullYear() - (range === "1y" ? 1 : 2));
    return D.series.filter((p) => new Date(p.d) >= start);
  }, [range]);
  const stats = useMemo(() => {
    const v = data.map((p) => p.pm);
    return { mean: v.reduce((a, b) => a + b, 0) / v.length, max: Math.max(...v), exceed: (v.filter((x) => x > LIMIT).length / v.length) * 100 };
  }, [data]);

  return (
    <Card className="lg:col-span-8">
      <CardHeader
        icon={LineIcon}
        title="Diễn biến PM2.5 trung bình ngày"
        subtitle="Đường cam: trung bình trượt 30 ngày · nét đứt: ngưỡng QCVN"
        right={<Segmented value={range} onChange={setRange} options={[{ value: "1y", label: "1 năm" }, { value: "2y", label: "2 năm" }, { value: "all", label: "Toàn bộ" }]} />}
      />
      <div className="mb-3 grid grid-cols-3 gap-2">
        {[["Trung bình", fmt(stats.mean), "µg/m³"], ["Cao nhất", fmt(stats.max), "µg/m³"], ["Ngày vượt chuẩn", fmt(stats.exceed, 0), "%"]].map(([l, v, u]) => (
          <div key={l} className="rounded-lg bg-zinc-50 px-3 py-2 dark:bg-zinc-800/40">
            <div className="text-[11px] text-zinc-500 dark:text-zinc-400">{l}</div>
            <div className="font-mono text-sm font-semibold tabular-nums">{v} <span className="font-sans text-xs font-normal text-zinc-500">{u}</span></div>
          </div>
        ))}
      </div>
      <div className="h-72">
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="pmFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={t.primary} stopOpacity={0.35} />
                <stop offset="100%" stopColor={t.primary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={t.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="d" tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={50}
              tickFormatter={my} />
            <YAxis tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip content={<ChartTooltip labelFormat={(l) => fmtDate(l)} />} cursor={{ stroke: t.axis, strokeDasharray: "3 3" }} />
            <ReferenceLine y={LIMIT} stroke="#ef4444" strokeDasharray="5 4" strokeOpacity={0.7}
              label={{ value: "QCVN 50", position: "insideTopRight", fill: "#ef4444", fontSize: 11 }} />
            <Area type="monotone" dataKey="pm" name="PM2.5" stroke={t.primary} strokeWidth={1.2} fill="url(#pmFill)" animationDuration={600} />
            <Area type="monotone" dataKey="ma" name="TB 30 ngày" stroke={t.secondary} strokeWidth={2.2} fill="none" animationDuration={600} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function ProbRing({ value, color }) {
  const r = 26, c = 2 * Math.PI * r;
  return (
    <div className="relative size-16">
      <svg viewBox="0 0 64 64" className="size-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" strokeWidth="6" className="stroke-zinc-200 dark:stroke-zinc-800" />
        <circle cx="32" cy="32" r={r} fill="none" strokeWidth="6" stroke={color} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - value)} style={{ transition: "stroke-dashoffset 1s ease" }} />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-sm font-semibold tabular-nums">{Math.round(value * 100)}%</span>
    </div>
  );
}

function ForecastCard({ t }) {
  const f = D.forecast;
  if (!f)
    return (
      <Card className="flex flex-col items-center justify-center text-center lg:col-span-4">
        <AlertTriangle className="mb-2 text-amber-500" />
        <p className="text-sm font-medium">Chưa có dự báo thời gian thực</p>
        <p className="mt-1 text-xs text-zinc-500">Chạy <code className="font-mono">python src/export_dashboard.py</code> khi có mạng.</p>
      </Card>
    );
  const spark = [...f.recent.map((p) => ({ d: p.d, pm: p.pm })), { d: f.target, fc: f.pm }];
  spark[spark.length - 2].fc = spark[spark.length - 2].pm;
  const weather = [
    [Thermometer, "Nhiệt độ", `${fmt(f.today.temp)}°C`],
    [Droplets, "Độ ẩm", `${fmt(f.today.humidity, 0)}%`],
    [Wind, "Gió", `${fmt(f.today.wind_speed)} km/h`],
    [CloudRain, "Mưa", `${fmt(f.today.precipitation)} mm`],
  ];
  return (
    <Card className="relative overflow-hidden lg:col-span-4">
      <div className="pointer-events-none absolute -right-16 -top-16 size-48 rounded-full opacity-25 blur-3xl" style={{ background: f.color }} />
      <CardHeader icon={CalendarClock} title="Dự báo ngày mai" subtitle={`${fmtDate(f.target, { weekday: "long", day: "2-digit", month: "2-digit" })}`}
        right={<Pill color={f.color}>{f.level}</Pill>} />
      <div className="relative flex items-center justify-between">
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-5xl font-semibold tracking-tight tabular-nums">{fmt(f.pm, 0)}</span>
            <span className="text-sm text-zinc-500 dark:text-zinc-400">µg/m³</span>
          </div>
          <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Hôm nay {fmt(f.today.pm2_5)} ·{" "}
            <span className={f.pm > f.today.pm2_5 ? "text-rose-500" : "text-emerald-500"}>
              {f.pm > f.today.pm2_5 ? "▲" : "▼"} {fmt(Math.abs(f.pm - f.today.pm2_5))}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-center">
          <ProbRing value={f.prob} color={f.color} />
          <span className="mt-1 text-[11px] text-zinc-500">P(vượt QCVN)</span>
        </div>
      </div>
      <div className="relative -mx-1 mt-3 h-20">
        <ResponsiveContainer>
          <LineChart data={spark} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
            <ReferenceLine y={LIMIT} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
            <Tooltip content={<ChartTooltip labelFormat={(l) => fmtDate(l)} />} />
            <Line dataKey="pm" name="PM2.5" stroke={t.primary} strokeWidth={2} dot={false} />
            <Line dataKey="fc" name="Dự báo" stroke={f.color} strokeWidth={2} strokeDasharray="4 3"
              dot={(p) => p.index === spark.length - 1 ? <circle key="end" cx={p.cx} cy={p.cy} r={4} fill={f.color} /> : <g key={p.index} />} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="relative mt-2 rounded-lg border border-zinc-200 bg-zinc-50 p-2.5 text-xs leading-relaxed text-zinc-600 dark:border-zinc-800 dark:bg-zinc-800/40 dark:text-zinc-300">
        {f.advice}
      </p>
      <div className="relative mt-3 grid grid-cols-4 gap-2">
        {weather.map(([I, l, v]) => (
          <div key={l} className="text-center">
            <I size={14} className="mx-auto mb-1 text-zinc-400" />
            <div className="text-xs font-medium tabular-nums">{v}</div>
            <div className="text-[10px] text-zinc-500">{l}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function MonthlyCard({ t }) {
  return (
    <Card className="lg:col-span-5">
      <CardHeader icon={BarChart3} title="Theo tháng" subtitle="PM2.5 trung bình, tô màu theo mức VN_AQI" />
      <div className="h-56">
        <ResponsiveContainer>
          <BarChart data={D.monthly} margin={{ top: 8, right: 4, left: -22, bottom: 0 }}>
            <CartesianGrid stroke={t.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="m" tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: t.grid, opacity: 0.4 }} />
            <ReferenceLine y={LIMIT} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.6} />
            <Bar dataKey="pm" name="PM2.5" radius={[6, 6, 0, 0]} animationDuration={600}>
              {D.monthly.map((m) => <Cell key={m.m} fill={levelOf(m.pm).color} fillOpacity={0.85} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function HourlyCard({ t }) {
  return (
    <Card className="lg:col-span-4">
      <CardHeader icon={Activity} title="Chu kỳ trong ngày" subtitle="Thấp nhất buổi trưa, đỉnh 19–22h" />
      <div className="h-56">
        <ResponsiveContainer>
          <LineChart data={D.hourly} margin={{ top: 8, right: 4, left: -22, bottom: 0 }}>
            <CartesianGrid stroke={t.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="h" tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} interval={3} />
            <YAxis tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} domain={["dataMin - 3", "dataMax + 3"]} tickFormatter={(v) => Math.round(v)} />
            <Tooltip content={<ChartTooltip />} />
            <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11, color: t.text }} />
            <Line type="monotone" dataKey="dry" name="Mùa khô (T11–T2)" stroke={t.secondary} strokeWidth={2.2} dot={false} />
            <Line type="monotone" dataKey="other" name="Tháng khác" stroke={t.primary} strokeWidth={2.2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function SeasonCard() {
  const icons = { "Xuân": "🌸", "Hè": "☀️", "Thu": "🍂", "Đông": "❄️" };
  return (
    <Card className="lg:col-span-3">
      <CardHeader icon={Layers} title="Theo mùa" subtitle="Tỉ lệ ngày vượt QCVN" />
      <div className="space-y-4">
        {D.seasons.map((s) => (
          <div key={s.s}>
            <div className="mb-1.5 flex justify-between text-xs">
              <span className="font-medium">{icons[s.s]} {s.s}</span>
              <span className="font-mono tabular-nums text-zinc-500">{fmt(s.exceed)}% · {fmt(s.pm)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
              <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-rose-500 transition-all duration-700" style={{ width: `${s.exceed * 2}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function CorrelationCard({ t }) {
  return (
    <Card className="lg:col-span-4">
      <CardHeader icon={ScanSearch} title="Tương quan với PM2.5" subtitle="Spearman · xanh: làm giảm bụi, đỏ: đi cùng bụi" />
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart data={D.correlation} layout="vertical" margin={{ top: 0, right: 12, left: 6, bottom: 0 }}>
            <CartesianGrid stroke={t.grid} strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" domain={[-1, 1]} tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="k" width={80} tick={{ fill: t.text, fontSize: 11 }} tickLine={false} axisLine={false} />
            <ReferenceLine x={0} stroke={t.axis} />
            <Tooltip content={<ChartTooltip unit="" />} cursor={{ fill: t.grid, opacity: 0.4 }} />
            <Bar dataKey="v" name="ρ" radius={4} barSize={12}>
              {D.correlation.map((c) => <Cell key={c.k} fill={c.v < 0 ? "#3b82f6" : "#f43f5e"} fillOpacity={0.35 + Math.abs(c.v) * 0.65} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function ModelCard() {
  const [tab, setTab] = useState("reg");
  const rows = tab === "reg" ? D.regression : D.classification;
  const cols = tab === "reg" ? ["MAE", "RMSE", "R2"] : ["Accuracy", "F1", "Recall", "ROC-AUC"];
  const best = tab === "reg" ? D.bestReg : D.bestClf;
  const maxMae = Math.max(...D.regression.map((r) => r.MAE));
  return (
    <Card className="lg:col-span-4">
      <CardHeader icon={Brain} title="So sánh mô hình" subtitle={`Test: ${D.nTest} ngày từ ${fmtDate(D.split)}`}
        right={<Segmented value={tab} onChange={setTab} options={[{ value: "reg", label: "Hồi quy" }, { value: "clf", label: "Phân loại" }]} />} />
      <div className="overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-xs">
          <thead className="bg-zinc-50 text-zinc-500 dark:bg-zinc-800/50 dark:text-zinc-400">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Mô hình</th>
              {cols.map((c) => <th key={c} className="px-2 py-2 text-right font-medium">{c}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {rows.map((r) => {
              const name = r["Mô hình"].replace("Baseline (ngày mai = hôm nay)", "Baseline");
              const isBest = r["Mô hình"] === best;
              return (
                <tr key={name} className={`transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/40 ${isBest ? "bg-indigo-50/60 dark:bg-indigo-500/10" : ""}`}>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-1.5 font-medium">
                      {isBest && <CheckCircle2 size={12} className="text-indigo-500" />}{name}
                    </div>
                    {tab === "reg" && (
                      <div className="mt-1 h-1 w-full rounded-full bg-zinc-100 dark:bg-zinc-800">
                        <div className="h-full rounded-full bg-indigo-500/70" style={{ width: `${(r.MAE / maxMae) * 100}%` }} />
                      </div>
                    )}
                  </td>
                  {cols.map((c) => <td key={c} className="px-2 py-2.5 text-right font-mono tabular-nums">{r[c] == null ? "–" : fmt(r[c], c === "RMSE" || c === "MAE" ? 2 : 3)}</td>)}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
        {tab === "reg"
          ? <>Mô hình tốt nhất giảm sai số <b className="text-zinc-800 dark:text-zinc-200">{fmt(D.kpi.maeGain, 0)}%</b> so với cách đoán “ngày mai = hôm nay”.</>
          : <>Ưu tiên <b className="text-zinc-800 dark:text-zinc-200">Recall</b>: bỏ sót một ngày ô nhiễm nguy hiểm hơn báo nhầm.</>}
      </p>
    </Card>
  );
}

function ImportanceCard({ t }) {
  return (
    <Card className="lg:col-span-4">
      <CardHeader icon={Gauge} title="Đặc trưng quan trọng" subtitle={`Permutation importance · ${D.bestReg}`} />
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart data={D.importance} layout="vertical" margin={{ top: 0, right: 12, left: 6, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="k" width={150} tick={{ fill: t.text, fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip content={<ChartTooltip unit=" MAE" />} cursor={{ fill: t.grid, opacity: 0.4 }} />
            <Bar dataKey="v" name="Mức tăng" radius={4} barSize={12} fill={t.primary}
              label={{ position: "right", fill: t.axis, fontSize: 10, formatter: (v) => fmt(v, 2) }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function BacktestCard({ t }) {
  return (
    <Card className="lg:col-span-8">
      <CardHeader icon={Database} title="Dự báo vs thực tế (tập kiểm tra)"
        subtitle="Kéo thanh bên dưới biểu đồ để phóng to một giai đoạn" right={<Pill color={ACCENT}>R² = {fmt(D.kpi.r2, 2)}</Pill>} />
      <div className="h-80">
        <ResponsiveContainer>
          <ComposedChart data={D.test} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke={t.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="d" tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={50}
              tickFormatter={dm} />
            <YAxis tick={{ fill: t.axis, fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip content={<ChartTooltip labelFormat={(l) => fmtDate(l)} />} />
            <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11, color: t.text }} />
            <ReferenceLine y={LIMIT} stroke="#ef4444" strokeDasharray="5 4" strokeOpacity={0.6} />
            <Line type="monotone" dataKey="actual" name="Thực tế" stroke={t.muted === "#52525b" ? "#e4e4e7" : "#27272a"} strokeWidth={1.4} dot={false} />
            <Line type="monotone" dataKey="pred" name="Dự báo" stroke={t.secondary} strokeWidth={1.8} dot={false} />
            <Brush dataKey="d" height={22} stroke={t.axis} fill={t.grid} travellerWidth={8}
              tickFormatter={my} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function ThresholdCard() {
  const [thr, setThr] = useState(0.5);
  const m = useMemo(() => {
    let tp = 0, fp = 0, fn = 0, tn = 0;
    for (const r of D.test) {
      const p = r.prob >= thr ? 1 : 0;
      if (p && r.y) tp++; else if (p) fp++; else if (r.y) fn++; else tn++;
    }
    const prec = tp / Math.max(tp + fp, 1), rec = tp / Math.max(tp + fn, 1);
    return { tp, fp, fn, tn, acc: (tp + tn) / D.test.length, prec, rec, f1: (2 * prec * rec) / Math.max(prec + rec, 1e-9) };
  }, [thr]);
  const cells = [
    ["Đúng: đạt chuẩn", m.tn, "emerald"], ["Báo nhầm", m.fp, "amber"],
    ["Bỏ sót", m.fn, "rose"], ["Bắt đúng ô nhiễm", m.tp, "indigo"],
  ];
  const tone = { emerald: "text-emerald-600 dark:text-emerald-400", amber: "text-amber-600 dark:text-amber-400", rose: "text-rose-600 dark:text-rose-400", indigo: "text-indigo-600 dark:text-indigo-400" };
  return (
    <Card className="lg:col-span-4">
      <CardHeader icon={Wand2} title="Ngưỡng cảnh báo" subtitle={`${D.bestClf} · kéo để xem đánh đổi`} />
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-zinc-500">Cảnh báo khi P ≥</span>
        <span className="font-mono font-semibold">{thr.toFixed(2)}</span>
      </div>
      <input type="range" min="0.05" max="0.95" step="0.05" value={thr} onChange={(e) => setThr(+e.target.value)} className="w-full" />
      <div className="mt-4 grid grid-cols-2 gap-2">
        {cells.map(([l, v, c]) => (
          <div key={l} className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <div className={`font-mono text-2xl font-semibold tabular-nums ${tone[c]}`}>{v}</div>
            <div className="text-[11px] text-zinc-500">{l}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-4 gap-1 text-center">
        {[["Acc", m.acc], ["Prec", m.prec], ["Recall", m.rec], ["F1", m.f1]].map(([l, v]) => (
          <div key={l}>
            <div className="font-mono text-sm font-semibold tabular-nums">{v.toFixed(2)}</div>
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">{l}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Pipeline() {
  const steps = [
    [CloudDownload, "Thu thập", "Open-Meteo API · 15 biến · 37k bản ghi"],
    [Database, "Tiền xử lý", "Nội suy thiếu · IQR · gộp ngày"],
    [ScanSearch, "Khám phá", "Mùa vụ · chu kỳ ngày · tương quan"],
    [Brain, "Mô hình hoá", "Ridge · RF · Gradient Boosting"],
    [Rocket, "Triển khai", "Dashboard · dự báo thời gian thực"],
  ];
  return (
    <Card className="lg:col-span-12">
      <CardHeader icon={Sparkles} title="Quy trình Khoa học dữ liệu" subtitle="5 bước từ dữ liệu thô đến sản phẩm" />
      <ol className="relative grid gap-6 md:grid-cols-5 md:gap-4">
        <div className="absolute left-5 right-5 top-5 hidden h-px bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 md:block" />
        {steps.map(([Icon, title, desc], i) => (
          <li key={title} className="group relative flex gap-3 md:flex-col md:gap-0">
            <div className="relative z-10 grid size-10 shrink-0 place-items-center rounded-full border border-zinc-200 bg-white text-indigo-600 shadow-sm transition-all duration-300 group-hover:scale-110 group-hover:border-indigo-400 group-hover:shadow-indigo-500/20 group-hover:shadow-lg dark:border-zinc-700 dark:bg-zinc-900 dark:text-indigo-400">
              <Icon size={17} />
              <span className="absolute -right-1 -top-1 grid size-4 place-items-center rounded-full bg-indigo-600 text-[9px] font-bold text-white">{i + 1}</span>
            </div>
            <div className="md:mt-3">
              <div className="text-sm font-semibold">{title}</div>
              <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{desc}</div>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

/* ---------------------------------------------------------------- app */
export default function App() {
  const [dark, setDark] = useTheme();
  const t = chartTheme(dark);
  const k = D.kpi;
  return (
    <div className="grid-bg min-h-screen">
      <Header dark={dark} setDark={setDark} />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
        <Hero />
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard icon={Wind} tone="indigo" label="PM2.5 trung bình" value={fmt(k.mean)} unit="µg/m³" delta={`${fmt(k.who)}×`} deltaGood={false} hint="ngưỡng WHO (15)" />
          <KpiCard icon={AlertTriangle} tone="orange" label="Ngày vượt QCVN" value={fmt(k.exceed, 0)} unit="%" hint={`trên ${k.days.toLocaleString("vi-VN")} ngày`} />
          <KpiCard icon={Activity} tone="rose" label="Ngày ô nhiễm nhất" value={dm(k.worstDate)} unit={new Date(k.worstDate).getFullYear()} delta={`${fmt(k.worstVal, 0)} µg/m³`} deltaGood={false} />
          <KpiCard icon={Brain} tone="emerald" label="Sai số dự báo (MAE)" value={fmt(k.mae)} unit="µg/m³" delta={`−${fmt(k.maeGain, 0)}%`} deltaGood hint="so với baseline" />
        </section>
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <TimeSeriesCard t={t} />
          <ForecastCard t={t} />
          <MonthlyCard t={t} />
          <HourlyCard t={t} />
          <SeasonCard />
          <CorrelationCard t={t} />
          <ModelCard />
          <ImportanceCard t={t} />
          <BacktestCard t={t} />
          <ThresholdCard />
          <Pipeline />
        </section>
        <footer className="flex flex-col items-center justify-between gap-2 border-t border-zinc-200 pt-6 text-xs text-zinc-500 sm:flex-row dark:border-zinc-800">
          <span>Nhóm 17 · Nhập môn Khoa học dữ liệu · ĐHBK Hà Nội</span>
          <span>Dữ liệu mô hình CAMS/ERA5 qua Open-Meteo · chỉ dùng cho mục đích học tập</span>
        </footer>
      </main>
    </div>
  );
}
