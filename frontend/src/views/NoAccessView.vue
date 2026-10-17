<script setup>
/**
 * Shown inside the normal shell (top bar with name and Sign out) when the user is signed in
 * but holds no permission at all (S011 § 1.4): a maintenance_team login with no role at any
 * site yet, or — while the database is down — anyone whose rights come from the database.
 */
import { dbUnavailable } from "../stores/auth";
</script>

<template>
  <div class="py-5 text-center">
    <template v-if="dbUnavailable">
      <i class="fa-solid fa-database fa-2x text-secondary mb-3"></i>
      <p class="text-secondary">The database is unavailable — try again shortly.</p>
    </template>
    <template v-else>
      <i class="fa-solid fa-user-lock fa-2x text-secondary mb-3"></i>
      <p class="text-secondary">You have no access yet — ask IT or your engineer to add you in Team.</p>
    </template>
  </div>
</template>
