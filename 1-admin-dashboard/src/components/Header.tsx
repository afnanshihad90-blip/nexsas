import React, { useState, useRef, useEffect } from 'react';
import {
  Bell,
  Calendar,
  CheckCheck,
  ChevronDown,
  Menu,
  Moon,
  Search,
  ServerOff,
  Settings,
  ShieldCheck,
  Sun,
  User,
  X,
} from 'lucide-react';
import { GENERATED_ASSETS, NAVIGATION_ITEMS } from '../data/mockDashboardData';
import {
  AIAgent,
  ArticleRecord,
  DateRangeOption,
  NavPageId,
  NotificationItem,
} from '../types/dashboard';

interface HeaderProps {
  activePage: NavPageId;
  onSelectPage: (page: NavPageId) => void;
  onOpenMobileNav: () => void;
  dateRange: DateRangeOption;
  onChangeDateRange: (range: DateRangeOption) => void;
  searchQuery: string;
  onChangeSearchQuery: (q: string) => void;
  notifications: NotificationItem[];
  onMarkAllNotificationsRead: () => void;
  onSelectNotification: (notif: NotificationItem) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  articles: ArticleRecord[];
  agents: AIAgent[];
  currentUser?: { email: string; role: string } | null;
  onOpenLogin?: () => void;
  onLogout?: () => void;
}

const DATE_RANGES: { value: DateRangeOption; label: string }[] = [
  { value: '24h', label: 'Last 24h' },
  { value: '7d', label: 'Last 7d' },
  { value: '30d', label: 'Last 30d' },
  { value: '90d', label: 'Last 90d' },
];

