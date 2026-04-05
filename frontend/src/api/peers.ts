import { api } from "./client";

export interface Peer {
  id: string;
  user_id: string;
  name: string;
  public_key: string;
  allowed_ips: string;
  assigned_ip: string;
  dns: string | null;
  enabled: boolean;
  last_handshake: string | null;
  client_label: string | null;
  created_at: string;
}

export interface PeerCreate {
  name: string;
  public_key?: string;
  allowed_ips?: string;
  dns?: string;
  client_label?: string;
}

// Admin
export const listAllPeers = () => api.get<Peer[]>("/peers").then((r) => r.data);
export const createPeer = (data: PeerCreate) => api.post<Peer>("/peers", data).then((r) => r.data);
export const deletePeer = (id: string) => api.delete(`/peers/${id}`);
export const updatePeer = (id: string, data: Partial<{ enabled: boolean; name: string; allowed_ips: string }>) =>
  api.patch<Peer>(`/peers/${id}`, data).then((r) => r.data);

// User
export const listMyPeers = () => api.get<Peer[]>("/me/peers").then((r) => r.data);
export const createMyPeer = (data: PeerCreate) => api.post<Peer>("/me/peers", data).then((r) => r.data);
export const deleteMyPeer = (id: string) => api.delete(`/me/peers/${id}`);
export const getPeerConfigUrl = (id: string) => `/api/me/peers/${id}/config`;
