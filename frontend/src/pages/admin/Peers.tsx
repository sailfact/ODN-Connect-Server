import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Trash2, ToggleLeft, ToggleRight, Plus } from "lucide-react";
import { listAllPeers, createPeer, deletePeer, updatePeer, type Peer } from "../../api/peers";

export default function AdminPeers() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");

  const { data: peers = [], isLoading } = useQuery({ queryKey: ["admin-peers"], queryFn: listAllPeers, refetchInterval: 30_000 });

  const createMutation = useMutation({
    mutationFn: () => createPeer({ name: newName }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-peers"] }); setShowCreate(false); setNewName(""); toast.success("Peer created"); },
    onError: () => toast.error("Failed to create peer"),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePeer,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-peers"] }); toast.success("Peer removed"); },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updatePeer(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-peers"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Peers</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={16} /> Add Peer
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl shadow-sm p-4 mb-4 flex gap-3">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Peer name"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={() => createMutation.mutate()}
            disabled={!newName || createMutation.isPending}
            className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            Create
          </button>
          <button onClick={() => setShowCreate(false)} className="text-gray-500 hover:text-gray-700 px-2">✕</button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Name</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Assigned IP</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Last Handshake</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {peers.map((peer: Peer) => (
                <tr key={peer.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{peer.name}</td>
                  <td className="px-4 py-3 font-mono text-xs">{peer.assigned_ip}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {peer.last_handshake ? new Date(peer.last_handshake).toLocaleString() : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${peer.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {peer.enabled ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3 flex items-center justify-end gap-2">
                    <button
                      onClick={() => toggleMutation.mutate({ id: peer.id, enabled: !peer.enabled })}
                      className="text-gray-400 hover:text-brand-600"
                      title={peer.enabled ? "Disable" : "Enable"}
                    >
                      {peer.enabled ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                    </button>
                    <button
                      onClick={() => { if (confirm("Delete this peer?")) deleteMutation.mutate(peer.id); }}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {peers.length === 0 && <p className="text-center text-gray-400 py-8">No peers yet</p>}
        </div>
      )}
    </div>
  );
}
