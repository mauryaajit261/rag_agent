import { useState, useEffect, useRef } from 'react';
import './DocumentManager.css';
import api from '../api';

function DocumentManager({ onRefresh }) {
    const [documents, setDocuments] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);

    useEffect(() => {
        loadDocuments();

        // Auto-refresh polling if there are processing documents
        const interval = setInterval(() => {
            const hasProcessing = documents.some(doc => doc.status === 'processing');
            if (hasProcessing || documents.length === 0) {
                loadDocuments();
            }
        }, 5000);

        return () => clearInterval(interval);
    }, [documents]);

    const loadDocuments = async () => {
        try {
            const docs = await api.listDocuments();
            setDocuments(docs);
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    };

    const handleDeleteDocument = async (docId, e) => {
        e.stopPropagation();
        if (!window.confirm('Are you sure you want to delete this document? This will remove it from the knowledge base.')) return;

        try {
            await api.deleteDocument(docId);
            setDocuments(docs => docs.filter(doc => doc.id !== docId));
        } catch (error) {
            console.error('Failed to delete document:', error);
            alert(`Delete failed: ${error.message}`);
        }
    };

    const handleFileSelect = async (files) => {
        if (!files || files.length === 0) return;

        const file = files[0];
        setIsUploading(true);
        setUploadProgress({ filename: file.name, status: 'uploading' });

        try {
            const result = await api.uploadDocument(file);

            if (result.success) {
                setUploadProgress({ filename: file.name, status: 'success' });
                await loadDocuments();
                onRefresh();

                setTimeout(() => setUploadProgress(null), 3000);
            } else {
                setUploadProgress({ filename: file.name, status: 'error', message: result.message });
            }
        } catch (error) {
            setUploadProgress({
                filename: file.name,
                status: 'error',
                message: error.message
            });
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files);
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const getStatusBadge = (status) => {
        const badges = {
            completed: { class: 'badge-success', text: '✓ Completed' },
            processing: { class: 'badge-warning', text: '⏳ Processing' },
            failed: { class: 'badge-error', text: '✗ Failed' },
            pending: { class: 'badge-info', text: '⏸ Pending' },
        };
        return badges[status] || badges.pending;
    };

    return (
        <div className="document-manager">
            <div className="manager-header">
                <div>
                    <h2>📄 Document Management</h2>
                    <p className="manager-subtitle">
                        Upload and manage your documents for intelligent querying
                    </p>
                </div>
                <button className="btn-refresh" onClick={loadDocuments}>
                    🔄 Refresh
                </button>
            </div>

            <div
                className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    className="file-input"
                    accept=".pdf,.txt,.docx,.csv,.xlsx,.md"
                    onChange={(e) => handleFileSelect(e.target.files)}
                    disabled={isUploading}
                />

                <div className="upload-icon">📤</div>
                <h3>Upload Documents</h3>
                <p>Drag and drop files here, or click to browse</p>
                <div className="supported-formats">
                    <span className="format-badge">PDF</span>
                    <span className="format-badge">DOCX</span>
                    <span className="format-badge">TXT</span>
                    <span className="format-badge">CSV</span>
                    <span className="format-badge">XLSX</span>
                    <span className="format-badge">MD</span>
                </div>
            </div>

            {uploadProgress && (
                <div className={`upload-progress upload-${uploadProgress.status}`}>
                    <div className="progress-icon">
                        {uploadProgress.status === 'uploading' && <div className="spinner"></div>}
                        {uploadProgress.status === 'success' && '✓'}
                        {uploadProgress.status === 'error' && '✗'}
                    </div>
                    <div className="progress-content">
                        <div className="progress-filename">{uploadProgress.filename}</div>
                        <div className="progress-status">
                            {uploadProgress.status === 'uploading' && 'Processing...'}
                            {uploadProgress.status === 'success' && 'Successfully uploaded and indexed'}
                            {uploadProgress.status === 'error' && (uploadProgress.message || 'Upload failed')}
                        </div>
                    </div>
                </div>
            )}

            <div className="documents-list">
                <div className="list-header">
                    <h3>Uploaded Documents ({documents.length})</h3>
                </div>

                {documents.length === 0 ? (
                    <div className="empty-documents">
                        <div className="empty-icon">📭</div>
                        <p>No documents uploaded yet</p>
                        <p className="empty-hint">Upload your first document to get started</p>
                    </div>
                ) : (
                    <div className="documents-grid">
                        {documents.map((doc) => (
                            <div key={doc.id} className="document-card">
                                <div className="document-icon">
                                    {doc.file_type === 'pdf' && '📕'}
                                    {doc.file_type === 'docx' && '📘'}
                                    {doc.file_type === 'txt' && '📄'}
                                    {doc.file_type === 'csv' && '📊'}
                                    {doc.file_type === 'xlsx' && '📗'}
                                    {doc.file_type === 'md' && '📝'}
                                </div>

                                <div className="document-info">
                                    <div className="document-name-row">
                                        <h4 className="document-name" title={doc.filename}>
                                            {doc.filename}
                                        </h4>
                                        <button
                                            className="btn-delete"
                                            onClick={(e) => handleDeleteDocument(doc.id, e)}
                                            title="Delete document"
                                        >
                                            🗑️
                                        </button>
                                    </div>

                                    <div className="document-meta">
                                        <span className="meta-item">{formatFileSize(doc.file_size)}</span>
                                        <span className="meta-item">{doc.chunk_count || 0} chunks</span>
                                    </div>

                                    <div className="document-footer">
                                        <span className={`badge ${getStatusBadge(doc.status).class}`}>
                                            {getStatusBadge(doc.status).text}
                                        </span>
                                        <span className="document-date">
                                            {new Date(doc.upload_date).toLocaleDateString()}
                                        </span>
                                    </div>

                                    {doc.error_message && (
                                        <div className="document-error">
                                            ⚠️ {doc.error_message}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default DocumentManager;
