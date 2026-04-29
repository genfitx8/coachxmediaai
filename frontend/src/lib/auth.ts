/**
 * Auth utilities: sign-in, sign-out, and route guard hook.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth as authApi, setTokens, clearTokens, getAccessToken, getRefreshToken, TokenResponse } from "./api";

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
// JWT expiry helper (client-side only — no signature verification)
// ---------------------------------------------------------------------------

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (typeof payload.exp !== "number") return false;
    // Consider token expired 30 seconds before actual expiry
    return Date.now() / 1000 > payload.exp - 30;
  } catch {
    return true;
  }
}

// ---------------------------------------------------------------------------
// Route guard hook (client components)
// ---------------------------------------------------------------------------

/**
 * Redirects to /login when the user is not authenticated.
 * Performs a lightweight client-side JWT expiry check; if the access token
 * is expired it attempts a refresh before deciding.
 * Returns `authenticated: true` once the check passes.
 */
export function useRequireAuth(): { authenticated: boolean } {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    async function check() {
      const token = getAccessToken();
      if (!token) {
        router.replace("/login");
        return;
      }

      if (!isTokenExpired(token)) {
        setAuthenticated(true);
        return;
      }

      // Access token is expired — try to refresh
      const rt = getRefreshToken();
      if (!rt) {
        clearTokens();
        router.replace("/login");
        return;
      }

      try {
        const tokens = await authApi.refresh(rt);
        setTokens(tokens.access_token, tokens.refresh_token);
        setAuthenticated(true);
      } catch {
        clearTokens();
        router.replace("/login");
      }
    }

    check();
  }, [router]);

  return { authenticated };
}
