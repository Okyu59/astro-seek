import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, MapPin, Calendar, Clock, Loader2, Star, Moon, Sun, RotateCcw, ChevronRight } from 'lucide-react';

// --- [Mock Data for Fallback] ---
const FALLBACK_DATA = {
  profile: { name: "User", sun_sign: "Virgo", moon_sign: "Leo", ascendant: "Sagittarius" },
  planets: [
    { name: "Sun", sign: "Virgo", "house": "10 House" },
    { name: "Moon", sign: "Leo", "house": "9 House" },
    { name: "Ascendant", sign: "Sagittarius", "house": "1 House" }
  ],
  summary: "서버 응답 지연으로 예비 데이터를 표시합니다."
};

const SUGGESTED_QUESTIONS = [
  "2026년도 월별 흐름을 예측해줘",
  "2026년도 연애운을 알려줘",
  "내 직업적 재능과 잘 맞는 분야를 알려줘"
];

// --- [Component] Interactive Starfield Background ---
const StarfieldCanvas = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let stars = [];

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = 350;
    };

    class StarParams {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2;
        this.speedX = (Math.random() * 1 - 0.5) * 0.3;
        this.speedY = (Math.random() * 1 - 0.5) * 0.3;
        this.opacity = Math.random();
      }
      update() {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
        if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
      }
      draw() {
        ctx.fillStyle = `rgba(251, 191, 36, ${this.opacity})`;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const init = () => {
      stars = [];
      const numberOfStars = Math.floor(window.innerWidth / 15); 
      for (let i = 0; i < numberOfStars; i++) {
        stars.push(new StarParams());
      }
    };

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      stars.forEach(star => {
        star.update();
        star.draw();
      });
      animationFrameId = requestAnimationFrame(animate);
    };

    window.addEventListener('resize', () => { resizeCanvas(); init(); });
    resizeCanvas();
    init();
    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute top-0 left-0 w-full h-[350px] z-0 pointer-events-none" />;
};

// --- [UI Components] ---

const ChatMessage = ({ message, isAi, isLoading }) => (
  <div className={`flex w-full mb-6 ${isAi ? 'justify-start' : 'justify-end'} animate-fade-in-up`}>
    <div className={`flex max-w-[85%] md:max-w-[75%] ${isAi ? 'flex-row' : 'flex-row-reverse'} items-end gap-3`}>
      {isAi && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-300 to-amber-600 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(245,158,11,0.4)]">
          <Sparkles size={16} className="text-slate-900" />
        </div>
      )}
      <div className={`p-4 text-sm leading-7 shadow-lg relative ${
        isAi 
          ? 'bg-slate-900/80 border border-amber-500/20 text-slate-200 rounded-2xl rounded-bl-none' 
          : 'bg-gradient-to-r from-amber-600 to-amber-700 text-white rounded-2xl rounded-br-none font-medium'
      }`}>
        {isLoading ? (
            <div className="flex gap-1 items-center h-6">
                <div className="w-2 h-2 bg-amber-500/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-amber-500/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-amber-500/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
        ) : (
            <div className={isAi ? "font-serif tracking-wide whitespace-pre-line" : "font-sans"}>
                {message}
            </div>
        )}
      </div>
    </div>
  </div>
);

const PlanetCard = ({ planet }) => (
  <div className="group relative bg-slate-900/40 backdrop-blur-sm p-4 rounded-xl border border-amber-500/10 hover:border-amber-500/40 transition-all duration-300 w-32 shrink-0 flex flex-col items-center gap-2">
    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-inner">
        {planet.name === "Sun" ? <Sun size={16} /> : planet.name === "Moon" ? <Moon size={16} /> : <Star size={16} />}
    </div>
    <div className="text-center z-10">
        <h4 className="font-serif text-amber-100 font-bold text-sm">{planet.name}</h4>
        <p className="text-xs text-amber-200/80">{planet.sign}</p>
        <p className="text-[10px] text-slate-500 uppercase tracking-wider mt-1">{planet.house}</p>
    </div>
  </div>
);

