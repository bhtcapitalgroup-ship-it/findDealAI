import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bot, Send, MessageSquare, Phone, Mail, AlertTriangle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import api from '../lib/api';

interface Conversation { id: string; tenantName: string; unit: string; lastMessage: string; time: string; unread: number; channel: 'sms' | 'email' | 'portal'; escalated: boolean; }
interface Message { id: string; sender: 'tenant' | 'ai' | 'landlord'; text: string; time: string; }

const mockConversations: Conversation[] = [
  { id: '1', tenantName: 'Sarah Johnson', unit: '1A - Oak Manor', lastMessage: 'Thank you! When can I expect the new lease?', time: '2026-03-16T16:20:00Z', unread: 2, channel: 'sms', escalated: false },
  { id: '2', tenantName: 'Mike Chen', unit: '1B - Oak Manor', lastMessage: 'The plumber came but the leak is still there', time: '2026-03-16T15:45:00Z', unread: 1, channel: 'sms', escalated: true },
  { id: '3', tenantName: 'Emma Wilson', unit: '3B - Oak Manor', lastMessage: 'I sent the payment via Venmo yesterday', time: '2026-03-16T14:30:00Z', unread: 0, channel: 'email', escalated: false },
  { id: '4', tenantName: 'David Kim', unit: '3A - Oak Manor', lastMessage: 'Can I have a guest stay for 2 weeks?', time: '2026-03-16T12:00:00Z', unread: 0, channel: 'portal', escalated: false },
  { id: '5', tenantName: 'Robert Garcia', unit: 'A - Elm Street', lastMessage: 'The noise from upstairs is unbearable', time: '2026-03-16T10:15:00Z', unread: 3, channel: 'sms', escalated: true },
  { id: '6', tenantName: 'Nina Patel', unit: 'B - Elm Street', lastMessage: 'Thanks for the quick response about parking', time: '2026-03-15T18:30:00Z', unread: 0, channel: 'portal', escalated: false },
  { id: '7', tenantName: 'Amy Taylor', unit: '4B - Oak Manor', lastMessage: 'My rent will be late this month, sorry', time: '2026-03-15T16:00:00Z', unread: 0, channel: 'sms', escalated: false },
];

const mockMessages: Record<string, Message[]> = {
  '1': [
    { id: 'm1', sender: 'tenant', text: 'Hi, I was wondering about my lease renewal. It expires in August.', time: '2026-03-16T15:00:00Z' },
    { id: 'm2', sender: 'ai', text: 'Hi Sarah! Thanks for reaching out about your lease renewal. Your current lease for Unit 1A at Oak Manor expires on August 31, 2026. We would love to have you stay! I can prepare a renewal offer for you. Would you prefer a 12-month or month-to-month renewal?', time: '2026-03-16T15:00:15Z' },
    { id: 'm3', sender: 'tenant', text: "I'd like a 12-month renewal. Will there be a rent increase?", time: '2026-03-16T15:30:00Z' },
    { id: 'm4', sender: 'ai', text: "Great choice! For a 12-month renewal, there would be a 3% increase, bringing your rent from $1,800 to $1,854/month. This is below the current market rate for comparable units in the area. I'll prepare the renewal documents for your review.", time: '2026-03-16T15:30:20Z' },
    { id: 'm5', sender: 'tenant', text: 'Thank you! When can I expect the new lease?', time: '2026-03-16T16:20:00Z' },
    { id: 'm6', sender: 'ai', text: "I'll have the renewal lease ready for your review within 24 hours. You'll receive it via email and can sign electronically through the tenant portal. Is there anything else I can help with?", time: '2026-03-16T16:20:15Z' },
  ],
  '2': [
    { id: 'm1', sender: 'tenant', text: 'The kitchen sink is still leaking even after the plumber visit.', time: '2026-03-16T14:00:00Z' },
    { id: 'm2', sender: 'ai', text: "I'm sorry to hear the leak persists, Mike. I've flagged this as a follow-up maintenance request with high priority. Let me escalate this to the property manager for immediate attention.", time: '2026-03-16T14:00:20Z' },
    { id: 'm3', sender: 'tenant', text: 'The plumber came but the leak is still there', time: '2026-03-16T15:45:00Z' },
    { id: 'm4', sender: 'ai', text: "I understand your frustration. I've escalated this to the landlord for direct review. In the meantime, please place a bucket under the leak. Someone will contact you within 2 hours.", time: '2026-03-16T15:45:15Z' },
  ],
};

const channelIcon = { sms: Phone, email: Mail, portal: MessageSquare };

