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

const AppLayout = ({ user, onLogout, children, isDemo = false }) => {
  const { isExpanded } = useSidebar();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0d0a]">
      {/* Sidebar */}
      <AppSidebar isDemo={isDemo} />

      {/* Backdrop for mobile */}
      <Backdrop />

      {/* Main Content */}
      <div
        className={`transition-all duration-300 ease-in-out ${
          isExpanded ? "lg:pl-[260px]" : "lg:pl-[80px]"
        }`}
      >
        {/* Header */}
        <AppHeader user={user} onLogout={onLogout} isDemo={isDemo} />

        {/* Page Content */}
        <main className="p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
