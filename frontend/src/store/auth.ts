import { create } from "zustand";
import { persist } from "zustand/middleware";
import { decodeJwt } from "jose";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  role: "admin" | "user" | null;
  userId: string | null;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      role: null,
      userId: null,

      setTokens: (access, refresh) => {
        let role: "admin" | "user" | null = null;
        let userId: string | null = null;
        try {
          const payload = decodeJwt(access);
          role = payload.role as "admin" | "user";
          userId = payload.sub ?? null;
        } catch {
          // invalid token
        }
        set({ accessToken: access, refreshToken: refresh, role, userId });
      },

      logout: () => set({ accessToken: null, refreshToken: null, role: null, userId: null }),
    }),
    { name: "odn-auth" }
  )
);
