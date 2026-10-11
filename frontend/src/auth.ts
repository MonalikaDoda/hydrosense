import { Amplify } from "aws-amplify";
import {
  fetchAuthSession,
  getCurrentUser,
  signInWithRedirect,
  signOut,
} from "aws-amplify/auth";
import { cognitoUserPoolsTokenProvider } from "aws-amplify/auth/cognito";
import { sessionStorage } from "aws-amplify/utils";

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const userPoolClientId = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID;
const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN;

export const authConfigured = Boolean(
  userPoolId && userPoolClientId && cognitoDomain,
);

if (authConfigured) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: {
          oauth: {
            domain: cognitoDomain,
            scopes: ["openid", "email"],
            redirectSignIn: [window.location.origin],
            redirectSignOut: [window.location.origin],
            responseType: "code",
          },
        },
      },
    },
  });
  cognitoUserPoolsTokenProvider.setKeyValueStorage(sessionStorage);
}

export async function getAccessToken(): Promise<string | null> {
  if (!authConfigured) return null;
  const session = await fetchAuthSession();
  return session.tokens?.accessToken.toString() ?? null;
}

export async function isSignedIn(): Promise<boolean> {
  if (!authConfigured) return true;
  try {
    await getCurrentUser();
    return true;
  } catch {
    return false;
  }
}

export async function beginSignIn(): Promise<void> {
  if (!authConfigured) return;
  await signInWithRedirect();
}

export async function endSession(): Promise<void> {
  if (!authConfigured) return;
  await signOut();
}