export const Header: React.FC<HeaderProps> = ({
  activePage,
  onSelectPage,
  onOpenMobileNav,
  dateRange,
  onChangeDateRange,
  searchQuery,
  onChangeSearchQuery,
  notifications,
  onMarkAllNotificationsRead,
  onSelectNotification,
  darkMode,
  onToggleDarkMode,
  articles,
  agents,
  currentUser,
  onOpenLogin,
  onLogout,
}) => {
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);
  const [avatarFailed, setAvatarFailed] = useState(false);

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  const currentNav =
    NAVIGATION_ITEMS.find((item) => item.id === activePage) ?? NAVIGATION_ITEMS[0];
  const unreadCount = notifications.filter((n) => !n.read).length;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchFocused(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const trimmedQuery = searchQuery.trim().toLowerCase();
  const matchedNavItems = trimmedQuery
    ? NAVIGATION_ITEMS.filter(
        (item) =>
          item.label.toLowerCase().includes(trimmedQuery) ||
          item.section.toLowerCase().includes(trimmedQuery) ||
          item.description.toLowerCase().includes(trimmedQuery)
      ).slice(0, 4)
    : [];

  const matchedArticles = trimmedQuery
    ? articles
        .filter(
          (a) =>
            a.headline.toLowerCase().includes(trimmedQuery) ||
            a.category.toLowerCase().includes(trimmedQuery) ||
            a.id.toLowerCase().includes(trimmedQuery)
        )
        .slice(0, 3)
    : [];

  const matchedAgents = trimmedQuery
    ? agents
        .filter(
          (ag) =>
            ag.name.toLowerCase().includes(trimmedQuery) ||
            ag.role.toLowerCase().includes(trimmedQuery) ||
            ag.currentTask.toLowerCase().includes(trimmedQuery)
        )
        .slice(0, 3)
    : [];

  return (
    <header className="sticky top-0 z-30 bg-white/95 dark:bg-[#0D1320]/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-800/90 px-4 lg:px-6 py-2.5 lg:py-0 lg:h-16 flex flex-wrap lg:flex-nowrap items-center justify-between gap-2.5 lg:gap-4">
      {/* Left Zone: Mobile Hamburger + Breadcrumb / Page Title */}
      <div className="flex items-center gap-2.5 min-w-0 shrink-0">
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
          className="lg:hidden p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 min-w-0">
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
            <span>{currentNav.section}</span>
            <span aria-hidden="true">/</span>
          </div>
          <h1 className="font-display font-semibold text-sm sm:text-base text-slate-900 dark:text-white truncate max-w-[140px] sm:max-w-none">
            {currentNav.label}
          </h1>
        </div>
      </div>

      {/* Center Zone: Global Search Input */}
      <div
        ref={searchRef}
        className="relative order-3 lg:order-2 w-full lg:w-auto lg:flex-1 lg:max-w-md"
      >
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 pointer-events-none" />
          <input
            type="search"
            value={searchQuery}
            onFocus={() => setSearchFocused(true)}
            onChange={(e) => {
              onChangeSearchQuery(e.target.value);
              setSearchFocused(true);
            }}
            placeholder="Search modules, articles, or AI agents..."
            aria-label="Search modules, articles, or AI agents"
            className="w-full pl-9 pr-8 py-1.5 text-xs sm:text-sm rounded-lg bg-slate-100 dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500 transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onChangeSearchQuery('')}
              aria-label="Clear search query"
              className="absolute right-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Live Search Dropdown */}
        {searchFocused && trimmedQuery.length > 0 && (
          <div className="absolute left-0 right-0 mt-1.5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xl p-2 z-50 max-h-96 overflow-y-auto">
            {matchedNavItems.length === 0 &&
            matchedArticles.length === 0 &&
            matchedAgents.length === 0 ? (
              <div className="py-4 px-3 text-center text-xs text-slate-500 dark:text-slate-400">
                No matching modules, articles, or agents for &ldquo;{searchQuery}&rdquo;.
              </div>
            ) : (
              <div className="space-y-3">
                {matchedNavItems.length > 0 && (
                  <div>
                    <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                      Navigation Modules
                    </div>
                    {matchedNavItems.map((nav) => (
                      <button
                        key={nav.id}
                        type="button"
                        onClick={() => {
                          onSelectPage(nav.id);
                          setSearchFocused(false);
                        }}
                        className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/80 flex items-center justify-between text-xs"
                      >
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {nav.label}
                        </span>
                        <span className="text-slate-400 dark:text-slate-500">
                          {nav.section}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {matchedAgents.length > 0 && (
                  <div>
                    <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                      AI Agents
                    </div>
                    {matchedAgents.map((ag) => (
                      <button
                        key={ag.id}
                        type="button"
                        onClick={() => {
                          onSelectPage('ai-agents');
                          setSearchFocused(false);
                        }}
                        className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/80 flex items-center justify-between text-xs"
                      >
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {ag.name}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400">
                          {ag.status}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {matchedArticles.length > 0 && (
                  <div>
                    <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                      Editorial Articles
                    </div>
                    {matchedArticles.map((art) => (
                      <button
                        key={art.id}
                        type="button"
                        onClick={() => {
                          onSelectPage('articles');
                          setSearchFocused(false);
                        }}
                        className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/80 text-xs"
                      >
                        <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                          {art.headline}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {art.id} · {art.category} · {art.stage}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Zone: Date Range Selector, System Status Indicator, Theme Toggle, Notifications, Profile */}
      <div className="order-2 lg:order-3 flex items-center gap-1.5 sm:gap-3 shrink-0">
        {/* Date Range Segmented Control */}
        <div
          role="group"
          aria-label="Date range selector"
          className="hidden xl:flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800"
        >
          <Calendar className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1 shrink-0" />
          {DATE_RANGES.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onChangeDateRange(r.value)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                dateRange === r.value
                  ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-2xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        {/* Compact Date Range Select for Smaller Screens */}
        <div className="xl:hidden">
          <select
            aria-label="Select date range"
            value={dateRange}
            onChange={(e) => onChangeDateRange(e.target.value as DateRangeOption)}
            className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200"
          >
            {DATE_RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {/* System Status Indicator (Honest Step 1 Indicator) */}
        <button
          type="button"
          onClick={() => onSelectPage('system-health')}
          title="Inspect System Health status"
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 hover:border-blue-500/40 transition-colors whitespace-nowrap shrink-0"
        >
          <ServerOff className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span>Step 1 Demo</span>
          <span aria-hidden="true" className="text-slate-400">
            ·
          </span>
          <span className="text-slate-500 dark:text-slate-400">API Unbound</span>
        </button>

        {/* Theme Toggle */}
        <button
          type="button"
          onClick={onToggleDarkMode}
          aria-label={darkMode ? 'Switch to light theme' : 'Switch to dark theme'}
          title={darkMode ? 'Switch to light theme' : 'Switch to dark theme'}
          className="p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Notifications Dropdown */}
        <div ref={notifRef} className="relative">
          <button
            type="button"
            onClick={() => setNotifOpen((prev) => !prev)}
            aria-label={`Notifications (${unreadCount} unread)`}
            aria-expanded={notifOpen}
            className="relative p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 px-1 min-w-4 h-4 rounded-full bg-blue-600 text-white font-mono text-[10px] font-semibold flex items-center justify-center tabular-nums">
                {unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xl z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-display font-semibold text-xs text-slate-900 dark:text-white">
                    System &amp; Editorial Alerts
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    Step 1 local notification stream
                  </div>
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={onMarkAllNotificationsRead}
                    className="flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>

              <div className="divide-y divide-slate-200/70 dark:divide-slate-800/80 max-h-80 overflow-y-auto">
                {notifications.map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => {
                      onSelectNotification(n);
                      setNotifOpen(false);
                    }}
                    className={`w-full text-left px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${
                      !n.read ? 'bg-blue-50/40 dark:bg-blue-950/20' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-medium text-xs text-slate-900 dark:text-slate-100">
                        {n.title}
                      </span>
                      <span className="font-mono text-[11px] text-slate-400 shrink-0 tabular-nums">
                        {n.timestamp}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                      {n.detail}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Admin Profile Menu */}
        <div ref={profileRef} className="relative">
          <button
            type="button"
            onClick={() => setProfileOpen((prev) => !prev)}
            aria-label="Admin profile menu"
            aria-expanded={profileOpen}
            className="flex items-center gap-2 pl-1.5 pr-2 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {!avatarFailed ? (
              <img
                src={GENERATED_ASSETS.adminAvatar}
                alt="Elena Rostova — Managing AI Operator"
                referrerPolicy="no-referrer"
                onError={() => setAvatarFailed(true)}
                className="w-7 h-7 rounded-full object-cover border border-slate-300 dark:border-slate-700 shrink-0"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold shrink-0">
                ER
              </div>
            )}
            <div className="hidden md:block text-left">
              <div className="text-xs font-medium text-slate-900 dark:text-slate-100 leading-none whitespace-nowrap">
                E. Rostova
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 whitespace-nowrap">
                Ops Architect
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>

          {profileOpen && (
            <div className="absolute right-0 mt-2 w-60 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xl z-50 py-1.5">
              <div className="px-4 py-2.5 border-b border-slate-200 dark:border-slate-800">
                <div className="font-display font-semibold text-xs text-slate-900 dark:text-white">
                  {currentUser ? currentUser.email : 'Guest / Offline Operator'}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  {currentUser ? `Role: ${currentUser.role}` : 'Not Signed In (Read-Only)'}
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 mt-1 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{currentUser ? 'JWT Session Verified' : 'Click below to authenticate'}</span>
                </div>
              </div>

              <div className="py-1">
                {currentUser ? (
                  <button
                    type="button"
                    onClick={() => {
                      onLogout?.();
                      setProfileOpen(false);
                    }}
                    className="w-full px-4 py-2 text-left text-xs text-rose-600 dark:text-rose-400 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2"
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      onOpenLogin?.();
                      setProfileOpen(false);
                    }}
                    className="w-full px-4 py-2 text-left text-xs text-blue-600 dark:text-blue-400 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 font-medium"
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>Sign In (JWT Login)</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    onSelectPage('settings');
                    setProfileOpen(false);
                  }}
                  className="w-full px-4 py-2 text-left text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2"
                >
                  <Settings className="w-3.5 h-3.5 text-slate-400" />
                  <span>Platform Settings</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onSelectPage('api-connections');
                    setProfileOpen(false);
                  }}
                  className="w-full px-4 py-2 text-left text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2"
                >
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span>API Service Abstraction</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
