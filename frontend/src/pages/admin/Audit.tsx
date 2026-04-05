import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

interface AuditEntry {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  created_at: string;
}

export default function AdminAudit() {
  const { data: entries = [], isLoading } = useQuery<AuditEntry[]>({
    queryKey: ["audit"],
    queryFn: () => api.get("/admin/audit?limit=100").then((r) => r.data),
    refetchInterval: 60_000,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Audit Log</h1>
      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Time</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Action</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Target</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">IP</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{new Date(e.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 font-mono text-xs">{e.action}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{e.target_type ? `${e.target_type}:${e.target_id}` : "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{e.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {entries.length === 0 && <p className="text-center text-gray-400 py-8">No audit entries</p>}
        </div>
      )}
    </div>
  );
}
