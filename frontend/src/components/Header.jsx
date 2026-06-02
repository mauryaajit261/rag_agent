import mySetuLogo from '../assets/mysetu_logo.png';
import './Header.css';

function Header({ systemHealth, session }) {
    const getStatusColor = () => {
        if (!systemHealth) return '#94A3B8';
        if (systemHealth.status === 'healthy' && systemHealth.ollama_available) return '#00963A';
        if (systemHealth.status === 'healthy') return '#F59E0B';
        return '#EF4444';
    };

    const getStatusText = () => {
        if (!systemHealth) return 'Checking...';
        if (systemHealth.status === 'healthy' && systemHealth.ollama_available) return 'System Safe';
        if (systemHealth.status === 'healthy') return 'System Warning (Ollama)';
        return 'System Critical';
    };

    return (
        <header className="header">
            <div className="header-content">
                <div className="header-left">
                    <div className="logo">
                        <img src={mySetuLogo} alt="mySetu" className="logo-image" />
                        <div className="logo-wordmark">
                            <span className="logo-name">
                                my<span className="blue">Setu</span> <span className="green">AI</span>
                            </span>
                            <span className="logo-badge">Knowledge Assistant</span>
                        </div>
                    </div>
                </div>

                <div className="header-right">
                    <div className="system-status">
                        <div className="status-indicator" style={{ backgroundColor: getStatusColor() }} />
                        <span className="status-text">{getStatusText()}</span>
                    </div>

                    {systemHealth && (
                        <div className="stats">
                            <div className="stat-item">
                                <span className="stat-value">{systemHealth.documents_indexed || 0}</span>
                                <span className="stat-label">Documents</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">{systemHealth.databases_connected || 0}</span>
                                <span className="stat-label">Databases</span>
                            </div>
                        </div>
                    )}

                    {session && (
                        <button
                            className="btn-logout"
                            onClick={() => {
                                import('../supabaseClient').then(({ supabase }) => {
                                    supabase.auth.signOut();
                                });
                            }}
                        >
                            Log Out
                        </button>
                    )}
                </div>
            </div>
        </header>
    );
}

export default Header;
