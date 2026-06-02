import { useState, useEffect } from 'react';
import './DatabaseManager.css';
import api from '../api';

function DatabaseManager({ onRefresh }) {
    const [databases, setDatabases] = useState([]);
    const [showConnectForm, setShowConnectForm] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [formData, setFormData] = useState({
        db_type: 'mysql',
        host: 'localhost',
        port: 3306,
        database: '',
        username: '',
        password: '',
        connection_name: '',
        tables: '',
    });

    useEffect(() => {
        loadDatabases();
    }, []);

    const loadDatabases = async () => {
        try {
            const dbs = await api.listDatabases();
            setDatabases(dbs);
        } catch (error) {
            console.error('Failed to load databases:', error);
        }
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
            // Update port based on database type
            ...(name === 'db_type' && {
                port: value === 'mysql' ? 3306 : value === 'postgresql' ? 5432 : value === 'mongodb' ? 27017 : 3306
            })
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsConnecting(true);

        try {
            const config = {
                ...formData,
                port: parseInt(formData.port),
                tables: formData.tables ? formData.tables.split(',').map(t => t.trim()).filter(Boolean) : null,
            };

            await api.connectDatabase(config);

            // Reset form and reload
            setFormData({
                db_type: 'mysql',
                host: 'localhost',
                port: 3306,
                database: '',
                username: '',
                password: '',
                connection_name: '',
                tables: '',
            });
            setShowConnectForm(false);
            await loadDatabases();
            onRefresh();
        } catch (error) {
            alert(`Database connection failed: ${error.message}`);
        } finally {
            setIsConnecting(false);
        }
    };

    const handleDeleteDatabase = async (dbId) => {
        if (window.confirm("Are you sure you want to delete this database connection and its indexed memory?")) {
            try {
                await api.deleteDatabase(dbId);
                await loadDatabases();
                onRefresh();
            } catch (error) {
                alert(`Failed to delete database: ${error.message}`);
            }
        }
    };

    const getDbIcon = (dbType) => {
        const icons = {
            mysql: '🐬',
            postgresql: '🐘',
            mongodb: '🍃',
            sqlite: '💾',
        };
        return icons[dbType] || '🗄️';
    };

    const getStatusBadge = (status) => {
        const badges = {
            completed: { class: 'badge-success', text: '✓ Connected' },
            processing: { class: 'badge-warning', text: '⏳ Processing' },
            failed: { class: 'badge-error', text: '✗ Failed' },
            pending: { class: 'badge-info', text: '⏸ Pending' },
        };
        return badges[status] || badges.pending;
    };

    return (
        <div className="database-manager">
            <div className="manager-header">
                <div>
                    <h2>🗄️ Database Management</h2>
                    <p className="manager-subtitle">
                        Connect databases to query structured data with natural language
                    </p>
                </div>
                <div className="header-actions">
                    <button className="btn-refresh" onClick={loadDatabases}>
                        🔄 Refresh
                    </button>
                    <button
                        className="btn-retry"
                        onClick={() => setShowConnectForm(!showConnectForm)}
                    >
                        {showConnectForm ? '✕ Cancel' : '+ Connect Database'}
                    </button>
                </div>
            </div>

            {showConnectForm && (
                <div className="connect-form-container">
                    <form className="connect-form" onSubmit={handleSubmit}>
                        <h3>Connect New Database</h3>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="connection_name">Connection Name *</label>
                                <input
                                    type="text"
                                    id="connection_name"
                                    name="connection_name"
                                    value={formData.connection_name}
                                    onChange={handleInputChange}
                                    placeholder="My Database"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="db_type">Database Type *</label>
                                <select
                                    id="db_type"
                                    name="db_type"
                                    value={formData.db_type}
                                    onChange={handleInputChange}
                                    required
                                >
                                    <option value="mysql">MySQL</option>
                                    <option value="postgresql">PostgreSQL</option>
                                    <option value="mongodb">MongoDB</option>
                                    <option value="sqlite">SQLite</option>
                                </select>
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="host">Host *</label>
                                <input
                                    type="text"
                                    id="host"
                                    name="host"
                                    value={formData.host}
                                    onChange={handleInputChange}
                                    placeholder="localhost"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="port">Port *</label>
                                <input
                                    type="number"
                                    id="port"
                                    name="port"
                                    value={formData.port}
                                    onChange={handleInputChange}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="database">Database Name *</label>
                            <input
                                type="text"
                                id="database"
                                name="database"
                                value={formData.database}
                                onChange={handleInputChange}
                                placeholder="my_database"
                                required
                            />
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="username">Username *</label>
                                <input
                                    type="text"
                                    id="username"
                                    name="username"
                                    value={formData.username}
                                    onChange={handleInputChange}
                                    placeholder="root"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="password">Password *</label>
                                <input
                                    type="password"
                                    id="password"
                                    name="password"
                                    value={formData.password}
                                    onChange={handleInputChange}
                                    placeholder="••••••••"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="tables">
                                Tables (optional)
                                <span className="label-hint">Comma-separated. Leave empty for all tables</span>
                            </label>
                            <input
                                type="text"
                                id="tables"
                                name="tables"
                                value={formData.tables}
                                onChange={handleInputChange}
                                placeholder="users, products, orders"
                            />
                        </div>

                        <div className="form-actions">
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => setShowConnectForm(false)}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn-retry"
                                disabled={isConnecting}
                            >
                                {isConnecting ? (
                                    <>
                                        <div className="spinner"></div>
                                        Connecting...
                                    </>
                                ) : (
                                    'Connect & Index'
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="databases-list">
                <div className="list-header">
                    <h3>Connected Databases ({databases.length})</h3>
                </div>

                {databases.length === 0 ? (
                    <div className="empty-databases">
                        <div className="empty-icon">🗄️</div>
                        <p>No databases connected yet</p>
                        <p className="empty-hint">Connect your first database to enable querying</p>
                    </div>
                ) : (
                    <div className="databases-grid">
                        {databases.map((db) => (
                            <div key={db.id} className="database-card">
                                <button
                                    onClick={() => handleDeleteDatabase(db.id)}
                                    className="btn-delete btn-delete-float"
                                    title="Delete Database"
                                >
                                    🗑️ Delete
                                </button>
                                <div className="database-icon">
                                    {getDbIcon(db.db_type)}
                                </div>

                                <div className="database-info">
                                    <h4 className="database-name">{db.connection_name}</h4>

                                    <div className="database-details">
                                        <div className="detail-item">
                                            <span className="detail-label">Type:</span>
                                            <span className="detail-value">{db.db_type.toUpperCase()}</span>
                                        </div>
                                        <div className="detail-item">
                                            <span className="detail-label">Host:</span>
                                            <span className="detail-value">{db.host}:{db.port}</span>
                                        </div>
                                        <div className="detail-item">
                                            <span className="detail-label">Database:</span>
                                            <span className="detail-value">{db.database}</span>
                                        </div>
                                        {db.table_count !== null && (
                                            <div className="detail-item">
                                                <span className="detail-label">Tables:</span>
                                                <span className="detail-value">{db.table_count}</span>
                                            </div>
                                        )}
                                    </div>

                                    <div className="database-footer">
                                        <span className={`badge ${getStatusBadge(db.status).class}`}>
                                            {getStatusBadge(db.status).text}
                                        </span>
                                        {db.indexed_date && (
                                            <span className="database-date">
                                                {new Date(db.indexed_date).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default DatabaseManager;
