import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, ".", "");
  const requiredProductionVariables = ["VITE_API_BASE_URL"];
  const cognitoVariables = [
    "VITE_COGNITO_USER_POOL_ID",
    "VITE_COGNITO_USER_POOL_CLIENT_ID",
    "VITE_COGNITO_DOMAIN",
  ];
  const missingVariables = requiredProductionVariables.filter(
    (name) => !environment[name]?.trim(),
  );
  const missingCognitoVariables = cognitoVariables.filter(
    (name) => !environment[name]?.trim(),
  );
  if (mode === "production" && missingVariables.length) {
    throw new Error(
      `Production build is missing: ${missingVariables.join(", ")}.`,
    );
  }
  if (
    mode === "production" &&
    missingCognitoVariables.length &&
    missingCognitoVariables.length < cognitoVariables.length
  ) {
    throw new Error(
      `Cognito configuration is partially set; provide all of ${cognitoVariables.join(", ")} or none of them.`,
    );
  }

  return {
    plugins: [react()],
  };
});
