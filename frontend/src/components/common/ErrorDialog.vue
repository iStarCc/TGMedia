<script setup lang="ts">
import { onMounted, onUnmounted, watch } from "vue";
import MIcon from "@/components/common/MIcon.vue";
import { useErrorDialogStore } from "@/stores/errorDialog";

const store = useErrorDialogStore();

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && store.visible) store.close();
}

watch(
  () => store.visible,
  (open) => {
    document.body.style.overflow = open ? "hidden" : "";
  },
);

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="store.visible"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/45 backdrop-blur-[2px] p-4"
        @click.self="store.close"
      >
        <Transition
          appear
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95 translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 translate-y-1"
        >
          <div
            v-if="store.visible"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="error-dialog-title"
            aria-describedby="error-dialog-message"
            class="w-full max-w-sm rounded-2xl border border-surface-border bg-surface-2 p-6 shadow-2xl"
          >
            <div class="flex flex-col items-center text-center">
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-danger/10 text-danger">
                <MIcon name="error_outline" :size="24" />
              </div>
              <h2 id="error-dialog-title" class="mt-4 text-base font-semibold text-text-primary">
                {{ store.title }}
              </h2>
              <p id="error-dialog-message" class="mt-2 text-sm leading-relaxed text-text-secondary">
                {{ store.message }}
              </p>
            </div>
            <button
              class="mt-6 w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white cursor-pointer transition-colors hover:bg-primary-hover"
              @click="store.close"
            >
              知道了
            </button>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
