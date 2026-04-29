/**
 * Auth utilities: sign-in, sign-out, and route guard hook.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth as authApi, setTokens, clearTokens, getAccessToken, TokenResponse } from "./api";

// ---------------------------------------------------------------------------
// Sign-in / sign-out helpers
// ---------------------------------------------------------------------------

export async function signIn(email: string, password: string): Promise<void> {
  const tokens: TokenResponse = await authApi.login(email, password);
  setTokens(tokens.access_token, tokens.refresh_token);
}

export async function signUp(
  email: string,
  password: string,
  full_name?: string
): Promise<void> {
  const tokens: TokenResponse = await authApi.signup(email, password, full_name);
  setTokens(tokens.access_token, tokens.refresh_token);
}

export async function signOut(): Promise<void> {
  try {
    await authApi.logout();
  } catch {
    // ignore server errors on logout
  } finally {
    clearTokens();
  }
}

// ---------------------------------------------------------------------------
// Route guard hook (client components)
// ---------------------------------------------------------------------------

/**
 * Redirects to /login when the user is not authenticated.
 * Returns `authenticated: true` once the check passes.
 */
export function useRequireAuth(): { authenticated: boolean } {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
    } else {
      setAuthenticated(true);
    }
  }, [router]);

  return { authenticated };
}
