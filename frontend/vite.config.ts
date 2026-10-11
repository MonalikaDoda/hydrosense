import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, ".", "");
  const requiredProductionVariables = [
    "VITE_API_BASE_URL",
    "VITE_COGNITO_USER_POOL_ID",
    "VITE_COGNITO_USER_POOL_CLIENT_ID",
    "VITE_COGNITO_DOMAIN",
  ];
  const missingVariables = requiredProductionVariables.filter(
    (name) => !environment[name]?.trim(),
  );
  if (mode === "production" && missingVariables.length) {
    throw new Error(
      `Production build is missing: ${missingVariables.join(", ")}.`,
    );
  }

  return {
    plugins: [react()],
  };
});
