import { api } from "./client";

export interface UserOut {
  id: string;
  email: string;
  role: "admin" | "user";
  is_active: boolean;
  totp_enabled: boolean;
}

export interface UserCreate {
  email: string;
  password: string;
  role: "admin" | "user";
}

export const listUsers = () => api.get<UserOut[]>("/admin/users").then((r) => r.data);
export const createUser = (data: UserCreate) => api.post<UserOut>("/admin/users", data).then((r) => r.data);
export const deleteUser = (id: string) => api.delete(`/admin/users/${id}`);

export const setupTotp = () => api.post<{ secret: string; uri: string }>("/admin/me/totp/setup").then((r) => r.data);
export const confirmTotp = (secret: string, code: string) =>
  api.post("/admin/me/totp/confirm", { secret, code });
