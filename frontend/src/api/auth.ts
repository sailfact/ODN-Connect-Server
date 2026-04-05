import axios from "axios";

export interface LoginPayload {
  email: string;
  password: string;
  totp_code?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export const login = (data: LoginPayload) =>
  axios.post<TokenResponse>("/api/auth/login", data).then((r) => r.data);

export const logout = (refresh_token: string) =>
  axios.post("/api/auth/logout", { refresh_token });
