import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import LoginPage from "./pages/LoginPage";
import AdminLayout from "./components/layout/AdminLayout";
import PortalLayout from "./components/layout/PortalLayout";
import AdminDashboard from "./pages/admin/Dashboard";
import AdminPeers from "./pages/admin/Peers";
import AdminUsers from "./pages/admin/Users";
import AdminAudit from "./pages/admin/Audit";
import PortalPeers from "./pages/portal/Peers";
import PortalProfile from "./pages/portal/Profile";

function RequireAuth({ children, adminOnly = false }: { children: JSX.Element; adminOnly?: boolean }) {
  const { accessToken, role } = useAuthStore();
  if (!accessToken) return <Navigate to="/login" replace />;
  if (adminOnly && role !== "admin") return <Navigate to="/portal" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/admin"
        element={
          <RequireAuth adminOnly>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="peers" element={<AdminPeers />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="audit" element={<AdminAudit />} />
      </Route>

      <Route
        path="/portal"
        element={
          <RequireAuth>
            <PortalLayout />
          </RequireAuth>
        }
      >
        <Route index element={<PortalPeers />} />
        <Route path="profile" element={<PortalProfile />} />
      </Route>

      <Route path="/" element={<Navigate to="/portal" replace />} />
      <Route path="*" element={<Navigate to="/portal" replace />} />
    </Routes>
  );
}