export default function Messages() {
  const [selectedId, setSelectedId] = useState<string>('1');
  const [inputText, setInputText] = useState('');

  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => { const res = await api.get('/conversations'); return res.data; },
    placeholderData: mockConversations,
  });

  const convos: Conversation[] = conversations ?? mockConversations;
  const selected = convos.find((c) => c.id === selectedId);
  const messages = mockMessages[selectedId] || [];

  const handleSend = () => { if (!inputText.trim()) return; setInputText(''); };

  return (
    <div className="h-[calc(100vh-7rem)]">
      <div className="flex h-full bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
        <div className="w-80 border-r border-zinc-200 flex flex-col shrink-0">
          <div className="p-4 border-b border-zinc-200"><h2 className="text-lg font-semibold text-zinc-900">Messages</h2><p className="text-xs text-zinc-500 mt-0.5">{convos.length} conversations</p></div>
          <div className="flex-1 overflow-y-auto">
            {convos.map((convo) => { const ChannelIcon = channelIcon[convo.channel]; return (
              <button key={convo.id} onClick={() => setSelectedId(convo.id)} className={clsx('w-full text-left px-4 py-3 border-b border-zinc-100 hover:bg-zinc-50 transition-colors', selectedId === convo.id && 'bg-blue-50 border-l-2 border-l-blue-600', convo.escalated && 'bg-amber-50/50')}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2"><span className="text-sm font-semibold text-zinc-900">{convo.tenantName}</span>{convo.escalated && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}</div>
                  <div className="flex items-center gap-1.5"><ChannelIcon className="w-3 h-3 text-zinc-400" /><span className="text-xs text-zinc-400">{formatDistanceToNow(new Date(convo.time), { addSuffix: false })}</span></div>
                </div>
                <p className="text-xs text-zinc-500 mb-0.5">{convo.unit}</p>
                <p className="text-xs text-zinc-600 truncate">{convo.lastMessage}</p>
                {convo.unread > 0 && <span className="inline-flex items-center justify-center mt-1 w-5 h-5 bg-blue-600 text-white text-[10px] font-bold rounded-full">{convo.unread}</span>}
              </button>
            ); })}
          </div>
        </div>

        <div className="flex-1 flex flex-col">
          {selected ? (<>
            <div className="px-5 py-3 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2"><h3 className="font-semibold text-zinc-900">{selected.tenantName}</h3>{selected.escalated && <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-semibold rounded-full"><AlertTriangle className="w-3 h-3" />Escalated</span>}</div>
                <p className="text-xs text-zinc-500">{selected.unit}</p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={clsx('flex gap-2', msg.sender === 'tenant' ? 'justify-end' : 'justify-start')}>
                  {msg.sender !== 'tenant' && <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-1', msg.sender === 'ai' ? 'bg-purple-100' : 'bg-blue-100')}>{msg.sender === 'ai' ? <Bot className="w-3.5 h-3.5 text-purple-600" /> : <span className="text-xs font-bold text-blue-600">Y</span>}</div>}
                  <div className={clsx('max-w-[70%] rounded-2xl px-4 py-2.5 text-sm', msg.sender === 'tenant' ? 'bg-blue-600 text-white rounded-tr-sm' : msg.sender === 'ai' ? 'bg-zinc-100 text-zinc-800 rounded-tl-sm' : 'bg-blue-50 text-zinc-800 rounded-tl-sm border border-blue-200')}>
                    {msg.sender === 'ai' && <span className="text-[10px] font-semibold text-purple-600 uppercase tracking-wider block mb-1">AI Assistant</span>}
                    {msg.sender === 'landlord' && <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider block mb-1">You (Override)</span>}
                    <p className="leading-relaxed">{msg.text}</p>
                    <p className={clsx('text-[10px] mt-1', msg.sender === 'tenant' ? 'text-blue-200' : 'text-zinc-400')}>{formatDistanceToNow(new Date(msg.time), { addSuffix: true })}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="px-5 py-3 border-t border-zinc-200">
              <div className="flex items-center gap-2">
                <input type="text" value={inputText} onChange={(e) => setInputText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} placeholder="Type a message to override AI response..." className="flex-1 px-4 py-2.5 text-sm bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                <button onClick={handleSend} className="p-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"><Send className="w-4 h-4" /></button>
              </div>
              <p className="text-[10px] text-zinc-400 mt-1.5">Your message will be sent directly to the tenant, bypassing AI</p>
            </div>
          </>) : (
            <div className="flex-1 flex items-center justify-center text-zinc-400"><div className="text-center"><MessageSquare className="w-12 h-12 mx-auto mb-3 text-zinc-300" /><p className="text-sm">Select a conversation to view messages</p></div></div>
          )}
        </div>
      </div>
    </div>
  );
}
