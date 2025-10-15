import React, { useState } from 'react';

// --- Core Logic (Translated from Python to JavaScript) ---
const extractBudget = (text) => {
    if (!text) return null;

    // 1. Pre-process the text.
    let cleanedText = text.toLowerCase();
    
    // Step 1.1: Remove decimal part (e.g., ",00")
    cleanedText = cleanedText.replace(/,[\d]+/, '');

    // Step 1.2: Remove currency symbols, thousand separators (dots), and spaces.
    cleanedText = cleanedText.replace(/(rp|\s|\.)/g, '');

    // 2. Define regex patterns. Note the order is important (most specific first).
    const patterns = [
        { regex: /(\d+)(m|miliar)/, multiplier: 1_000_000_000 },
        { regex: /(\d+)(jt|juta|million)/, multiplier: 1_000_000 },
        { regex: /(\d+)(k|ribu)/, multiplier: 1_000 },
        { regex: /(\d+)/, multiplier: 1 } // For plain numbers
    ];

    for (const pattern of patterns) {
        const match = cleanedText.match(pattern.regex);
        if (match) {
            const value = parseInt(match[1], 10);
            return value * pattern.multiplier;
        }
    }

    // 4. If no pattern matches, no budget was found.
    return null;
};

// --- Main React Component ---
function App() {
    const [inputText, setInputText] = useState('');
    const [result, setResult] = useState(null);

    const handleAnalysis = () => {
        const budget = extractBudget(inputText);

        if (budget === null) {
            setResult({
                detected: 'Tidak ada budget yang ditemukan.',
                decision: 'Silakan spesifikasikan budget Anda dengan jelas.',
                color: 'text-yellow-500'
            });
            return;
        }

        // Format the budget for display using Indonesian locale string formatting.
        const formattedBudget = new Intl.NumberFormat('id-ID', {
            style: 'currency',
            currency: 'IDR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(budget);

        if (budget >= 300_000_000) {
            setResult({
                detected: `Budget yang terdeteksi: ${formattedBudget}`,
                decision: 'Keputusan: b (Budget Rp 300.000.000 atau lebih)',
                documents: 'BAP\nDraf nota dinas izin prinsip\nRAB\nRKS\nNota Dina izin Prinsip',
                color: 'text-green-500'
            });
        } else {
            setResult({
                detected: `Budget yang terdeteksi: ${formattedBudget}`,
                decision: 'Keputusan: a (Budget kurang dari Rp 300.000.000)',
                documents: 'BAP\nReview Pekerjaan\nRAB\nRKS',
                color: 'text-blue-500'
            });
        }
    };
    
    // Handle Enter key press in textarea
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // Prevents new line on Enter
            handleAnalysis();
        }
    };

    return (
        <div className="bg-slate-900 min-h-screen flex flex-col items-center justify-center font-sans p-4 text-white">
            <div className="w-full max-w-2xl bg-slate-800 rounded-2xl shadow-2xl p-8 space-y-6">
                
                {/* Header */}
                <div className="text-center">
                    <h1 className="text-4xl font-bold text-cyan-400">Budget Analyzer</h1>
                    <p className="text-slate-400 mt-2">
                        Masukkan deskripsi kebutuhan Anda, dan kami akan mengekstrak budgetnya.
                    </p>
                </div>
                
                {/* Input Area */}
                <div className="flex flex-col">
                    <textarea
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyPress={handleKeyPress}
                        className="w-full h-32 p-4 bg-slate-700 border-2 border-slate-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:outline-none transition-all duration-300 placeholder-slate-500"
                        placeholder="Contoh: Saya ingin memperpanjang lisensi Adobe dengan budget sekitar 300jt rupiah..."
                    />
                    <button
                        onClick={handleAnalysis}
                        className="mt-4 w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-4 rounded-lg transition-transform duration-200 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-800 focus:ring-cyan-500"
                    >
                        Analisis Deskripsi
                    </button>
                </div>

                {/* Result Display */}
                {result && (
                    <div className="bg-slate-700 p-6 rounded-lg animate-fade-in">
                        <p className="text-slate-300 text-lg">{result.detected}</p>
                        <p className={`text-xl font-semibold mt-2 ${result.color}`}>{result.decision}</p>
                    </div>
                )}
            </div>
            
            <footer className="text-center mt-8 text-slate-500">
                <p>Powered by React & Tailwind CSS</p>
            </footer>
        </div>
    );
}

export default App;
