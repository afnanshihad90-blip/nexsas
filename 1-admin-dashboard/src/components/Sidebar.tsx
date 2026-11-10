import React from 'react';
import {
  Activity,
  BarChart3,
  Bot,
  CalendarClock,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Database,
  DollarSign,
  FileEdit,
  FileText,
  Flame,
  GitBranch,
  Globe,
  Image as ImageIcon,
  Layers,
  LayoutDashboard,
  Link2,
  ListTodo,
  Newspaper,
  SearchCheck,
  Settings,
  Share2,
  Sliders,
  Video,
  X,
} from 'lucide-react';
import { NAVIGATION_ITEMS } from '../data/mockDashboardData';
import { NavItem, NavPageId, NavSectionName } from '../types/dashboard';

interface SidebarProps {
  activePage: NavPageId;
  onSelectPage: (page: NavPageId) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  activeAgentCount: number;
  totalAgentCount: number;
}

const SECTION_ORDER: NavSectionName[] = [
  'Overview',
  'Intelligence',
  'Content',
  'Automation',
  'Distribution',
  'Analytics',
  'System',
];

function getNavIcon(id: NavPageId) {
  switch (id) {
    case 'dashboard':
      return LayoutDashboard;
    case 'system-health':
      return Cpu;
    case 'trending-news':
      return Flame;
    case 'news-sources':
      return Newspaper;
    case 'research-center':
      return Layers;
    case 'fact-checking':
      return CheckCircle2;
    case 'articles':
      return FileText;
    case 'article-editor':
      return FileEdit;
    case 'seo-analysis':
      return SearchCheck;
    case 'media-library':
      return ImageIcon;
    case 'ai-agents':
      return Bot;
    case 'workflow-manager':
      return GitBranch;
    case 'publishing-queue':
      return ListTodo;
    case 'scheduler':
      return CalendarClock;
    case 'social-accounts':
      return Share2;
    case 'social-publishing':
      return Globe;
    case 'youtube-publishing':
      return Video;
    case 'website-traffic':
      return BarChart3;
    case 'social-reach':
      return Activity;
    case 'revenue-analytics':
      return DollarSign;
    case 'api-connections':
      return Link2;
    case 'database-status':
      return Database;
    case 'activity-logs':
      return Sliders;
    case 'settings':
      return Settings;
  }
}

export const Sidebar: React.FC<SidebarProps> = ({
  activePage,
  onSelectPage,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  activeAgentCount,
  totalAgentCount,
}) => {
  const grouped = SECTION_ORDER.map((section) => ({
    section,
    items: NAVIGATION_ITEMS.filter((item) => item.section === section),
  }));

  const handleNavClick = (id: NavPageId) => {
    onSelectPage(id);
    if (mobileOpen) {
      onCloseMobile();
    }
  };

  const renderNavContent = (isMobileDrawer: boolean) => {
    const isCollapsedView = !isMobileDrawer && collapsed;

    return (
      <div className="flex flex-col h-full bg-white dark:bg-[#0D1320] text-slate-800 dark:text-slate-200 border-r border-slate-200 dark:border-slate-800/90 select-none">
        {/* Top Sidebar Brand / Collapse Controls */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-800/90 shrink-0">
          {!isCollapsedView && (
            <button
              type="button"
              onClick={() => handleNavClick('dashboard')}
              className="flex items-center gap-2.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-md"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white font-display font-bold text-sm shrink-0">
                NX
              </div>
              <div className="min-w-0">
                <div className="font-display font-bold text-sm text-slate-900 dark:text-white whitespace-nowrap">
                  NEXUS MEDIA AI
                </div>
                <div className="text-[11px] text-emerald-500 dark:text-emerald-400 whitespace-nowrap font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Control Plane · Online
                </div>
              </div>
            </button>
          )}

          {isCollapsedView && (
            <button
              type="button"
              onClick={() => handleNavClick('dashboard')}
              aria-label="NEXUS MEDIA AI Home"
              className="mx-auto w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white font-display font-bold text-sm"
            >
              NX
            </button>
          )}

          {isMobileDrawer ? (
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Close navigation menu"
              className="p-2 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/70 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          ) : (
            !isCollapsedView && (
              <button
                type="button"
                onClick={onToggleCollapse}
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
                className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/70 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )
          )}
        </div>

        {/* Expand button when collapsed on desktop */}
        {isCollapsedView && (
          <div className="flex justify-center py-2 border-b border-slate-200 dark:border-slate-800/90">
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label="Expand sidebar"
              title="Expand sidebar"
              className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/70 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Scrollable Navigation Sections */}
        <nav
          aria-label="Main Navigation"
          className="flex-1 overflow-y-auto py-3 px-2.5 space-y-5 scrollbar-thin"
        >
          {grouped.map(({ section, items }) => (
            <div key={section}>
              {!isCollapsedView ? (
                <div className="px-2.5 mb-1.5 text-[11px] font-semibold tracking-wider text-slate-400 dark:text-slate-500">
                  {section}
                </div>
              ) : (
                <div className="h-px bg-slate-200 dark:bg-slate-800 my-2 mx-2" />
              )}

              <ul className="space-y-0.5">
                {items.map((item: NavItem) => {
                  const Icon = getNavIcon(item.id);
                  const isActive = activePage === item.id;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => handleNavClick(item.id)}
                        title={isCollapsedView ? `${section}: ${item.label}` : undefined}
                        aria-current={isActive ? 'page' : undefined}
                        className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors ${
                          isActive
                            ? 'bg-blue-600/10 text-blue-600 dark:bg-blue-500/15 dark:text-blue-400 font-semibold'
                            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100/80 dark:hover:bg-slate-800/50'
                        } ${isCollapsedView ? 'justify-center' : 'justify-between'}`}
                      >
                        <span className="flex items-center gap-2.5 min-w-0">
                          <Icon
                            className={`w-4 h-4 shrink-0 ${
                              isActive
                                ? 'text-blue-600 dark:text-blue-400'
                                : 'text-slate-400 dark:text-slate-500'
                            }`}
                          />
                          {!isCollapsedView && (
                            <span className="truncate whitespace-nowrap">{item.label}</span>
                          )}
                        </span>

                        {!isCollapsedView && item.id === 'ai-agents' && (
                          <span className="font-mono text-[11px] tabular-nums text-slate-500 dark:text-slate-400 shrink-0">
                            {activeAgentCount}/{totalAgentCount}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Bottom Production Architecture Status */}
        {!isCollapsedView && (
          <div className="p-3 m-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-slate-600 dark:text-slate-400">
            <div className="font-semibold text-emerald-600 dark:text-emerald-400 mb-0.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Autonomous News Pipeline
            </div>
            <div className="leading-relaxed text-slate-500 dark:text-slate-400">
              FastAPI + DeepSeek AI + Supabase PostgreSQL
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        aria-label="Desktop Sidebar"
        className={`hidden lg:block shrink-0 transition-all duration-150 ${
          collapsed ? 'w-16' : 'w-64'
        }`}
      >
        <div className="sticky top-0 h-screen">{renderNavContent(false)}</div>
      </aside>

      {/* Mobile Overlay Navigation Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 w-72 max-w-[85vw] h-full">
            {renderNavContent(true)}
          </div>
        </div>
      )}
    </>
  );
};