export default function App() {
  const [step, setStep] = useState('input');
  const [loadingState, setLoadingState] = useState('idle');
  const [formData, setFormData] = useState({ date: '1995-09-22', time: '14:30', city: 'Seoul' });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [chartData, setChartData] = useState(null);
  const [isAiThinking, setIsAiThinking] = useState(false); // AI 로딩 상태
  const messagesEndRef = useRef(null);

  useEffect(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, isAiThinking]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStep('loading');
    setLoadingState('calculating');

    try {
        const response = await fetch('/api/chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        const validData = (data && data.planets) ? data : FALLBACK_DATA;

        setChartData(validData);
        setStep('chat');
        setMessages([{ 
            text: `환영합니다. ${validData.summary}\n\n별들의 배치는 당신의 운명에 대한 지도를 보여줍니다. 무엇이든 물어보세요.`, 
            isAi: true 
        }]);

    } catch (error) {
        console.error("API Error:", error);
        setChartData(FALLBACK_DATA);
        setStep('chat');
        setMessages([{ 
            text: `서버 연결에 약간의 문제가 있었지만, 예비 데이터로 분석을 시작합니다.\n\n${FALLBACK_DATA.summary}`, 
            isAi: true 
        }]);
    }
  };

  const handleSendMessage = async (e, textOverride = null) => {
    if (e) e.preventDefault();
    const userMsg = textOverride || input;
    if (!userMsg.trim()) return;
    
    setInput('');
    setMessages(prev => [...prev, { text: userMsg, isAi: false }]);
    setIsAiThinking(true); // AI 생각 중 표시

    try {
        // [수정됨] 실제 백엔드 AI 엔드포인트 호출
        // 질문과 함께 현재 차트 정보도 보내야 정확한 해석이 가능합니다.
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: userMsg,
                planets: chartData.planets || FALLBACK_DATA.planets
            })
        });

        const data = await response.json();
        
        setIsAiThinking(false);
        setMessages(prev => [...prev, { text: data.answer, isAi: true }]);

    } catch (error) {
        console.error("AI Request Error:", error);
        setIsAiThinking(false);
        setMessages(prev => [...prev, { 
            text: "죄송합니다. 별들의 목소리가 잠시 끊겼습니다. 다시 한 번 질문해 주시겠어요?", 
            isAi: true 
        }]);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans selection:bg-amber-500/30 selection:text-amber-100 overflow-x-hidden">
      
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;800&family=Lato:wght@300;400;700&display=swap');
        .font-serif { font-family: 'Cinzel', serif; }
        .font-sans { font-family: 'Lato', sans-serif; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in-up { animation: fade-in-up 0.4s ease-out forwards; }
      `}</style>

      <div className="fixed inset-0 pointer-events-none z-0">
         <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-[#1a1f35] to-transparent opacity-60"></div>
      </div>

      <main className="relative z-10 max-w-lg mx-auto min-h-screen flex flex-col shadow-2xl shadow-black">
        
        {/* HERO SECTION */}
        <div className={`relative transition-all duration-700 ${step === 'input' ? 'h-[320px]' : 'h-[140px]'} flex flex-col items-center justify-center overflow-hidden shrink-0`}>
            <StarfieldCanvas />
            
            <div className="relative z-10 text-center px-6 animate-fade-in-up mt-8">
                <div className="flex items-center justify-center gap-2 mb-2 text-amber-400 drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]">
                    <Sparkles size={18} />
                    <span className="text-xs tracking-[0.3em] font-sans uppercase opacity-80">Astro Seek AI</span>
                    <Sparkles size={18} />
                </div>
                <h1 className="text-4xl md:text-5xl font-serif font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-amber-200 pb-2">
                    {step === 'chat' ? 'Oracle' : 'Destiny'}
                </h1>
                {step === 'input' && (
                    <p className="text-slate-400 text-sm font-sans font-light mt-2 max-w-[250px] mx-auto leading-relaxed">
                        별들이 속삭이는 당신의 운명을<br/>고대의 지혜와 기술로 해석합니다.
                    </p>
                )}
            </div>
            {step === 'chat' && (
                <button onClick={() => setStep('input')} className="absolute top-4 right-4 text-slate-500 hover:text-amber-400 transition-colors z-20">
                    <RotateCcw size={16} />
                </button>
            )}
        </div>

        {/* INPUT FORM */}
        {step === 'input' && (
          <div className="flex-1 px-6 pb-10 animate-fade-in-up flex flex-col justify-center -mt-10 relative z-20">
            <form onSubmit={handleSubmit} className="space-y-6 bg-[#121726]/90 backdrop-blur-xl p-8 rounded-2xl border border-amber-500/10 shadow-[0_10px_40px_-10px_rgba(0,0,0,0.5)]">
              
              <div className="group">
                <label className="block text-xs font-serif text-amber-500/70 mb-2 uppercase tracking-widest">Birth Date</label>
                <div className="relative border-b border-slate-700 group-focus-within:border-amber-500 transition-colors pb-1">
                    <Calendar className="absolute left-0 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                    <input type="date" required value={formData.date} onChange={(e) => setFormData({...formData, date: e.target.value})}
                        className="w-full bg-transparent pl-8 pr-2 py-2 text-slate-200 text-center outline-none font-sans" />
                </div>
              </div>

              <div className="flex gap-4">
                <div className="group flex-1">
                    <label className="block text-xs font-serif text-amber-500/70 mb-2 uppercase tracking-widest">Time</label>
                    <div className="relative border-b border-slate-700 group-focus-within:border-amber-500 transition-colors pb-1">
                        <Clock className="absolute left-0 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                        <input type="time" required value={formData.time} onChange={(e) => setFormData({...formData, time: e.target.value})}
                            className="w-full bg-transparent pl-8 pr-2 py-2 text-slate-200 text-center outline-none font-sans" />
                    </div>
                </div>
                <div className="group flex-1">
                    <label className="block text-xs font-serif text-amber-500/70 mb-2 uppercase tracking-widest">City</label>
                    <div className="relative border-b border-slate-700 group-focus-within:border-amber-500 transition-colors pb-1">
                        <MapPin className="absolute left-0 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                        <input type="text" required placeholder="Seoul" value={formData.city} onChange={(e) => setFormData({...formData, city: e.target.value})}
                            className="w-full bg-transparent pl-8 pr-2 py-2 text-slate-200 text-center outline-none font-sans" />
                    </div>
                </div>
              </div>

              <button type="submit" className="w-full mt-4 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-serif font-bold py-4 rounded-xl shadow-[0_0_20px_rgba(217,119,6,0.2)] transition-all flex items-center justify-center gap-2">
                REVEAL MY FATE <Sparkles size={16} />
              </button>
            </form>
          </div>
        )}

        {/* LOADING */}
        {step === 'loading' && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center animate-fade-in-up">
            <Loader2 className="text-amber-500 animate-spin mb-4" size={48} />
            <h3 className="text-xl font-serif text-amber-100">Connecting to Stars</h3>
            <p className="text-slate-500 text-sm mt-2">행성의 위치를 계산하고 있습니다...</p>
          </div>
        )}

        {/* CHAT */}
        {step === 'chat' && chartData && (
          <div className="flex-1 flex flex-col h-[calc(100vh-140px)] relative z-20">
            <div className="w-full overflow-x-auto scrollbar-hide px-6 pb-4 pt-2 shrink-0 border-b border-slate-800/50">
                <div className="flex gap-3 w-max">
                    {chartData.planets.map((planet, idx) => (
                        <PlanetCard key={idx} planet={planet} />
                    ))}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-hide">
              {messages.map((msg, idx) => (
                <div key={idx}>
                    <ChatMessage message={msg.text} isAi={msg.isAi} />
                    {idx === 0 && messages.length === 1 && (
                        <div className="pl-12 pr-4 mb-6 space-y-3 animate-fade-in-up">
                            <p className="text-slate-500 text-xs mb-2 ml-1">다음 질문을 선택해보세요</p>
                            {SUGGESTED_QUESTIONS.map((q, qIdx) => (
                                <button key={qIdx} onClick={() => handleSendMessage(null, q)}
                                    className="w-full text-left bg-slate-800/50 hover:bg-amber-900/20 border border-slate-700 hover:border-amber-500/50 text-amber-100/90 text-sm py-3 px-4 rounded-xl transition-all flex items-center justify-between group">
                                    <span>{q}</span>
                                    <ChevronRight size={14} className="text-slate-500 group-hover:text-amber-400 transition-colors" />
                                </button>
                            ))}
                        </div>
                    )}
                </div>
              ))}
              
              {/* AI 로딩 인디케이터 */}
              {isAiThinking && <ChatMessage message="" isAi={true} isLoading={true} />}
              
              <div ref={messagesEndRef} className="h-4" />
            </div>

            <div className="p-4 bg-gradient-to-t from-[#0B0F19] via-[#0B0F19] to-transparent sticky bottom-0 z-30">
              <form onSubmit={handleSendMessage} className="relative group">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="운세에 대해 물어보세요..."
                  className="w-full bg-[#121726] border border-slate-700 text-slate-200 rounded-2xl py-4 pl-5 pr-14 outline-none focus:border-amber-500/50 placeholder:text-slate-600 font-sans shadow-xl relative z-10" />
                <button type="submit" disabled={!input.trim() || isAiThinking} className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-amber-600 hover:bg-amber-500 text-white rounded-xl disabled:opacity-50 transition-all z-20">
                  <Send size={18} />
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
