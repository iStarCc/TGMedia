<script setup lang="ts">
import { ref, computed } from "vue";

const model = defineModel<string>({ required: true });

interface Country {
  code: string;
  name: string;
  flag: string;
}

const countries: Country[] = [
  { code: "+86", name: "中国大陆", flag: "🇨🇳" },
  { code: "+852", name: "中国香港", flag: "🇨🇳" },
  { code: "+853", name: "中国澳门", flag: "🇨🇳" },
  { code: "+886", name: "中国台湾", flag: "🇨🇳" },
  { code: "+1", name: "美国/加拿大", flag: "🇺🇸" },
  { code: "+7", name: "俄罗斯", flag: "🇷🇺" },
  { code: "+20", name: "埃及", flag: "🇪🇬" },
  { code: "+27", name: "南非", flag: "🇿🇦" },
  { code: "+30", name: "希腊", flag: "🇬🇷" },
  { code: "+31", name: "荷兰", flag: "🇳🇱" },
  { code: "+32", name: "比利时", flag: "🇧🇪" },
  { code: "+33", name: "法国", flag: "🇫🇷" },
  { code: "+34", name: "西班牙", flag: "🇪🇸" },
  { code: "+36", name: "匈牙利", flag: "🇭🇺" },
  { code: "+39", name: "意大利", flag: "🇮🇹" },
  { code: "+40", name: "罗马尼亚", flag: "🇷🇴" },
  { code: "+41", name: "瑞士", flag: "🇨🇭" },
  { code: "+43", name: "奥地利", flag: "🇦🇹" },
  { code: "+44", name: "英国", flag: "🇬🇧" },
  { code: "+45", name: "丹麦", flag: "🇩🇰" },
  { code: "+46", name: "瑞典", flag: "🇸🇪" },
  { code: "+47", name: "挪威", flag: "🇳🇴" },
  { code: "+48", name: "波兰", flag: "🇵🇱" },
  { code: "+49", name: "德国", flag: "🇩🇪" },
  { code: "+51", name: "秘鲁", flag: "🇵🇪" },
  { code: "+52", name: "墨西哥", flag: "🇲🇽" },
  { code: "+53", name: "古巴", flag: "🇨🇺" },
  { code: "+54", name: "阿根廷", flag: "🇦🇷" },
  { code: "+55", name: "巴西", flag: "🇧🇷" },
  { code: "+56", name: "智利", flag: "🇨🇱" },
  { code: "+57", name: "哥伦比亚", flag: "🇨🇴" },
  { code: "+58", name: "委内瑞拉", flag: "🇻🇪" },
  { code: "+60", name: "马来西亚", flag: "🇲🇾" },
  { code: "+61", name: "澳大利亚", flag: "🇦🇺" },
  { code: "+62", name: "印度尼西亚", flag: "🇮🇩" },
  { code: "+63", name: "菲律宾", flag: "🇵🇭" },
  { code: "+64", name: "新西兰", flag: "🇳🇿" },
  { code: "+65", name: "新加坡", flag: "🇸🇬" },
  { code: "+66", name: "泰国", flag: "🇹🇭" },
  { code: "+81", name: "日本", flag: "🇯🇵" },
  { code: "+82", name: "韩国", flag: "🇰🇷" },
  { code: "+84", name: "越南", flag: "🇻🇳" },
  { code: "+90", name: "土耳其", flag: "🇹🇷" },
  { code: "+91", name: "印度", flag: "🇮🇳" },
  { code: "+92", name: "巴基斯坦", flag: "🇵🇰" },
  { code: "+93", name: "阿富汗", flag: "🇦🇫" },
  { code: "+94", name: "斯里兰卡", flag: "🇱🇰" },
  { code: "+95", name: "缅甸", flag: "🇲🇲" },
  { code: "+98", name: "伊朗", flag: "🇮🇷" },
  { code: "+212", name: "摩洛哥", flag: "🇲🇦" },
  { code: "+213", name: "阿尔及利亚", flag: "🇩🇿" },
  { code: "+216", name: "突尼斯", flag: "🇹🇳" },
  { code: "+218", name: "利比亚", flag: "🇱🇾" },
  { code: "+220", name: "冈比亚", flag: "🇬🇲" },
  { code: "+221", name: "塞内加尔", flag: "🇸🇳" },
  { code: "+233", name: "加纳", flag: "🇬🇭" },
  { code: "+234", name: "尼日利亚", flag: "🇳🇬" },
  { code: "+254", name: "肯尼亚", flag: "🇰🇪" },
  { code: "+255", name: "坦桑尼亚", flag: "🇹🇿" },
  { code: "+256", name: "乌干达", flag: "🇺🇬" },
  { code: "+260", name: "赞比亚", flag: "🇿🇲" },
  { code: "+351", name: "葡萄牙", flag: "🇵🇹" },
  { code: "+352", name: "卢森堡", flag: "🇱🇺" },
  { code: "+353", name: "爱尔兰", flag: "🇮🇪" },
  { code: "+354", name: "冰岛", flag: "🇮🇸" },
  { code: "+358", name: "芬兰", flag: "🇫🇮" },
  { code: "+370", name: "立陶宛", flag: "🇱🇹" },
  { code: "+371", name: "拉脱维亚", flag: "🇱🇻" },
  { code: "+372", name: "爱沙尼亚", flag: "🇪🇪" },
  { code: "+380", name: "乌克兰", flag: "🇺🇦" },
  { code: "+381", name: "塞尔维亚", flag: "🇷🇸" },
  { code: "+385", name: "克罗地亚", flag: "🇭🇷" },
  { code: "+420", name: "捷克", flag: "🇨🇿" },
  { code: "+421", name: "斯洛伐克", flag: "🇸🇰" },
  { code: "+855", name: "柬埔寨", flag: "🇰🇭" },
  { code: "+856", name: "老挝", flag: "🇱🇦" },
  { code: "+880", name: "孟加拉", flag: "🇧🇩" },
  { code: "+960", name: "马尔代夫", flag: "🇲🇻" },
  { code: "+961", name: "黎巴嫩", flag: "🇱🇧" },
  { code: "+962", name: "约旦", flag: "🇯🇴" },
  { code: "+964", name: "伊拉克", flag: "🇮🇶" },
  { code: "+965", name: "科威特", flag: "🇰🇼" },
  { code: "+966", name: "沙特阿拉伯", flag: "🇸🇦" },
  { code: "+968", name: "阿曼", flag: "🇴🇲" },
  { code: "+971", name: "阿联酋", flag: "🇦🇪" },
  { code: "+972", name: "以色列", flag: "🇮🇱" },
  { code: "+974", name: "卡塔尔", flag: "🇶🇦" },
  { code: "+977", name: "尼泊尔", flag: "🇳🇵" },
  { code: "+992", name: "塔吉克斯坦", flag: "🇹🇯" },
  { code: "+993", name: "土库曼斯坦", flag: "🇹🇲" },
  { code: "+994", name: "阿塞拜疆", flag: "🇦🇿" },
  { code: "+995", name: "格鲁吉亚", flag: "🇬🇪" },
  { code: "+996", name: "吉尔吉斯斯坦", flag: "🇰🇬" },
  { code: "+998", name: "乌兹别克斯坦", flag: "🇺🇿" },
];

