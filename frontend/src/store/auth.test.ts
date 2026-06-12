import { describe, expect, it } from "vitest";
import { useAuthStore } from "./auth";

const b64url = (obj: object) =>
  btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const makeToken = (payload: object) =>
  `${b64url({ alg: "HS256", typ: "JWT" })}.${b64url(payload)}.sig`;

describe("auth store", () => {
  it("decodes role and userId from the access token", () => {
    const token = makeToken({ sub: "user-123", role: "admin", exp: 9999999999 });
    useAuthStore.getState().setTokens(token, "refresh-token");

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe(token);
    expect(state.refreshToken).toBe("refresh-token");
    expect(state.role).toBe("admin");
    expect(state.userId).toBe("user-123");
  });

  it("clears all auth state on logout", () => {
    useAuthStore.getState().setTokens(makeToken({ sub: "u", role: "user" }), "r");
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.role).toBeNull();
    expect(state.userId).toBeNull();
  });

  it("stores tokens but no role when the access token is malformed", () => {
    useAuthStore.getState().setTokens("not-a-jwt", "r");

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("not-a-jwt");
    expect(state.role).toBeNull();
    expect(state.userId).toBeNull();
  });
});
