/**
 * RegulationChatbot - Premium Glassmorphism Chatbot UI
 * 
 * Updated Features:
 * - Violet/Purple Theme
 * - Fullscreen/Expand Capability
 * - Header Icons (Search, Minimize, Maximize)
 * - Online Status Indicator
 * - Enhanced Input Layout
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
    sendStreamingChatMessage,
    getChatSuggestions,
    clearChatHistory,
    ChatResponse,
    ChatCitation,
    StreamingCallbacks,
} from '../lib/api';
import './RegulationChatbot.css';
import { RegulationResponse } from './regulation/RegulationResponse';
import { StreamingAnswer } from './regulation/StreamingAnswer';

// --- Icons ---
const BookIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
    </svg>
);

const BookIconSmall = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
    </svg>
);

const SendIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
);

const CloseIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
);

const SearchIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
);

const MinusIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
);

const MaximizeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line>
    </svg>
);

const MinimizeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
    </svg>
);

const RefreshIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" /><path d="M16 21h5v-5" />
    </svg>
);

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: (ChatCitation & { index: number })[];
    timestamp: Date;
    isLoading?: boolean;
    isStreaming?: boolean;
    // Streaming state
    streamingStatus?: 'idle' | 'searching' | 'analyzing' | 'streaming' | 'citations' | 'done';
    streamingStatusMessage?: string;
    streamingMetadata?: {
        confidence: 'LOW' | 'MEDIUM' | 'HIGH';
        processingTimeMs: number;
        citationsCount: number;
        followUpQuestions: string[];
    };
    // Store raw API response for Generative UI rendering
    rawResponse?: ChatResponse;
}

export function RegulationChatbot() {
    const [isOpen, setIsOpen] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | undefined>();
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);

    // Add refs for scrolling
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Load initial suggestions
    useEffect(() => {
        if (isOpen && suggestions.length === 0) {
            getChatSuggestions().then(setSuggestions).catch(() => { });
        }
    }, [isOpen]);

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen) {
            inputRef.current?.focus();
        }
    }, [isOpen]);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                setIsOpen(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen]);

    const handleSend = useCallback(() => {
        const message = inputValue.trim();
        if (!message || isLoading) return;

        setError(null);
        setInputValue('');

        // Add user message
        const userMessage: Message = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: message,
            timestamp: new Date(),
        };

        // Add streaming message
        const streamingMsgId = `streaming-${Date.now()}`;
        const streamingMessage: Message = {
            id: streamingMsgId,
            role: 'assistant',
            content: '',
            citations: [],
            timestamp: new Date(),
            isStreaming: true,
            streamingStatus: 'idle',
            streamingStatusMessage: '',
        };

        setMessages(prev => [...prev, userMessage, streamingMessage]);
        setIsLoading(true);

        // Use streaming API
        const callbacks: StreamingCallbacks = {
            onStatus: (status, msg) => {
                setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                        ? { ...m, streamingStatus: status as Message['streamingStatus'], streamingStatusMessage: msg }
                        : m
                ));
            },
            onToken: (token) => {
                setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                        ? { ...m, content: m.content + token, streamingStatus: 'streaming' }
                        : m
                ));
            },
            onCitation: (citation) => {
                setMessages(prev => prev.map(m =>
                    m.id === streamingMsgId
                        ? { ...m, citations: [...(m.citations || []), citation], streamingStatus: 'citations' }
                        : m
                ));
            },
            onDone: (metadata) => {
                if (!conversationId) {
                    setConversationId(metadata.conversation_id);
                }
                setMessages(prev => prev.map(m => {
                    if (m.id === streamingMsgId) {
                        // Construct the full response object for the Generative UI
                        const fullResponse: ChatResponse = {
                            answer: m.content, // The accumulated content
                            citations: m.citations || [],
                            confidence: metadata.confidence,
                            follow_up_questions: metadata.follow_up_questions,
                            conversation_id: metadata.conversation_id,
                            processing_time_ms: metadata.processing_time_ms,
                            source_pages: metadata.source_pages || []
                        };

                        return {
                            ...m,
                            isStreaming: false,
                            streamingStatus: undefined, // Clear status to switch to RegulationResponse renderer
                            rawResponse: fullResponse
                        };
                    }
                    return m;
                }));
                if (metadata.follow_up_questions?.length) {
                    setSuggestions(metadata.follow_up_questions);
                }
                setIsLoading(false);
            },
            onError: (error) => {
                setMessages(prev => prev.filter(m => m.id !== streamingMsgId));
                setError(error);
                setIsLoading(false);
            }
        };

        sendStreamingChatMessage(message, conversationId, callbacks);
    }, [inputValue, isLoading, conversationId]);

    const handleSuggestionClick = (suggestion: string) => {
        setInputValue(suggestion);
        // focus input
        setTimeout(() => inputRef.current?.focus(), 0);
    };

    const handleClearHistory = async () => {
        if (conversationId) {
            await clearChatHistory(conversationId);
        }
        setMessages([]);
        setConversationId(undefined);
        setSuggestions([]);
        getChatSuggestions().then(setSuggestions).catch(() => { });
    };

    const toggleExpand = () => {
        setIsExpanded(!isExpanded);
    };

    return (
        <>
            {/* Floating Toggle Button */}
            <button
                className={`regulation-chat-toggle ${isOpen ? 'hidden' : ''}`}
                onClick={() => setIsOpen(true)}
                aria-label="Ouvrir le chatbot réglementation"
                title="Agent Réglementation Bancaire"
            >
                <div className="toggle-icon">
                    <BookIcon />
                </div>
                <span className="toggle-label font-medium">Agent Réglementation</span>
                <div className="toggle-pulse" />
            </button>

            {/* Chat Panel */}
            <div className={`regulation-chat-panel ${isOpen ? 'open' : ''} ${isExpanded ? 'expanded' : ''}`}>

                {/* Header */}
                <div className="chat-header">
                    <div className="header-left">
                        <div className="agent-icon-container">
                            <BookIconSmall />
                        </div>
                        <div className="header-info">
                            <h3>Agent Réglementation</h3>
                            <div className="status-indicator">
                                <span className="status-dot"></span>
                                <span>En ligne</span>
                                <span className="text-gray-500">•</span>
                                <span>BCT</span>
                            </div>
                        </div>
                    </div>

                    <div className="header-actions">
                        <button className="header-btn" title="Rechercher">
                            <SearchIcon />
                        </button>
                        <button
                            className="header-btn"
                            onClick={() => setIsOpen(false)}
                            title="Réduire"
                        >
                            <MinusIcon />
                        </button>
                        <button
                            className="header-btn"
                            onClick={toggleExpand}
                            title={isExpanded ? "Réduire" : "Agrandir"}
                        >
                            {isExpanded ? <MinimizeIcon /> : <MaximizeIcon />}
                        </button>
                        <button
                            className="header-btn close-btn"
                            onClick={() => setIsOpen(false)}
                            title="Fermer"
                        >
                            <CloseIcon />
                        </button>
                    </div>
                </div>

                {/* Messages */}
                <div className="chat-messages">
                    {messages.length === 0 && (
                        <div className="welcome-message">
                            <div className="welcome-icon-large">
                                <BookIcon />
                            </div>
                            <h4>Agent Réglementation</h4>
                            <p>
                                Expert en réglementation bancaire BCT.
                                <br />Posez vos questions sur les circulaires et lois.
                            </p>
                        </div>
                    )}

                    {messages.map((msg) => (
                        <div key={msg.id}>
                            {/* User Messages - Keep as chat bubbles */}
                            {msg.role === 'user' && (
                                <div className={`message user`}>
                                    <div className="message-content">
                                        <div className="message-text">{msg.content}</div>
                                        <div className="message-time">
                                            {msg.timestamp.toLocaleTimeString('fr-FR', {
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Assistant Messages - Generative UI */}
                            {msg.role === 'assistant' && (
                                <>
                                    {msg.isStreaming || msg.streamingStatus ? (
                                        /* Use StreamingAnswer for streaming responses */
                                        <StreamingAnswer
                                            status={msg.streamingStatus || 'idle'}
                                            statusMessage={msg.streamingStatusMessage || ''}
                                            streamedText={msg.content}
                                            citations={msg.citations || []}
                                            metadata={msg.streamingMetadata || null}
                                            onFollowUpClick={handleSuggestionClick}
                                        />
                                    ) : msg.isLoading ? (
                                        <div className="message assistant loading">
                                            <div className="message-avatar">
                                                <BookIconSmall />
                                            </div>
                                            <div className="message-content">
                                                <div className="typing-indicator">
                                                    <span></span>
                                                    <span></span>
                                                    <span></span>
                                                </div>
                                            </div>
                                        </div>
                                    ) : msg.rawResponse ? (
                                        /* Use Generative UI for responses with raw data */
                                        <RegulationResponse
                                            response={msg.rawResponse}
                                            onFollowUpClick={handleSuggestionClick}
                                        />
                                    ) : (
                                        /* Fallback for legacy messages without rawResponse */
                                        <div className="message assistant">
                                            <div className="message-avatar">
                                                <BookIconSmall />
                                            </div>
                                            <div className="message-content">
                                                <div className="message-text">{msg.content}</div>
                                                <div className="message-time">
                                                    {msg.timestamp.toLocaleTimeString('fr-FR', {
                                                        hour: '2-digit',
                                                        minute: '2-digit'
                                                    })}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Error */}
                {error && (
                    <div className="chat-error">
                        ⚠️ {error}
                        <button onClick={() => setError(null)}>×</button>
                    </div>
                )}

                {/* Suggestions */}
                {suggestions.length > 0 && !isLoading && (
                    <div className="chat-suggestions">
                        {suggestions.slice(0, 3).map((suggestion, idx) => (
                            <button
                                key={idx}
                                className="suggestion-chip"
                                onClick={() => handleSuggestionClick(suggestion)}
                            >
                                {suggestion.length > 40
                                    ? suggestion.slice(0, 40) + '...'
                                    : suggestion
                                }
                            </button>
                        ))}
                    </div>
                )}

                {/* Input */}
                <div className="chat-input-container">
                    <div className="input-wrapper">
                        <input
                            ref={inputRef}
                            type="text"
                            className="chat-input"
                            placeholder="Posez votre question sur la réglementation..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSend();
                                }
                            }}
                            disabled={isLoading}
                        />
                        <button
                            className="send-btn"
                            onClick={handleSend}
                            disabled={!inputValue.trim() || isLoading}
                            title="Envoyer"
                        >
                            <SendIcon />
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

export default RegulationChatbot;
