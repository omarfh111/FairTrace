
import { ChatCitation } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface StreamingAnswerProps {
    status: 'idle' | 'searching' | 'analyzing' | 'streaming' | 'citations' | 'done';
    statusMessage: string;
    streamedText: string;
    citations: ChatCitation[];
    metadata: any | null;
    onFollowUpClick: (question: string) => void;
}

export function StreamingAnswer({ status, statusMessage, streamedText, citations }: StreamingAnswerProps) {

    return (
        <div className="streaming-container p-4 bg-slate-900/50 rounded-lg border border-slate-700/50 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-4 text-slate-400 text-sm">
                {status !== 'done' && <Loader2 className="animate-spin" size={16} />}
                <span className="uppercase tracking-wider text-xs font-semibold text-blue-400">
                    {statusMessage || "Traitement..."}
                </span>
            </div>

            {streamedText && (
                <div className="prose prose-invert prose-sm max-w-none">
                    <p className="text-slate-200 leading-relaxed whitespace-pre-wrap animate-pulse-short">
                        {streamedText}
                        {status === 'streaming' && <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse" />}
                    </p>
                </div>
            )}

            {citations.length > 0 && (
                <div className="grid grid-cols-1 gap-2 mt-4 pt-4 border-t border-slate-700/50">
                    {citations.map((cit, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs text-slate-400 bg-slate-800/50 p-2 rounded">
                            <span className="bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded text-[10px] font-bold">
                                {cit.article}
                            </span>
                            <span className="truncate flex-1 italic opacity-70">
                                "...{cit.excerpt.substring(0, 50)}..."
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
