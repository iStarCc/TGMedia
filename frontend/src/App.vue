<script setup lang="ts">
import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppHeader from "@/components/layout/AppHeader.vue";
import ErrorDialog from "@/components/common/ErrorDialog.vue";
</script>

<template>
  <div class="flex h-[100dvh] overflow-hidden">
    <AppSidebar />
    <div class="flex flex-1 flex-col overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-y-auto p-5">
        <RouterView />
      </main>
    </div>
  </div>
  <ErrorDialog />
</template>
