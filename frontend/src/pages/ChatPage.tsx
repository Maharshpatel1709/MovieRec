import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Send, Sparkles, RotateCcw } from 'lucide-react'
import { ChatBubble, SuggestionChips } from '../components/ChatBubble'
import { ragApi } from '../api/client'
import type { ChatMessage, Movie, Reasoning } from '../api/client'
import clsx from 'clsx'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  recommendations?: Movie[]
  reasoning?: Reasoning
}

const INITIAL_SUGGESTIONS = [
  "Recommend sci-fi movies like Interstellar",
  "What are some feel-good comedies?",
  "Movies directed by Christopher Nolan",
  "Best thrillers from the 90s",
]

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [suggestions, setSuggestions] = useState(INITIAL_SUGGESTIONS)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    try {
      const history: ChatMessage[] = messages.map(m => ({
        role: m.role,
        content: m.content,
      }))

      const response = await ragApi.chat(content, history)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        recommendations: response.recommendations,
        reasoning: response.reasoning,
      }

      setMessages(prev => [...prev, assistantMessage])
      setSuggestions(response.suggestions)
    } catch (error) {
      console.error('Chat error:', error)
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion)
  }

  const clearChat = () => {
    setMessages([])
    setSuggestions(INITIAL_SUGGESTIONS)
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Chat Container */}
      <div className="flex-1 overflow-hidden flex flex-col max-w-6xl mx-auto w-full px-4">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="max-w-md"
              >
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cinema-500/20 to-cinema-600/20 flex items-center justify-center mx-auto mb-6">
                  <Sparkles className="w-10 h-10 text-cinema-400" />
                </div>
                <h2 className="font-display text-2xl font-bold text-white mb-3">
                  Movie Assistant
                </h2>
                <p className="text-slate-400 mb-8">
                  Ask me anything about movies! I can recommend films based on your mood, 
                  find similar movies to ones you love, or help you discover hidden gems.
                </p>
                <SuggestionChips
                  suggestions={suggestions}
                  onSelect={handleSuggestionClick}
                />
              </motion.div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <ChatBubble
                  key={message.id}
                  message={message.content}
                  isUser={message.role === 'user'}
                  recommendations={message.recommendations}
                  reasoning={message.reasoning}
                />
              ))}
              
              {isTyping && (
                <ChatBubble
                  message=""
                  isUser={false}
                  isTyping
                />
              )}
              
              {/* Suggestions after response */}
              {!isTyping && messages.length > 0 && suggestions.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="pt-4"
                >
                  <p className="text-xs text-slate-500 mb-2">Try asking:</p>
                  <SuggestionChips
                    suggestions={suggestions}
                    onSelect={handleSuggestionClick}
                  />
                </motion.div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-slate-800">
          {messages.length > 0 && (
            <div className="flex justify-end mb-2">
              <button
                onClick={clearChat}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-400 transition-colors"
              >
                <RotateCcw className="w-3 h-3" />
                Clear chat
              </button>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="relative">
            <div className="glass rounded-2xl border border-slate-700/50 focus-within:border-cinema-500/50 transition-colors overflow-hidden">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about movies..."
                rows={1}
                className="w-full px-4 py-3 pr-14 bg-transparent text-white placeholder-slate-500 resize-none focus:outline-none"
                style={{ minHeight: '52px', maxHeight: '200px' }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                className={clsx(
                  'absolute right-2 bottom-2 p-2.5 rounded-xl transition-all',
                  input.trim() && !isTyping
                    ? 'bg-gradient-to-r from-cinema-500 to-cinema-600 text-white hover:from-cinema-600 hover:to-cinema-700'
                    : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                )}
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>
          
          <p className="text-center text-xs text-slate-500 mt-3">
            Powered by RAG + Neo4j Knowledge Graph
          </p>
        </div>
      </div>
    </div>
  )
}