const open = ref(false);
const search = ref("");
const containerRef = ref<HTMLDivElement>();

const current = computed(() => countries.find(c => c.code === model.value));

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim();
  if (!q) return countries;
  return countries.filter(c =>
    c.name.includes(q) || c.code.includes(q)
  );
});

function select(c: Country) {
  model.value = c.code;
  open.value = false;
  search.value = "";
}

function handleClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    open.value = false;
    search.value = "";
  }
}

function toggle() {
  open.value = !open.value;
  if (!open.value) search.value = "";
  else {
    document.addEventListener("click", handleClickOutside, { once: true });
  }
}
</script>

<template>
  <div ref="containerRef" class="relative">
    <button
      type="button"
      class="flex items-center gap-1 w-28 shrink-0 rounded-lg border border-surface-border bg-surface px-2 py-2 text-sm outline-none hover:bg-surface-2 cursor-pointer transition-colors"
      @click.stop="toggle"
    >
      <span v-if="current" class="text-base leading-none">{{ current.flag }}</span>
      <span class="truncate">{{ current?.code || model }}</span>
      <svg class="ml-auto h-3 w-3 text-text-muted shrink-0" viewBox="0 0 12 12" fill="none">
        <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div
      v-if="open"
      class="absolute left-0 top-full mt-1 z-50 w-56 rounded-lg border border-surface-border bg-surface-2 shadow-lg overflow-hidden"
    >
      <div class="p-1.5">
        <input
          v-model="search"
          type="text"
          placeholder="搜索国家/区号..."
          class="w-full rounded-md border border-surface-border bg-surface px-2.5 py-1.5 text-xs outline-none focus:border-primary"
          autofocus
        />
      </div>
      <div class="max-h-48 overflow-y-auto">
        <button
          v-for="c in filtered"
          :key="c.code"
          type="button"
          class="flex items-center gap-2 w-full px-3 py-1.5 text-sm hover:bg-surface cursor-pointer transition-colors"
          :class="{ 'bg-primary/5 text-primary': c.code === model }"
          @click="select(c)"
        >
          <span class="text-base leading-none">{{ c.flag }}</span>
          <span class="truncate">{{ c.name }}</span>
          <span class="ml-auto text-xs text-text-muted font-mono">{{ c.code }}</span>
        </button>
        <p v-if="filtered.length === 0" class="px-3 py-2 text-xs text-text-muted text-center">
          无匹配结果
        </p>
      </div>
    </div>
  </div>
</template>
