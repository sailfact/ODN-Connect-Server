import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Users, Shield, ClipboardList, LogOut } from "lucide-react";
import { useAuthStore } from "../../store/auth";
import { logout as apiLogout } from "../../api/auth";
import clsx from "clsx";

const nav = [
  { to: "/admin", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/admin/peers", icon: Shield, label: "Peers" },
  { to: "/admin/users", icon: Users, label: "Users" },
  { to: "/admin/audit", icon: ClipboardList, label: "Audit Log" },
];

export default function AdminLayout() {
  const { refreshToken, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    if (refreshToken) await apiLogout(refreshToken).catch(() => {});
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-56 bg-gray-900 text-white flex flex-col">
        <div className="px-6 py-5 border-b border-gray-700">
          <span className="font-bold text-lg">ODN Admin</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-3">
          {nav.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition",
                  isActive ? "bg-brand-600 text-white" : "text-gray-300 hover:bg-gray-700"
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-6 py-4 text-gray-400 hover:text-white text-sm border-t border-gray-700"
        >
          <LogOut size={16} /> Sign out
        </button>
      </aside>
      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
