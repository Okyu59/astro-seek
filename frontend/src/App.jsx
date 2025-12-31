import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, MapPin, Calendar, Clock, Loader2, Star, Moon, Sun, RotateCcw, ChevronRight } from 'lucide-react';

// ... (StarfieldCanvas 및 UI 컴포넌트 코드는 이전과 동일, 생략하여 길이 조절) ...
// ... (ChatMessage, PlanetCard 컴포넌트도 동일) ...

// [핵심 변경 사항: API 호출 로직]
export default function App() {
  const [step, setStep] = useState('input');
  const [loadingState, setLoadingState] = useState('verifying'); 
  const [formData, setFormData] = useState({ date: '1995-09-22', time: '14:30', city: 'Seoul' });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [chartData, setChartData] = useState(null);
  const messagesEndRef = useRef(null);

  // Scroll to bottom
  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(() => scrollToBottom(), [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStep('loading');
    setLoadingState('verifying');

    try {
        // 1. 도시 검증 (여기서는 간단한 길이 체크만)
        if (formData.city.trim().length < 2) throw new Error("Invalid City");
        
        setLoadingState('calculating');

        // 2. 백엔드 API 호출 (실제 크롤링 요청)
        const response = await fetch('/api/chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (!response.ok) throw new Error("Server Error");

        const data = await response.json();
        
        setChartData(data);
        setStep('chat');
        setMessages([{ 
            text: `환영합니다. ${data.summary}\n\n별들의 배치는 당신의 운명에 대한 지도를 보여줍니다. 무엇이든 물어보세요.`, 
            isAi: true 
        }]);

    } catch (error) {
        console.error(error);
        setStep('input');
        alert("데이터를 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.");
    }
  };

  const handleSendMessage = (e, textOverride = null) => {
    e && e.preventDefault();
    const userMsg = textOverride || input;
    if (!userMsg.trim()) return;
    
    setInput('');
    setMessages(prev => [...prev, { text: userMsg, isAi: false }]);

    // AI 답변 로직 (간단한 규칙 기반, 추후 LLM API 연결 가능)
    setTimeout(() => {
        let aiResponse = "별들의 움직임을 읽고 있습니다...";
        const sun = chartData.planets.find(p => p.name === "Sun")?.sign || "Unknown";
        
        if (userMsg.includes("연애") || userMsg.includes("사랑")) {
            aiResponse = `당신의 태양 별자리인 ${sun}의 기운을 보아하니, 올해는 감정적인 깊이가 깊어지는 시기입니다. 5월과 11월에 새로운 인연의 기운이 강합니다.`;
        } else if (userMsg.includes("직업") || userMsg.includes("일")) {
            aiResponse = `직업운에서는 ${sun} 특유의 분석력이 빛을 발할 때입니다. 현재 차트의 흐름은 변화보다는 안정을 추천하고 있습니다.`;
        } else {
             aiResponse = `흥미로운 질문이네요. ${sun} 자리의 영향으로 당신은 이 문제에 대해 꽤나 신중하게 접근하고 계신 것 같습니다.`;
        }
        setMessages(prev => [...prev, { text: aiResponse, isAi: true }]);
    }, 1200);
  };

  // ... (Return JSX 부분은 이전 디자인과 동일 - formData input에 text-center 등 적용됨) ...
  // (생략된 JSX 코드는 위에서 만든 완벽한 디자인을 그대로 사용합니다)
  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 overflow-x-hidden font-sans selection:bg-amber-500/30 selection:text-amber-100">
        {/* ... (이전 코드의 JSX 붙여넣기) ... */}
        {/* 주의: 위에서 작성한 StarfieldCanvas 등의 컴포넌트가 파일 내에 포함되어야 함 */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center animate-fade-in-up">
            {step === 'input' && (
                /* Form JSX... */
                <button onClick={handleSubmit}>Start</button> 
                /* (실제로는 위에서 만든 예쁜 Form 사용) */
            )}
            {/* Loading, Chat UI Logic... */}
        </div>
    </div>
  );
}


