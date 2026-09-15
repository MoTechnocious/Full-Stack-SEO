"use client";

/**
 * Auth context: owns the bearer token (persisted to localStorage), the
 * current user/org/role/plan, and the two async flows that mint a new token
 * (login/signup, switch-org). Also subscribes to `@/lib/api`'s global
 * 401/402/403 event bus so a session expiry, quota hit, or permission denial
 * anywhere in the app surfaces consistently:
 *
 *  - 401  -> clear the session and redirect to /login
 *  - 402  -> populate `upgradeNotice` (an "upgrade your plan" banner)
 *  - 403  -> populate `forbiddenNotice` ("insufficient role" banner)
 *
 * localStorage is fine here (per product spec) — this is a dashboard, not a
 * page handling third-party un-trusted content, and the token is short-lived
 * server-side anyway.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  getMe,
  login as apiLogin,
  setApiAuthEventListener,
  setAuthToken as setApiAuthToken,
  signup as apiSignup,
  switchOrg as apiSwitchOrg,
  type AuthResponse,
  type Role,
} from "@/lib/api";

const TOKEN_STORAGE_KEY = "myseoapp.auth.token";

interface AuthContextValue {
  /** True until the initial localStorage hydration + /auth/me check completes. */
  isLoading: boolean;
  isAuthenticated: boolean;
  token: string | null;
  userId: string | null;
  email: string | null;
  orgId: string | null;
  orgName: string | null;
  role: Role | null;
  planCode: string | null;
  /** owner or agency_admin — can invite/manage members and API keys. */
  canManageTeam: boolean;
  /** owner only — the backend only grants `billing:manage` to owner. */
  canManageBilling: boolean;
  upgradeNotice: string | null;
  forbiddenNotice: string | null;
  dismissUpgradeNotice: () => void;
  dismissForbiddenNotice: () => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName?: string, orgName?: string) => Promise<void>;
  logout: () => void;
  switchOrg: (orgId: string) => Promise<void>;
  /** Re-fetch /auth/me (e.g. after a billing checkout changes the plan). */
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function normalizeRole(value: string | null | undefined): Role | null {
  if (value === "owner" || value === "agency_admin" || value === "editor" || value === "client") return value;
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [orgName, setOrgName] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [planCode, setPlanCode] = useState<string | null>(null);
  const [upgradeNotice, setUpgradeNotice] = useState<string | null>(null);
  const [forbiddenNotice, setForbiddenNotice] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    setApiAuthToken(null);
    if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUserId(null);
    setEmail(null);
    setOrgId(null);
    setOrgName(null);
    setRole(null);
    setPlanCode(null);
  }, []);

  const applyAuthResponse = useCallback((res: AuthResponse) => {
    setApiAuthToken(res.access_token);
    if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token);
    setToken(res.access_token);
    setUserId(res.user.id);
    setEmail(res.user.email);
    setOrgId(res.org.id);
    setOrgName(res.org.name);
    setRole(normalizeRole(res.org.role));
    setPlanCode(res.org.plan_code);
  }, []);

  // Hydrate from localStorage once on mount, validating the token via /auth/me.
  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      const stored = typeof window !== "undefined" ? window.localStorage.getItem(TOKEN_STORAGE_KEY) : null;
      if (!stored) {
        setIsLoading(false);
        return;
      }
      setApiAuthToken(stored);
      setToken(stored);
      try {
        const me = await getMe();
        if (cancelled) return;
        setUserId(me.user_id);
        setEmail(me.email);
        setOrgId(me.org_id);
        setOrgName(me.org_name);
        setRole(normalizeRole(me.role));
        setPlanCode(me.plan_code);
      } catch {
        // A 401 here is broadcast through the global listener below, which
        // already clears the session and redirects — nothing else to do.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  // Subscribe to the API client's global auth-failure bus.
  useEffect(() => {
    setApiAuthEventListener((event) => {
      if (event.status === 401) {
        clearSession();
        router.push("/login");
      } else if (event.status === 402) {
        setUpgradeNotice(event.error.message);
      } else if (event.status === 403) {
        setForbiddenNotice(event.error.message);
      }
    });
    return () => setApiAuthEventListener(null);
  }, [clearSession, router]);

  const login = useCallback(
    async (loginEmail: string, password: string) => {
      const res = await apiLogin({ email: loginEmail, password });
      applyAuthResponse(res);
    },
    [applyAuthResponse],
  );

  const signup = useCallback(
    async (signupEmail: string, password: string, fullName?: string, orgName?: string) => {
      const res = await apiSignup({
        email: signupEmail,
        password,
        full_name: fullName || undefined,
        org_name: orgName || undefined,
      });
      applyAuthResponse(res);
    },
    [applyAuthResponse],
  );

  const logout = useCallback(() => {
    clearSession();
    router.push("/login");
  }, [clearSession, router]);

  const switchOrg = useCallback(async (nextOrgId: string) => {
    const res = await apiSwitchOrg({ org_id: nextOrgId });
    setApiAuthToken(res.access_token);
    if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token);
    setToken(res.access_token);
    setOrgId(res.org.id);
    setOrgName(res.org.name);
    setRole(normalizeRole(res.org.role));
    setPlanCode(res.org.plan_code);
  }, []);

  const refreshMe = useCallback(async () => {
    const me = await getMe();
    setUserId(me.user_id);
    setEmail(me.email);
    setOrgId(me.org_id);
    setOrgName(me.org_name);
    setRole(normalizeRole(me.role));
    setPlanCode(me.plan_code);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isLoading,
      isAuthenticated: token !== null && userId !== null,
      token,
      userId,
      email,
      orgId,
      orgName,
      role,
      planCode,
      canManageTeam: role === "owner" || role === "agency_admin",
      canManageBilling: role === "owner",
      upgradeNotice,
      forbiddenNotice,
      dismissUpgradeNotice: () => setUpgradeNotice(null),
      dismissForbiddenNotice: () => setForbiddenNotice(null),
      login,
      signup,
      logout,
      switchOrg,
      refreshMe,
    }),
    [
      isLoading,
      token,
      userId,
      email,
      orgId,
      orgName,
      role,
      planCode,
      upgradeNotice,
      forbiddenNotice,
      login,
      signup,
      logout,
      switchOrg,
      refreshMe,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth() must be used inside an <AuthProvider>.");
  return ctx;
}

/** Re-exported so pages can catch auth errors without importing `@/lib/api` too. */
export { ApiError };
