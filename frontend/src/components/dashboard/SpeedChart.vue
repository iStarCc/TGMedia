<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useStatsStore } from "@/stores/stats";

const statsStore = useStatsStore();
const canvasRef = ref<HTMLCanvasElement | null>(null);

const MAX_POINTS = 60;
const dataPoints = ref<number[]>(new Array(MAX_POINTS).fill(0));
let animFrame = 0;
let lastPush = 0;

function pushSpeed() {
  const now = Date.now();
  if (now - lastPush < 1000) return;
  lastPush = now;

  dataPoints.value.push(statsStore.stats.current_speed);
  if (dataPoints.value.length > MAX_POINTS) {
    dataPoints.value.shift();
  }
}

function draw() {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const points = dataPoints.value;
  const maxVal = Math.max(...points, 1);
  const padding = { top: 8, bottom: 24, left: 0, right: 0 };
  const chartW = w - padding.left - padding.right;
  const chartH = h - padding.top - padding.bottom;

  ctx.clearRect(0, 0, w, h);

  // grid lines
  const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
  const textColor = isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)";

  ctx.strokeStyle = gridColor;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const y = padding.top + (chartH / 3) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(w - padding.right, y);
    ctx.stroke();
  }

  // y-axis labels
  ctx.fillStyle = textColor;
  ctx.font = "10px var(--font-mono, monospace)";
  ctx.textAlign = "left";
  for (let i = 0; i <= 3; i++) {
    const val = maxVal * (1 - i / 3);
    const y = padding.top + (chartH / 3) * i;
    ctx.fillText(formatSpeed(val), padding.left + 4, y - 2);
  }

  if (points.length < 2) return;

  // area gradient
  const gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
  gradient.addColorStop(0, "rgba(16, 185, 129, 0.15)");
  gradient.addColorStop(1, "rgba(16, 185, 129, 0)");

  const stepX = chartW / (MAX_POINTS - 1);

  ctx.beginPath();
  ctx.moveTo(padding.left, h - padding.bottom);
  for (let i = 0; i < points.length; i++) {
    const x = padding.left + i * stepX;
    const y = padding.top + chartH * (1 - points[i] / maxVal);
    if (i === 0) ctx.lineTo(x, y);
    else {
      const prevX = padding.left + (i - 1) * stepX;
      const prevY = padding.top + chartH * (1 - points[i - 1] / maxVal);
      const cpx = (prevX + x) / 2;
      ctx.bezierCurveTo(cpx, prevY, cpx, y, x, y);
    }
  }
  ctx.lineTo(padding.left + (points.length - 1) * stepX, h - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // line
  ctx.beginPath();
  for (let i = 0; i < points.length; i++) {
    const x = padding.left + i * stepX;
    const y = padding.top + chartH * (1 - points[i] / maxVal);
    if (i === 0) ctx.moveTo(x, y);
    else {
      const prevX = padding.left + (i - 1) * stepX;
      const prevY = padding.top + chartH * (1 - points[i - 1] / maxVal);
      const cpx = (prevX + x) / 2;
      ctx.bezierCurveTo(cpx, prevY, cpx, y, x, y);
    }
  }
  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // current value dot
  if (points.length > 0) {
    const lastX = padding.left + (points.length - 1) * stepX;
    const lastY = padding.top + chartH * (1 - points[points.length - 1] / maxVal);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#10b981";
    ctx.fill();
  }
}

function formatSpeed(bytes: number): string {
  if (!bytes || bytes <= 0 || !isFinite(bytes)) return "0";
  const units = ["B/s", "KB/s", "MB/s", "GB/s"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  if (i < 0 || !isFinite(i)) return "0";
  return `${(bytes / 1024 ** i).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function tick() {
  pushSpeed();
  draw();
  animFrame = requestAnimationFrame(tick);
}

watch(() => statsStore.stats.current_speed, pushSpeed);

onMounted(() => {
  animFrame = requestAnimationFrame(tick);
});

onUnmounted(() => {
  cancelAnimationFrame(animFrame);
});
</script>

<template>
  <div class="rounded-xl border border-surface-border bg-surface-2 p-5">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-medium">实时下载速度</h3>
      <span class="text-xs font-mono text-primary">
        {{ statsStore.formattedSpeed }}
      </span>
    </div>
    <canvas
      ref="canvasRef"
      class="h-36 w-full"
    />
  </div>
</template>
