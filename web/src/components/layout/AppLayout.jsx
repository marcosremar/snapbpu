import { useSidebar } from "../../context/SidebarContext";
import AppHeader from "./AppHeader";
import AppSidebar from "./AppSidebar";

const Backdrop = () => {
  const { isMobileOpen, toggleMobileSidebar } = useSidebar();

  if (!isMobileOpen) return null;

  return (
    <div
      className="fixed inset-0 z-40 bg-gray-900/50 lg:hidden"
      onClick={toggleMobileSidebar}
    />
  );
};

const AppLayout = ({ user, onLogout, children, isDemo = false, dashboardStats = null }) => {
  const { isExpanded } = useSidebar();

  return (
    <div className="min-h-screen bg-[#0a0d0a] relative overflow-hidden">
      {/* Decorative Background Elements */}
      <div className="fixed top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-brand-500/5 blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-brand-400/5 blur-[100px] pointer-events-none" />

      {/* Sidebar */}
      <AppSidebar isDemo={isDemo} />

      {/* Backdrop for mobile */}
      <Backdrop />

      {/* Main Content */}
      <div
        className={`transition-all duration-300 ease-in-out relative z-10 ${isExpanded ? "lg:pl-[260px]" : "lg:pl-[80px]"
          }`}
      >
        {/* Header */}
        <AppHeader user={user} onLogout={onLogout} isDemo={isDemo} dashboardStats={dashboardStats} />

        {/* Page Content */}
        <main className="p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
