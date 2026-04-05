import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Download, Trash2, Plus, QrCode } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { listMyPeers, createMyPeer, deleteMyPeer, getPeerConfigUrl, type Peer } from "../../api/peers";
import { api } from "../../api/client";
import { useAuthStore } from "../../store/auth";

export default function PortalPeers() {
  const qc = useQueryClient();
  const { accessToken } = useAuthStore();
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [qrConfig, setQrConfig] = useState<{ name: string; content: string } | null>(null);

  const { data: peers = [], isLoading } = useQuery({
    queryKey: ["my-peers"],
    queryFn: listMyPeers,
    refetchInterval: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: () => createMyPeer({ name: newName, client_label: "web-portal" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["my-peers"] }); setShowCreate(false); setNewName(""); toast.success("Peer created"); },
    onError: (err: any) => toast.error(err.response?.data?.detail ?? "Failed to create peer"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMyPeer,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["my-peers"] }); toast.success("Peer removed"); },
  });

  const downloadConfig = async (peer: Peer) => {
    const res = await api.get(getPeerConfigUrl(peer.id), { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${peer.name}.conf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const showQr = async (peer: Peer) => {
    const res = await api.get(getPeerConfigUrl(peer.id));
    setQrConfig({ name: peer.name, content: res.data });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Peers</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} /> Add Device
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl shadow-sm p-4 mb-4 flex gap-3">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Device name (e.g. My Laptop)"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={() => createMutation.mutate()}
            disabled={!newName || createMutation.isPending}
            className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            Add
          </button>
          <button onClick={() => setShowCreate(false)} className="text-gray-500 px-2">✕</button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="space-y-3">
          {peers.map((peer: Peer) => (
            <div key={peer.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between">
              <div>
                <p className="font-semibold">{peer.name}</p>
                <p className="text-xs text-gray-500 font-mono">{peer.assigned_ip}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {peer.last_handshake
                    ? `Last seen ${new Date(peer.last_handshake).toLocaleString()}`
                    : "Never connected"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${peer.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {peer.enabled ? "Active" : "Disabled"}
                </span>
                <button onClick={() => showQr(peer)} className="text-gray-400 hover:text-brand-600" title="Show QR">
                  <QrCode size={18} />
                </button>
                <button onClick={() => downloadConfig(peer)} className="text-gray-400 hover:text-brand-600" title="Download config">
                  <Download size={18} />
                </button>
                <button
                  onClick={() => { if (confirm("Remove this peer?")) deleteMutation.mutate(peer.id); }}
                  className="text-gray-400 hover:text-red-500"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {peers.length === 0 && (
            <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-400">
              No devices yet. Add one to get started.
            </div>
          )}
        </div>
      )}

      {/* QR Modal */}
      {qrConfig && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setQrConfig(null)}>
          <div className="bg-white rounded-xl p-6 text-center" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-semibold mb-4">{qrConfig.name}</h2>
            <QRCodeSVG value={qrConfig.content} size={256} />
            <p className="text-xs text-gray-400 mt-3">Scan with a WireGuard app</p>
            <button onClick={() => setQrConfig(null)} className="mt-4 text-sm text-brand-600 hover:underline">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
