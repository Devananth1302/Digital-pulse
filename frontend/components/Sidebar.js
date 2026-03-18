import { useState, useCallback, memo, useMemo } from 'react';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '◎' },
  { id: 'narratives', label: 'Narratives', icon: '◈' },
  { id: 'emerging', label: 'Emerging', icon: '⚡' },
  { id: 'forecast', label: 'Forecast', icon: '◉' },
  { id: 'upload', label: 'Upload', icon: '↑' },
];

// Memoized nav item component to prevent re-renders
const NavItem = memo(function NavItem({ item, isActive, onClick, collapsed }) {
  return (
    <button
      className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
      title={item.label}
    >
      <span className="nav-icon">{item.icon}</span>
      {!collapsed && <span className="nav-label">{item.label}</span>}
      {isActive && <span className="nav-indicator" />}
    </button>
  );
});

function Sidebar({ activeView, onNavigate }) {
  const [collapsed, setCollapsed] = useState(false);

  const toggleCollapsed = useCallback(() => setCollapsed(c => !c), []);

  // Create stable click handlers for each nav item
  const navHandlers = useMemo(() => {
    const handlers = {};
    NAV_ITEMS.forEach(item => {
      handlers[item.id] = () => onNavigate(item.id);
    });
    return handlers;
  }, [onNavigate]);

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <span className="logo-icon">◉</span>
          {!collapsed && <span className="logo-text">Digital Pulse</span>}
        </div>
        <button
          className="sidebar-toggle"
          onClick={toggleCollapsed}
          aria-label="Toggle sidebar"
        >
          {collapsed ? '▸' : '◂'}
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.id}
            item={item}
            isActive={activeView === item.id}
            onClick={navHandlers[item.id]}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* Status */}
      <div className="sidebar-footer">
        <div className="status-dot" />
        {!collapsed && <span className="status-text">Pipeline Active</span>}
      </div>
    </aside>
  );
}

export default memo(Sidebar);
