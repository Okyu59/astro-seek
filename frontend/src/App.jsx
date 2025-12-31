import React, { useState } from 'react';

// 외부 라이브러리 의존성 제거 (아이콘, 애니메이션 등)
// 순수 React 로직만 테스트합니다.

export default function App() {
  const [step, setStep] = useState('input');
  const [formData, setFormData] = useState({ date: '1995-09-22', time: '14:30', city: 'Seoul' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
        const response = await fetch('/api/chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        setResult(data);
        setStep('result');
    } catch (error) {
        alert("데이터 요청 실패: " + error.message);
    } finally {
        setLoading(false);
    }
  };

  // 스타일 객체 (CSS 파일 의존성 제거를 위해 직접 주입)
  const styles = {
    container: {
        backgroundColor: '#111',
        color: '#fff',
        minHeight: '100vh',
        fontFamily: 'sans-serif',
        padding: '20px',
        textAlign: 'center'
    },
    input: {
        padding: '10px',
        margin: '5px',
        borderRadius: '5px',
        border: '1px solid #555',
        backgroundColor: '#222',
        color: 'white'
    },
    button: {
        padding: '10px 20px',
        backgroundColor: '#d97706',
        color: 'white',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        fontWeight: 'bold',
        marginTop: '20px'
    },
    card: {
        border: '1px solid #444',
        padding: '10px',
        margin: '5px',
        display: 'inline-block',
        width: '120px',
        backgroundColor: '#222'
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={{ color: '#fbbf24' }}>Oracle Destiny (Lite)</h1>
      <p>그래픽 요소를 제거한 디버깅 모드입니다.</p>
      <hr style={{ borderColor: '#333', margin: '20px 0' }} />

      {step === 'input' && (
        <form onSubmit={handleSubmit}>
            <div>
                <label>생년월일: </label>
                <input 
                    type="date" 
                    value={formData.date}
                    onChange={e => setFormData({...formData, date: e.target.value})}
                    style={styles.input}
                />
            </div>
            <div>
                <label>태어난 시간: </label>
                <input 
                    type="time" 
                    value={formData.time}
                    onChange={e => setFormData({...formData, time: e.target.value})}
                    style={styles.input}
                />
            </div>
            <div>
                <label>도시: </label>
                <input 
                    type="text" 
                    value={formData.city}
                    onChange={e => setFormData({...formData, city: e.target.value})}
                    style={styles.input}
                />
            </div>
            
            <button type="button" onClick={handleSubmit} disabled={loading} style={styles.button}>
                {loading ? "서버 통신 중..." : "운세 보기"}
            </button>
        </form>
      )}

      {step === 'result' && result && (
        <div>
            <h2>결과 분석</h2>
            <p style={{ color: '#aaa', marginBottom: '20px' }}>{result.summary}</p>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
                {result.planets.map((p, idx) => (
                    <div key={idx} style={styles.card}>
                        <div style={{ color: '#fbbf24', fontWeight: 'bold' }}>{p.name}</div>
                        <div>{p.sign}</div>
                        <div style={{ fontSize: '0.8em', color: '#888' }}>{p.house}</div>
                    </div>
                ))}
            </div>

            <button onClick={() => setStep('input')} style={{...styles.button, backgroundColor: '#444'}}>
                다시 하기
            </button>
        </div>
      )}
    </div>
  );
}


