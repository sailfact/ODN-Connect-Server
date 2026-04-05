import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { Shield, User, LogOut } from "lucide-react";
import { useAuthStore } from "../../store/auth";
import { logout as apiLogout } from "../../api/auth";
import clsx from "clsx";

const nav = [
  { to: "/portal", icon: Shield, label: "My Peers", end: true },
  { to: "/portal/profile", icon: User, label: "Profile" },
];

export default function PortalLayout() {
  const { refreshToken, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    if (refreshToken) await apiLogout(refreshToken).catch(() => {});
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-56 bg-brand-700 text-white flex flex-col">
        <div className="px-6 py-5 border-b border-brand-600">
          <span className="font-bold text-lg">ODN Connect</span>
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
                  isActive ? "bg-white/20 text-white" : "text-white/70 hover:bg-white/10"
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
          className="flex items-center gap-2 px-6 py-4 text-white/60 hover:text-white text-sm border-t border-brand-600"
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
