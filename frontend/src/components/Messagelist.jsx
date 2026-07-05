export default function MessageList({ messages }) {
  return (
    <div className="chat-log">
      {messages.map((m, i) => (
        <div key={i} className={`msg ${m.role === 'human' ? 'msg-human' : 'msg-ai'}`}>
          {m.content}
        </div>
      ))}
    </div>
  );
}