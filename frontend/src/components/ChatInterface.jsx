import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatInterface.css';
import api from '../api';

const IMAGE_ANALYSIS_API = 'https://aiuat.mysetu.com/safe_unsafe_analysis/analyze_local';

function ChatInterface({ systemHealth, messages, setMessages, sourceType, setSourceType, checkSystemHealth }) {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isImageLoading, setIsImageLoading] = useState(false);
    const [streamingMessageId, setStreamingMessageId] = useState(null);

    // Multi-chat states
    const [chats, setChats] = useState([]);
    const [activeChatId, setActiveChatId] = useState(null);
    const [isChatsLoading, setIsChatsLoading] = useState(true);
    const [isHistoryOpen, setIsHistoryOpen] = useState(true); // collapsible chat-history panel

    // Image upload states
    const [showImageModal, setShowImageModal] = useState(false);
    const [selectedImage, setSelectedImage] = useState(null);     // { file, previewUrl }
    const [isDragging, setIsDragging] = useState(false);
    const imageInputRef = useRef(null);

    const hasInitialized = useRef(false);
    const activeChatIdRef = useRef(null);
    const messagesEndRef = useRef(null);
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    // Auto-collapse the chat-history panel on narrow screens (never force-opens —
    // the user keeps manual control via the header toggle on wide screens).
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth < 900) setIsHistoryOpen(false);
        };
        handleResize();
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Load messages for a specific chat
    const loadMessagesForChat = useCallback(async (chatId) => {
        if (!chatId) return;
        try {
            setIsLoading(true);
            const history = await api.getChatHistory(chatId);
            const mappedMessages = (history || []).map(msg => {
                let content = msg.content || '';
                let imagePreview = null;
                let imageAnalysisData = null;

                // Parse "Smart String" format for Image Analysis persistence
                if (content.startsWith('[USER_IMAGE]')) {
                    imagePreview = content.replace('[USER_IMAGE]', '');
                    content = '📷 Image uploaded for safety analysis';
                } else if (content.startsWith('[IMAGE_REPORT]')) {
                    try {
                        const payload = JSON.parse(content.replace('[IMAGE_REPORT]', ''));
                        imageAnalysisData = payload.imageAnalysisData;
                        imagePreview = payload.image_url;
                        content = 'Image Safety Analysis Report generated.';
                    } catch (e) {
                        console.error("Failed to parse image report from content", e);
                    }
                }

                return {
                    id: msg.id,
                    type: msg.role,
                    content: content,
                    imageAnalysisData: imageAnalysisData,
                    imagePreview: imagePreview,
                    timestamp: new Date(msg.created_at)
                };
            });
            console.log("Mapped History:", mappedMessages);
            setMessages(mappedMessages);
        } catch (error) {
            console.error("Failed to fetch messages", error);
            setMessages([]);
        } finally {
            setIsLoading(false);
        }
    }, [setMessages]);

    const refreshChatTitles = useCallback(async () => {
        try {
            const data = await api.listChats();
            setChats(data || []);
        } catch (error) {
            console.error("Failed to refresh chats", error);
        }
    }, []);

    const loadChats = useCallback(async () => {
        try {
            setIsChatsLoading(true);
            const data = await api.listChats();
            setChats(data || []);
            if (data?.length > 0) {
                if (!activeChatIdRef.current) {
                    setActiveChatId(data[0].id);
                    activeChatIdRef.current = data[0].id;
                }
            } else {
                const newChat = await api.createNewChat("New Conversation");
                setChats([newChat]);
                setActiveChatId(newChat.id);
                activeChatIdRef.current = newChat.id;
                setMessages([]);
            }
        } catch (error) {
            console.error("Failed to list chats", error);
        } finally {
            setIsChatsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!hasInitialized.current) {
            hasInitialized.current = true;
            loadChats();
        }
    }, [loadChats]);

    useEffect(() => {
        if (activeChatId) {
            activeChatIdRef.current = activeChatId;
            loadMessagesForChat(activeChatId);
        }
    }, [activeChatId, loadMessagesForChat]);

    const handleNewChat = async () => {
        try {
            const newChat = await api.createNewChat("New Conversation");
            setChats(prev => [newChat, ...prev]);
            setActiveChatId(newChat.id);
            setMessages([]);
        } catch (error) {
            console.error("Failed to create chat", error);
        }
    };

    const handleDeleteChat = async (chatId, e) => {
        e.stopPropagation();
        if (window.confirm("Delete this chat?")) {
            try {
                await api.deleteChat(chatId);
                const updatedChats = chats.filter(c => c.id !== chatId);
                setChats(updatedChats);
                if (activeChatId === chatId) {
                    if (updatedChats.length > 0) setActiveChatId(updatedChats[0].id);
                    else handleNewChat();
                }
            } catch (error) {
                console.error("Failed to delete chat", error);
                alert("Failed to delete chat.");
            }
        }
    };

    const handleImageFileSelect = (file) => {
        if (!file || !file.type.startsWith('image/')) return;
        setSelectedImage({ file, previewUrl: URL.createObjectURL(file) });
    };

    const handleImageDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        handleImageFileSelect(file);
    };

    const closeImageModal = () => {
        setShowImageModal(false);
        setSelectedImage(null);
        setIsDragging(false);
    };

    const sendImageMessage = async () => {
        if (!selectedImage) return;
        closeImageModal();

        const userMsgId = Date.now();
        const aiMsgId = Date.now() + 1;

        setMessages(prev => [...prev, {
            id: userMsgId,
            type: 'user',
            content: '📷 Image uploaded for analysis',
            imagePreview: selectedImage.previewUrl,
            timestamp: new Date(),
        }]);

        setMessages(prev => [...prev, {
            id: aiMsgId,
            type: 'assistant',
            content: '',
            isImageAnalysis: true,
            isLoading: true,
            timestamp: new Date(),
        }]);

        setIsImageLoading(true);
        setIsLoading(true);

        try {
            // 1. Step 1: External Analysis
            const data = await api.analyzeImage(IMAGE_ANALYSIS_API, selectedImage.file);
            const formatted = formatImageAnalysis(data);

            // 2. Step 2: Background Archiving (Persist to Supabase)
            let finalImageUrl = selectedImage.previewUrl;
            if (activeChatId) {
                try {
                    const archiveRes = await api.archiveAnalysis(activeChatId, selectedImage.file, data);
                    if (archiveRes.success) {
                        finalImageUrl = archiveRes.image_url;
                    }
                } catch (archiveErr) {
                    // Silent fail — user still sees the analysis, just won't persist
                    console.error("⚠️ Failed to archive analysis to Supabase:", archiveErr.message);
                }
            } else {
                console.warn("⚠️ No active chat session to archive image analysis.");
            }

            setMessages(prev => prev.map(msg => {
                if (msg.id === userMsgId) {
                    return { ...msg, imagePreview: finalImageUrl };
                }
                if (msg.id === aiMsgId) {
                    return { ...msg, content: formatted, imageAnalysisData: data, isLoading: false };
                }
                return msg;
            }));
        } catch (err) {
            setMessages(prev => prev.map(msg =>
                msg.id === aiMsgId
                    ? { ...msg, content: `❌ Image analysis failed: ${err.message}`, isLoading: false }
                    : msg
            ));
        } finally {
            setIsLoading(false);
            setIsImageLoading(false);
        }
    };

    const formatImageAnalysis = (data) => {
        const safe = (data.safety_condition || data.status || '').toUpperCase();
        const safeEmoji = safe.includes('UNSAFE') ? '🔴' : safe.includes('SAFE') ? '🟢' : '🟡';
        let md = '';
        if (data.description || data.image_description) md += `**Image Description**\n${data.description || data.image_description}\n\n`;
        if (data.area || data.area_identified) md += `**Area / Location**\n${data.area || data.area_identified}\n\n`;
        if (data.activity || data.activity_identified) md += `**Activity Identified**\n${data.activity || data.activity_identified}\n\n`;
        if (data.objects_detected) {
            const objs = Array.isArray(data.objects_detected) ? data.objects_detected.join(', ') : data.objects_detected;
            md += `**Objects Detected**\n${objs}\n\n`;
        }
        if (data.person_count !== undefined && data.person_count !== null) md += `**Person Count**\n${data.person_count}\n\n`;
        if (safe) md += `**Safety Condition**\n${safeEmoji} ${data.safety_condition || data.status}\n\n`;
        if (data.reasoning || data.reason || data.analysis) md += `**Reasoning / Analysis**\n${data.reasoning || data.reason || data.analysis}\n\n`;
        return md.trim();
    };

    const sendMessage = async (text) => {
        if (!text.trim() || isLoading) return;
        const userMessage = { id: Date.now(), type: 'user', content: text.trim(), timestamp: new Date() };
        const aiMessageId = Date.now() + 1;
        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setStreamingMessageId(aiMessageId);
        const aiMessage = { id: aiMessageId, type: 'assistant', content: '', sources: [], confidence: null, processingTime: null, timestamp: new Date(), isStreaming: true };
        setMessages((prev) => [...prev, aiMessage]);

        try {
            await api.queryStream(text.trim(), {
                includeSource: true,
                sessionId: activeChatId,
                sourceType,
                onToken: (token) => {
                    setMessages((prev) => prev.map((msg) => msg.id === aiMessageId ? { ...msg, content: msg.content + token } : msg));
                },
                onDone: (metadata) => {
                    setMessages((prev) => prev.map((msg) => msg.id === aiMessageId ? { ...msg, isStreaming: false, sources: metadata.sources || [], confidence: metadata.confidence, processingTime: metadata.processing_time } : msg));
                    setIsLoading(false);
                    setStreamingMessageId(null);
                    refreshChatTitles();
                },
                onError: (error) => {
                    setMessages((prev) => prev.map((msg) => msg.id === aiMessageId ? { ...msg, content: msg.content || `❌ Error: ${error.message}`, isStreaming: false, type: msg.content ? 'assistant' : 'error' } : msg));
                    setIsLoading(false);
                    setStreamingMessageId(null);
                },
            });
        } catch (error) {
            console.error('Chat Error:', error);
            setMessages((prev) => prev.map((msg) => msg.id === aiMessageId ? { ...msg, content: `❌ Error: ${error.message}`, isStreaming: false, type: 'error' } : msg));
            setIsLoading(false);
            setStreamingMessageId(null);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        await sendMessage(input);
    };

    const toggleRecording = async () => {
        if (isRecording) {
            if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
        } else {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const mediaRecorder = new MediaRecorder(stream);
                mediaRecorderRef.current = mediaRecorder;
                audioChunksRef.current = [];
                mediaRecorder.ondataavailable = (event) => { if (event.data.size > 0) audioChunksRef.current.push(event.data); };
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/mp3' });
                    const audioFile = new File([audioBlob], `recording_${Date.now()}.mp3`, { type: 'audio/mp3' });
                    stream.getTracks().forEach(track => track.stop());
                    setIsRecording(false);
                    await transcribeAudio(audioFile);
                };
                mediaRecorder.start();
                setIsRecording(true);
            } catch (err) {
                console.error("Error accessing microphone:", err);
                alert("Could not access microphone.");
            }
        }
    };

    const transcribeAudio = async (file) => {
        try {
            const formData = new FormData();
            formData.append('file', file);
            setInput("🎙️ Transcribing audio...");
            setIsLoading(true);
            const response = await fetch('https://aiuat.mysetu.com/speech_to_text_api/transcribe', { method: 'POST', body: formData });
            if (!response.ok) throw new Error(`API error: ${response.status}`);
            const data = await response.json();
            let transcribedText = data.transcribed_text || data.text || (typeof data === 'string' ? data : JSON.stringify(data));
            setInput("");
            setIsLoading(false);
            if (transcribedText.trim()) await sendMessage(transcribedText);
        } catch (error) {
            console.error("Transcription failed", error);
            setInput("");
            setIsLoading(false);
            alert("Failed to transcribe audio.");
        }
    };

    const canChat = systemHealth?.vector_store_initialized && systemHealth?.ollama_available;

    return (
        <div className="chat-interface-container">
            <div className={`chat-history-sidebar ${isHistoryOpen ? '' : 'collapsed'}`}>
                <button className="new-chat-btn" onClick={handleNewChat}>＋ New Chat</button>
                <div style={{ flex: 1, overflowY: 'auto', padding: '4px 8px 8px' }}>
                    {chats.map(chat => (
                        <div key={chat.id} className={`chat-item ${activeChatId === chat.id ? 'active' : ''}`} onClick={() => setActiveChatId(chat.id)}>
                            <span className="chat-title">{chat.title}</span>
                            <button className="delete-btn" onClick={(e) => handleDeleteChat(chat.id, e)} title="Delete Chat">🗑</button>
                        </div>
                    ))}
                </div>
            </div>

            <div className="chat-interface">
                <div className="chat-header">
                    <div className="chat-header-top">
                        <div className="chat-header-title">
                            <button
                                className="history-toggle-btn"
                                onClick={() => setIsHistoryOpen(v => !v)}
                                title={isHistoryOpen ? 'Hide chat list' : 'Show chat list'}
                                aria-label="Toggle chat list"
                            >
                                {isHistoryOpen ? '⟨' : '☰'}
                            </button>
                            <h2>💬 Knowledge Chat</h2>
                        </div>
                        <div className="source-selector">
                            {['all', 'documents', 'databases'].map(type => (
                                <button key={type} className={`source-toggle ${sourceType === type ? 'active' : ''}`} onClick={() => setSourceType(type)}>
                                    {type === 'all' ? 'All' : type === 'documents' ? 'PDFs' : 'DBs'}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {!canChat && (
                    <div className="chat-warning">
                        <div className="warning-icon">⚙️</div>
                        <div className="warning-content">
                            <h3>System Configuration Pending</h3>
                            <p>{systemHealth?.detail || 'Please ensure Ollama is running and knowledge base is initialized.'}</p>
                            <div className="warning-actions">
                                <button className="btn-retry" onClick={checkSystemHealth}>🔄 Refresh Status</button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="chat-messages">
                    {messages.length === 0 && (
                        <div className="empty-state animate-fade-in">
                            <div className="empty-state-card">
                                <div className="empty-icon">🤖</div>
                                <h3>Knowledge Assistant Ready</h3>
                                <p>Ask me anything about your uploaded documents or connected databases.</p>
                            </div>
                        </div>
                    )}

                    {messages.map((message) => (
                        <div key={message.id} className={`message message-${message.type}`}>
                            <div className="message-avatar">{message.type === 'user' ? '👤' : message.type === 'error' ? '❌' : '🤖'}</div>
                            <div className="message-content">
                                {message.type === 'assistant' || message.type === 'error' ? (
                                    <div className="message-text">
                                        {message.imageAnalysisData ? (
                                            <SafetyReport data={message.imageAnalysisData} />
                                        ) : (
                                            <div className="assistant-card">
                                                {message.isLoading ? (
                                                    <div className="typing-indicator"><span></span><span></span><span></span><em>Analyzing...</em></div>
                                                ) : (
                                                    <div className="markdown-body">
                                                        <ReactMarkdown>{message.content}</ReactMarkdown>
                                                        {message.isStreaming && <span className="streaming-cursor" />}
                                                    </div>
                                                )}
                                                {message.sources && message.sources.length > 0 && !message.isStreaming && (
                                                    <div className="message-sources">
                                                        <div className="sources-header"><span className="sources-icon">📚</span><span className="sources-title">Sources ({message.sources.length})</span></div>
                                                        <div className="sources-list">
                                                            {message.sources.map((source, idx) => (
                                                                <div key={idx} className="source-item">
                                                                    <div className="source-name">📄 {source.document_name} {source.page_number && `· p.${source.page_number}`}</div>
                                                                    <div className="source-relevance">{Math.round(source.relevance_score * 100)}% match</div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                                {message.confidence !== undefined && message.confidence !== null && !message.isStreaming && (
                                                    <div className="message-metadata">
                                                        <span className="metadata-item">
                                                            <span className={`confidence-dot ${message.confidence >= 0.7 ? '' : message.confidence >= 0.4 ? 'medium' : 'low'}`} />
                                                            Confidence: {Math.round(message.confidence * 100)}%
                                                        </span>
                                                        {message.processingTime && <span className="metadata-item">⏱ {message.processingTime}s</span>}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="message-text">
                                        {message.imagePreview && (
                                            <img
                                                src={message.imagePreview}
                                                alt="User upload"
                                                className="message-image-preview"
                                                title="Click to view full size"
                                                onClick={() => window.open(message.imagePreview, '_blank', 'noopener')}
                                            />
                                        )}
                                        {/* Hide raw Smart String prefix if present */}
                                        {message.content && !message.content.startsWith('[USER_IMAGE]') ? message.content : ''}
                                    </div>
                                )}
                                <div className="message-timestamp">{message.timestamp.toLocaleTimeString()}</div>
                            </div>
                        </div>
                    ))}

                    {isLoading && !streamingMessageId && !isImageLoading && (
                        <div className="message message-assistant" style={{ marginBottom: '20px' }}>
                            <div className="message-avatar">🤖</div>
                            <div className="message-content">
                                <div className="typing-indicator"><span></span><span></span><span></span><em style={{ marginLeft: '10px', fontSize: '0.9em', color: '#888' }}>Searching knowledge base...</em></div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form className="chat-input-form" onSubmit={handleSubmit}>
                    <input type="file" ref={imageInputRef} accept="image/*" style={{ display: 'none' }}
                        onChange={(e) => { handleImageFileSelect(e.target.files[0]); setShowImageModal(true); e.target.value = ''; }} />
                    <button type="button" className="chat-image-btn" disabled={isLoading} onClick={() => setShowImageModal(true)}>+</button>
                    <input type="text" className="chat-input" placeholder={canChat ? "Ask a question..." : "System not ready..."} value={input} onChange={(e) => setInput(e.target.value)} disabled={!canChat || isLoading || isRecording} />
                    <button type="button" className={`chat-mic-btn ${isRecording ? 'recording' : ''}`} disabled={!canChat || (isLoading && !isRecording)} onClick={toggleRecording}>🎙️</button>
                    <button type="submit" className="chat-submit" disabled={!canChat || !input.trim() || isLoading}>
                        {isLoading && !isRecording && !input.includes('🎙️') ? <div className="spinner"></div> : '➤'}
                    </button>
                </form>

                {showImageModal && (
                    <div className="img-modal-overlay" onClick={closeImageModal}>
                        <div className="img-modal" onClick={e => e.stopPropagation()}>
                            <div className="img-modal-header"><h3>🔍 Analyze Image</h3><button className="img-modal-close" onClick={closeImageModal}>✕</button></div>
                            <div className="img-modal-body">
                                {!selectedImage ? (
                                    <div className={`img-dropzone ${isDragging ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onDrop={handleImageDrop} onClick={() => imageInputRef.current?.click()}>
                                        <div className="img-dropzone-icon">🖼️</div><p className="img-dropzone-title">Drop an image here</p><p className="img-dropzone-sub">or click to browse</p>
                                    </div>
                                ) : (
                                    <div className="img-preview-wrap"><img src={selectedImage.previewUrl} alt="preview" className="img-preview" /><button className="img-preview-remove" onClick={() => setSelectedImage(null)}>✕ Remove</button></div>
                                )}
                            </div>
                            <div className="img-modal-footer">
                                <button className="img-btn-cancel" onClick={closeImageModal}>Cancel</button>
                                <button className="img-btn-send" disabled={!selectedImage} onClick={sendImageMessage}>🔍 Analyze Image</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

function SafetyReport({ data }) {
    if (!data) return null;
    const safety = (data.safety_condition || '').toUpperCase();
    const isUnsafe = safety.includes('UNSAFE');
    const isSafe = safety.includes('SAFE') && !isUnsafe;
    const badgeClass = isSafe ? 'safe' : isUnsafe ? 'unsafe' : 'partial';
    const reportIcon = isSafe ? '🛡️' : isUnsafe ? '⚠️' : '⚡';

    return (
        <div className="safety-report-card">
            <div className={`safety-report-header ${badgeClass}`}>
                <div className="safety-status-badge"><span className="badge-icon">{reportIcon}</span>{data.safety_condition || 'Unknown'}</div>
                <p className="safety-image-desc">{data.image_description || data.description || "Image Safety Analysis"}</p>
            </div>
            <div className="safety-metrics-grid">
                <div className="metric-item"><div className="metric-label">📍 Area</div><div className="metric-value">{data.area || 'Unknown'}</div></div>
                <div className="metric-item"><div className="metric-label">🏃 Activity</div><div className="metric-value">{data.activity || 'Unknown'}</div></div>
                <div className="metric-item"><div className="metric-label">👥 Persons</div><div className="metric-value">{data.number_of_persons || '0'}</div></div>
            </div>
            <div className="safety-section">
                <div className="section-title">🛡️ PPE Detection</div>
                <div className="ppe-pill-container">{(data.detected_ppe || []).length > 0 ? data.detected_ppe.map((item, idx) => <span key={idx} className="ppe-pill">{item}</span>) : <span className="no-data">No PPE detected</span>}</div>
            </div>
            {data.detailed_report?.potential_hazards && (
                <div className="safety-section-alert hazards">
                    <div className="alert-title">🔥 Potential Hazards</div>
                    <ul className="alert-list">{data.detailed_report.potential_hazards.map((item, idx) => <li key={idx}>{item}</li>)}</ul>
                </div>
            )}
            {data.detailed_report?.recommended_actions && (
                <div className="safety-section-alert actions">
                    <div className="alert-title">✅ Recommended Actions</div>
                    <ul className="alert-list">{data.detailed_report.recommended_actions.map((item, idx) => <li key={idx}>{item}</li>)}</ul>
                </div>
            )}
            {(data.reasoning_points || data.reasoning) && (
                <div className="safety-section reasoning">
                    <div className="section-title">🧠 Reasoning & Analysis</div>
                    <div className="reasoning-list">{(Array.isArray(data.reasoning_points) ? data.reasoning_points : [data.reasoning]).map((point, idx) => <div key={idx} className="reasoning-item"><ReactMarkdown>{point}</ReactMarkdown></div>)}</div>
                </div>
            )}
        </div>
    );
}

export default ChatInterface;
