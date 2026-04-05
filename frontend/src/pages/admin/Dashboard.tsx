import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { Shield, Users, Activity } from "lucide-react";

interface StatusData {
  total_peers: number;
  enabled_peers: number;
  interface: string;
  peer_handshakes: Record<string, string>;
}

export default function AdminDashboard() {
  const { data, isLoading } = useQuery<StatusData>({
    queryKey: ["status"],
    queryFn: () => api.get("/status").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const statCards = [
    { label: "Total Peers", value: data?.total_peers ?? "—", icon: Shield, color: "bg-brand-500" },
    { label: "Active Peers", value: data?.enabled_peers ?? "—", icon: Activity, color: "bg-green-500" },
    {
      label: "Connected Now",
      value: data ? Object.keys(data.peer_handshakes).length : "—",
      icon: Users,
      color: "bg-purple-500",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      {isLoading ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-6 mb-8">
            {statCards.map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-white rounded-xl shadow-sm p-6 flex items-center gap-4">
                <div className={`${color} p-3 rounded-lg text-white`}>
                  <Icon size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">{label}</p>
                  <p className="text-3xl font-bold">{value}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Peer Handshakes</h2>
            {Object.keys(data?.peer_handshakes ?? {}).length === 0 ? (
              <p className="text-gray-400 text-sm">No recent handshakes</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2">Public Key</th>
                    <th className="pb-2">Last Handshake</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data?.peer_handshakes ?? {}).map(([key, ts]) => (
                    <tr key={key} className="border-b last:border-0">
                      <td className="py-2 font-mono text-xs truncate max-w-xs">{key}</td>
                      <td className="py-2 text-gray-600">{new Date(ts).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
