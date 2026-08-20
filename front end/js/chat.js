/* =========================================================

   T2D Care - Chat script

   Connects to the FastAPI backend and renders bot replies.

   "View Pipeline" button navigates to pipeline.html with

   the full trace stored in sessionStorage.

   ========================================================= */



   const API_URL = 'http://localhost:8000';



   const chatWindow   = document.getElementById('chat-window');
   
   const userInput    = document.getElementById('user-input');
   
   const sendBtn      = document.getElementById('send-btn');
   
   
   
   const voiceBtn     = document.getElementById('voice-btn');
   
   
   
   let sessionId = crypto.randomUUID ? crypto.randomUUID() : `s-${Date.now()}`;
   
   let msgCounter = 0;
   
   
   
   /* ---------------------------------------------------------
   
      1. SEND FLOW
   
      --------------------------------------------------------- */
   
   sendBtn.addEventListener('click', handleSend);
   
   userInput.addEventListener('keydown', (e) => {
   
     if (e.key === 'Enter') handleSend();
   
   });
   
   
   
   function handleSend() {
   
     const text = userInput.value.trim();
   
     if (!text) return;
   
   
   
     appendUserMessage(text);
   
     userInput.value = '';
   
   
   
     const typingEl = showTypingIndicator();
   
   
   
     getBotResponse(text).then(({ reply, trace }) => {
   
       typingEl.remove();
   
       appendBotMessage(reply, trace);
   
     });
   
   }
   
   
   
   function appendUserMessage(text) {
   
     const msg = document.createElement('div');
   
     msg.className = 'message user';
   
     msg.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
   
     chatWindow.appendChild(msg);
   
     scrollToBottom();
   
   }
   
   
   
   function appendBotMessage(text, trace) {
   
     msgCounter++;
   
     const traceKey = `pipeline-trace-${msgCounter}`;
   
   
   
     const msg = document.createElement('div');
   
     msg.className = 'message bot';
   
   
   
     const formattedText = escapeHtml(text).replace(/\n/g, '<br>');
   
     let html = `<div class="bubble">${formattedText}</div>`;
   
   
   
     if (trace && !trace.skipped) {
   
       html += `<button class="pipeline-btn" data-key="${traceKey}">📊 View Pipeline</button>`;
   
       sessionStorage.setItem(traceKey, JSON.stringify(trace));
   
       sessionStorage.setItem('latest-pipeline-trace', JSON.stringify(trace));
   
     }
   
   
   
     msg.innerHTML = html;
   
     chatWindow.appendChild(msg);
   
     scrollToBottom();
   
   
   
     const btn = msg.querySelector('.pipeline-btn');
   
     if (btn) {
   
       btn.addEventListener('click', () => {
   
         sessionStorage.setItem('latest-pipeline-trace', JSON.stringify(trace));
   
         // CHANGE: Navigate to pipeline.html instead of dashboard.html
         window.location.href = 'pipeline.html';
   
       });
   
     }
   
   }
   
   
   
   function showTypingIndicator() {
   
     const el = document.createElement('div');
   
     el.className = 'message bot typing';
   
     el.innerHTML = `<div class="bubble"><span></span><span></span><span></span></div>`;
   
     chatWindow.appendChild(el);
   
     scrollToBottom();
   
     return el;
   
   }
   
   
   
   function scrollToBottom() {
   
     chatWindow.scrollTop = chatWindow.scrollHeight;
   
   }
   
   
   
   function escapeHtml(str) {
   
     const div = document.createElement('div');
   
     div.textContent = str;
   
     return div.innerHTML;
   
   }
   
   
   
   /* ---------------------------------------------------------
   
      2. VOICE INPUT (Web Speech API — no install needed)
   
      --------------------------------------------------------- */
   
   const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
   
   let recognition = null;
   
   let isListening = false;
   
   
   
   if (SpeechRecognition) {
   
     recognition = new SpeechRecognition();
   
     recognition.lang = 'en-US';
   
     recognition.interimResults = false;
   
     recognition.continuous = false;
   
   
   
     recognition.addEventListener('result', (e) => {
   
       const transcript = e.results[0][0].transcript;
   
       userInput.value = transcript;
   
       stopListening();
   
     });
   
   
   
     recognition.addEventListener('end', stopListening);
   
     recognition.addEventListener('error', stopListening);
   
   
   
     voiceBtn.addEventListener('click', () => {
   
       if (isListening) {
   
         recognition.stop();
   
       } else {
   
         recognition.start();
   
         isListening = true;
   
         voiceBtn.classList.add('listening');
   
         voiceBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
   
       }
   
     });
   
   } else {
   
     voiceBtn.title = 'Voice input not supported in this browser';
   
     voiceBtn.style.opacity = '0.4';
   
     voiceBtn.style.cursor = 'not-allowed';
   
   }
   
   
   
   function stopListening() {
   
     isListening = false;
   
     if (voiceBtn) {
   
       voiceBtn.classList.remove('listening');
   
       voiceBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="1" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
   
     }
   
   }
   
   
   
   /* ---------------------------------------------------------
   
      3. BACKEND CALL
   
      --------------------------------------------------------- */
   
   async function getBotResponse(userText) {
   
     try {
   
       const res = await fetch(`${API_URL}/chat`, {
   
         method: 'POST',
   
         headers: { 'Content-Type': 'application/json' },
   
         body: JSON.stringify({ session_id: sessionId, message: userText }),
   
       });
   
   
   
       if (!res.ok) throw new Error(`Server error ${res.status}`);
   
   
   
       const data = await res.json();
   
       return {
   
         reply: data.message,
   
         trace: data.trace || {},
   
       };
   
     } catch (err) {
   
       console.error('Chat API error:', err);
   
       return {
   
         reply: 'Sorry, I could not reach the server. Please make sure the backend is running.',
   
         trace: {},
   
       };
   
     }
   
   }