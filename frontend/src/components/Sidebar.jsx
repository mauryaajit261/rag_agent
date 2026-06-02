import './Sidebar.css';

function Sidebar({ activeView, onViewChange, isOpen = true }) {
    const menuItems = [
        { id: 'chat', icon: '💬', label: 'AI Chat', sub: 'Interactive Assistant' },
        { id: 'documents', icon: '📄', label: 'Documents', sub: 'Knowledge Base' },
        { id: 'databases', icon: '🗄️', label: 'Databases', sub: 'Structured Data' },
        { id: 'profile', icon: '👤', label: 'User Profile', sub: 'Account Settings' },
    ];

    return (
        <aside className={`sidebar ${isOpen ? '' : 'collapsed'}`}>
            <nav className="sidebar-nav">
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        className={`nav-item ${activeView === item.id ? 'active' : ''}`}
                        onClick={() => onViewChange(item.id)}
                        title={item.label}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        <div className="nav-content">
                            <span className="nav-text">{item.label}</span>
                            <span className="nav-subtitle">{item.sub}</span>
                        </div>
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="version">v1.0.0</div>
            </div>
        </aside>
    );
}

export default Sidebar;
