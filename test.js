<<<<<<< HEAD

'use strict';

// ── STATE ──────────────────────────────────────────────────────
let activePhone      = null;
let lastMessageCount = 0;
let allChats         = [];
// Per-type: store selected File object
const selectedFiles  = {image:null,video:null,document:null,audio:null,sticker:null};

const appContainer = document.getElementById('appContainer');
const messageArea  = document.getElementById('messageArea');
const scrollBtn    = document.getElementById('scrollBottomBtn');
const attachPopup  = document.getElementById('attachPopup');
const attachBtn    = document.getElementById('attachBtn');

// ── AVATAR ────────────────────────────────────────────────────
const AVC = [['#1a4a3a','#00a884'],['#1e2d5a','#4a80f5'],['#4a1a2a','#e05c8a'],['#3a2a10','#e08040'],['#1a1a4a','#8060e0'],['#0d3d2d','#40c090'],['#3a1010','#e05040'],['#103a3a','#40b0b0']];
function avatarStyle(phone){let h=0;for(let c of(phone||''))h=(h*31+c.charCodeAt(0))&0xffffffff;const[bg,fg]=AVC[Math.abs(h)%AVC.length];return{bg,fg,initials:(phone||'??').replace(/\D/g,'').slice(-2)||'??'};}
function setHeaderAvatar(p){const{bg,fg,initials}=avatarStyle(p);const el=document.getElementById('headerAvatar');el.style.background=bg;el.style.color=fg;el.textContent=initials;}

// ── TIME ──────────────────────────────────────────────────────
function relTime(ts){if(!ts||ts==='now')return'';try{const d=new Date(ts);if(isNaN(d))return'';const diff=(Date.now()-d)/1000;if(diff<60)return'just now';if(diff<3600)return Math.floor(diff/60)+'m';if(diff<86400)return Math.floor(diff/3600)+'h';return d.toLocaleDateString([],{month:'short',day:'numeric'});}catch{return'';}}
function fmtTime(ts){if(!ts||ts==='now')return new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});try{const d=new Date(ts);if(isNaN(d))return'';return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}catch{return'';}}
function fmtBytes(b){if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(1)+' MB';}

// ── UTILS ─────────────────────────────────────────────────────
function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function showToast(msg,dur=2600){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),dur);}
function copyPhone(){if(!activePhone)return;navigator.clipboard.writeText(activePhone).then(()=>showToast('📋 Phone number copied!'));}

// ── SCROLL ────────────────────────────────────────────────────
function scrollToBottom(s=false){messageArea.scrollTo({top:messageArea.scrollHeight,behavior:s?'smooth':'auto'});}
messageArea.addEventListener('scroll',()=>{scrollBtn.classList.toggle('visible',(messageArea.scrollHeight-messageArea.scrollTop-messageArea.clientHeight)>120);});

// ── ATTACH POPUP ──────────────────────────────────────────────
function toggleAttachPopup(){const o=attachPopup.classList.toggle('visible');attachBtn.classList.toggle('open',o);}
document.addEventListener('click',e=>{if(!attachBtn.contains(e.target)&&!attachPopup.contains(e.target)){attachPopup.classList.remove('visible');attachBtn.classList.remove('open');}});

// ── MODALS ────────────────────────────────────────────────────
function openModal(t){attachPopup.classList.remove('visible');attachBtn.classList.remove('open');document.getElementById('modal-'+t).classList.add('active');}
function closeModal(t){document.getElementById('modal-'+t).classList.remove('active');}
document.querySelectorAll('.modal-overlay').forEach(o=>o.addEventListener('click',e=>{if(e.target===o)o.classList.remove('active');}));
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.modal-overlay.active').forEach(o=>o.classList.remove('active'));});

// ── FILE DROP ZONE ────────────────────────────────────────────
function onDragOver(e,type){e.preventDefault();document.getElementById('fdz-'+type).classList.add('drag-over');}
function onDragLeave(type){document.getElementById('fdz-'+type).classList.remove('drag-over');}
function onDrop(e,type){e.preventDefault();onDragLeave(type);const file=e.dataTransfer.files[0];if(file){const inp=document.getElementById('file-'+type);const dt=new DataTransfer();dt.items.add(file);inp.files=dt.files;onFileSelect(type);}}
function changeFile(type){document.getElementById('file-'+type).click();}

function onFileSelect(type){
    const inp=document.getElementById('file-'+type);
    if(!inp.files||!inp.files[0])return;
    const file=inp.files[0];
    selectedFiles[type]=file;

    // Hide drop zone, show preview
    document.getElementById('fdz-'+type).style.display='none';
    const prev=document.getElementById('prev-'+type);
    prev.classList.add('visible');

    // Fill in name + size
    const nameEl=document.getElementById('prev-'+type+'-name');
    const sizeEl=document.getElementById('prev-'+type+'-size');
    if(nameEl) nameEl.textContent=file.name;
    if(sizeEl) sizeEl.textContent=fmtBytes(file.size);

    // Image/sticker: show thumbnail
    if(type==='image'||type==='sticker'){
        const thumb=document.getElementById('prev-'+type+'-thumb');
        if(thumb){const reader=new FileReader();reader.onload=e=>thumb.src=e.target.result;reader.readAsDataURL(file);}
    }

    // Enable send button
    document.getElementById('send-'+type+'-btn').disabled=false;

    // Reset progress
    resetProgress(type);
}

function resetProgress(type){
    const p=document.getElementById('prog-'+type);
    if(!p)return;
    p.classList.remove('visible');
    document.getElementById('prog-'+type+'-bar').style.width='0%';
    document.getElementById('prog-'+type+'-pct').textContent='0%';
    document.getElementById('prog-'+type+'-status').textContent='';
}

// ── UPLOAD + SEND (2-step for file types) ────────────────────
async function sendWithUpload(type){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const file=selectedFiles[type];
    if(!file){showToast('⚠️ Please select a file first');return;}

    const sendBtn=document.getElementById('send-'+type+'-btn');
    sendBtn.disabled=true;
    sendBtn.innerHTML=`<svg style="animation:spin .8s linear infinite;width:15px;height:15px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Uploading…`;

    // Show progress bar
    const prog=document.getElementById('prog-'+type);
    prog.classList.add('visible');
    const bar=document.getElementById('prog-'+type+'-bar');
    const pct=document.getElementById('prog-'+type+'-pct');
    const stat=document.getElementById('prog-'+type+'-status');

    // ── STEP 1: Upload to Meta via XHR (so we can track progress) ──
    let media_id;
    try {
        const fd=new FormData();
        fd.append('file',file,file.name);

        media_id = await new Promise((resolve,reject)=>{
            const xhr=new XMLHttpRequest();
            xhr.open('POST','/api/upload_media');
            xhr.upload.onprogress=e=>{
                if(e.lengthComputable){
                    const p=Math.round(e.loaded/e.total*90); // 90% for upload, 10% for send
                    bar.style.width=p+'%';
                    pct.textContent=p+'%';
                }
            };
            xhr.onload=()=>{
                const data=JSON.parse(xhr.responseText);
                if(data.error){reject(new Error(data.error));}
                else{resolve(data.media_id);}
            };
            xhr.onerror=()=>reject(new Error('Network error during upload'));
            xhr.send(fd);
        });
    } catch(e) {
        showToast('⚠️ Upload failed: '+e.message, 3500);
        stat.textContent='❌ Upload failed: '+e.message;
        sendBtn.disabled=false;
        sendBtn.innerHTML=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:15px;height:15px" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Send`;
        return;
    }

    // ── STEP 2: Send the message using the media_id ──
    bar.style.width='95%'; pct.textContent='95%'; stat.textContent='Sending…';

    const endpointMap={image:'/api/send_image',video:'/api/send_video',document:'/api/send_document',audio:'/api/send_audio',sticker:'/api/send_sticker'};
    const body={phone:activePhone,media_id};

    // Extra fields per type
    if(type==='image')    body.caption = (document.getElementById('img-caption')||{}).value||'';
    if(type==='video')    body.caption = (document.getElementById('vid-caption')||{}).value||'';
    if(type==='document'){body.caption = (document.getElementById('doc-caption')||{}).value||'';body.filename=file.name;}
    if(type==='audio')    {} // no extra
    if(type==='sticker')  {} // no extra

    try {
        const res=await fetch(endpointMap[type],{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data=await res.json();
        if(data.error){
            stat.textContent='❌ Send failed: '+data.error;
            showToast('⚠️ Send failed: '+data.error,3500);
        } else {
            bar.style.width='100%'; pct.textContent='100%'; stat.textContent='✅ Sent!';
            showToast('✅ '+type.charAt(0).toUpperCase()+type.slice(1)+' sent!');
            // Reset modal after a short delay
            setTimeout(()=>{closeModal(type);resetModalState(type);},800);
            loadMessages(); loadChats();
        }
    } catch(e) {
        stat.textContent='❌ Network error';
        showToast('⚠️ Network error while sending');
    } finally {
        sendBtn.disabled=false;
        const lbl=type.charAt(0).toUpperCase()+type.slice(1);
        sendBtn.innerHTML=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:15px;height:15px" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Send ${lbl}`;
    }
}

function resetModalState(type){
    selectedFiles[type]=null;
    const fdz=document.getElementById('fdz-'+type);
    if(fdz) fdz.style.display='';
    const prev=document.getElementById('prev-'+type);
    if(prev) prev.classList.remove('visible');
    const inp=document.getElementById('file-'+type);
    if(inp) inp.value='';
    const sb=document.getElementById('send-'+type+'-btn');
    if(sb) sb.disabled=true;
    resetProgress(type);
    // Clear captions
    const cap=document.getElementById(type.substring(0,3)+'-caption');
    if(cap) cap.value='';
}

// ── LOCATION ──────────────────────────────────────────────────
async function sendLocation(){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const lat=document.getElementById('loc-lat').value.trim();
    const lng=document.getElementById('loc-lng').value.trim();
    if(!lat||!lng){showToast('⚠️ Latitude and Longitude are required');return;}
    await simpleSend('/api/send_location',{phone:activePhone,latitude:parseFloat(lat),longitude:parseFloat(lng),name:document.getElementById('loc-name').value.trim(),address:document.getElementById('loc-address').value.trim()},'location','📍 Location sent!');
}

// ── CATALOG ───────────────────────────────────────────────────
async function sendCatalog(){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const body={phone:activePhone,body:document.getElementById('cat-body').value.trim()};
    const th=document.getElementById('cat-thumb').value.trim();
    if(th) body.thumbnail_product_id=th;
    await simpleSend('/api/send_catalog',body,'catalog','🛍️ Catalog sent!');
}

// ── QUICK REPLY ───────────────────────────────────────────────
async function sendQuickReply(){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const bodyText=document.getElementById('qr-body').value.trim();
    if(!bodyText){showToast('⚠️ Message body is required');return;}
    const rows=document.getElementById('qrButtonsWrap').querySelectorAll('.qr-btn-row');
    const buttons={};let valid=true;
    rows.forEach(r=>{const id=r.querySelector('[data-role=id]').value.trim();const t=r.querySelector('[data-role=title]').value.trim();if(!id||!t){valid=false;}else{buttons[id]=t;}});
    if(!valid||Object.keys(buttons).length===0){showToast('⚠️ Fill in all button IDs and labels');return;}
    await simpleSend('/api/send_quick_reply',{phone:activePhone,text:bodyText,buttons},'quickreply','⚡ Quick reply sent!');
}

// ── GENERIC SIMPLE SEND (no upload) ──────────────────────────
async function simpleSend(endpoint,body,modalType,successMsg){
    try{
        const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data=await res.json();
        if(data.error){showToast('⚠️ '+data.error,3500);}
        else{showToast(successMsg);closeModal(modalType);loadMessages();loadChats();}
    }catch(e){showToast('⚠️ Network error');console.error(e);}
}

// ── QUICK REPLY BUILDER ───────────────────────────────────────
function addQrRow(){const w=document.getElementById('qrButtonsWrap');if(w.querySelectorAll('.qr-btn-row').length>=3){showToast('⚠️ Max 3 buttons');return;}const r=document.createElement('div');r.className='qr-btn-row';r.innerHTML=`<input class="form-input qr-id-inp" placeholder="ID" data-role="id"><input class="form-input" placeholder="Label" data-role="title"><button class="qr-remove" onclick="removeQrRow(this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>`;w.appendChild(r);updateQrCounter();}
function removeQrRow(b){b.closest('.qr-btn-row').remove();updateQrCounter();}
function updateQrCounter(){const n=document.getElementById('qrButtonsWrap').querySelectorAll('.qr-btn-row').length;document.getElementById('qrCounter').textContent=`${n} / 3 buttons`;document.getElementById('addQrBtn').style.display=n>=3?'none':'flex';}

// ── QUICK ACTIONS (menu / order booking) ─────────────────────
async function qaAction(action){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const id=action==='menu'?'qaMenuBtn':'qaOrderBtn';
    const ep=action==='menu'?'/api/send_menu':'/api/send_order_booking';
    const btn=document.getElementById(id);
    btn.classList.add('loading');
    try{
        const res=await fetch(ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:activePhone})});
        const data=await res.json();
        if(data.error){showToast('⚠️ '+data.error,3000);}
        else{btn.classList.add('success');showToast('✅ Sent!');loadMessages();loadChats();}
    }catch(e){showToast('⚠️ Network error');}
    finally{btn.classList.remove('loading');setTimeout(()=>btn.classList.remove('success'),2000);}
}

// ── LOAD CHATS ────────────────────────────────────────────────
async function loadChats(){
    try{const r=await fetch('/api/chats');allChats=await r.json();renderChatList(allChats);}
    catch(e){console.error('loadChats:',e);}
}
function renderChatList(chats){
    const el=document.getElementById('chatList');
    if(!chats||!chats.length){el.innerHTML='<div class="sidebar-empty"><p>No conversations yet.<br>Messages will appear here.</p></div>';return;}
    el.innerHTML=chats.map(c=>{const{bg,fg,initials}=avatarStyle(c.phone);const a=c.phone===activePhone?'active':'';return`<div class="chat-item ${a}" onclick="selectChat('${esc(c.phone)}')"><div class="avatar" style="width:46px;height:46px;font-size:16px;background:${bg};color:${fg};">${initials}</div><div class="chat-item-body"><div class="chat-item-top"><div class="phone-num">${esc(c.phone)}</div>${c.timestamp?`<div class="chat-time">${relTime(c.timestamp)}</div>`:''}</div><div class="preview-txt">${esc(c.last_message||'')}</div></div></div>`;}).join('');
}
function filterChats(q){q=q.trim().toLowerCase();renderChatList(q?allChats.filter(c=>c.phone.toLowerCase().includes(q)):allChats);}

// ── CHAT SELECTION ────────────────────────────────────────────
function selectChat(phone){activePhone=phone;lastMessageCount=0;document.getElementById('placeholderView').style.display='none';document.getElementById('activeChatContent').style.display='flex';document.getElementById('currentChatPhone').innerText=phone;setHeaderAvatar(phone);appContainer.classList.add('show-chat');loadMessages();loadChats();}
function goBackToList(){appContainer.classList.remove('show-chat');activePhone=null;}

// ── LOAD MESSAGES ─────────────────────────────────────────────
async function loadMessages(){
    if(!activePhone)return;
    try{
        const r=await fetch(`/api/messages/${activePhone}`);
        const msgs=await r.json();
        if(msgs.length===lastMessageCount)return;
        const atBottom=(messageArea.scrollHeight-messageArea.scrollTop-messageArea.clientHeight)<80;
        messageArea.innerHTML='';
        let lastDate=null;
        msgs.forEach(msg=>{
            const lbl='Today';
            if(lbl!==lastDate){lastDate=lbl;const sep=document.createElement('div');sep.className='date-separator';sep.innerHTML=`<div class="date-pill">${lbl}</div>`;messageArea.appendChild(sep);}
            const isOut=msg.type!=='incoming';
            const div=document.createElement('div');div.className=`msg ${isOut?'outgoing':'incoming'}`;
            const tick=isOut?`<span class="msg-tick"><svg viewBox="0 0 16 11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 5 4 8 9 2"/><polyline points="6 5 9 8 14 2"/></svg></span>`:'';
            div.innerHTML=`<div>${esc(msg.text)}</div><div class="msg-footer"><span class="msg-time">${fmtTime(msg.timestamp)}</span>${tick}</div>`;
            messageArea.appendChild(div);
        });
        if(atBottom||lastMessageCount===0)scrollToBottom(false);
        lastMessageCount=msgs.length;
    }catch(e){console.error('loadMessages:',e);}
}

// ── SEND TEXT ─────────────────────────────────────────────────
async function sendMessage(){
    const inp=document.getElementById('messageInput');
    const btn=document.getElementById('sendBtn');
    const text=inp.value.trim();
    if(!text||!activePhone)return;
    inp.value='';inp.focus();
    btn.classList.add('sending');setTimeout(()=>btn.classList.remove('sending'),400);
    try{await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:activePhone,message:text})});loadMessages();loadChats();}
    catch(e){console.error('sendMessage:',e);}
}

// ── INPUT TOGGLE (mic ↔ send arrow) ──────────────────────────
function onInputChange(){
    const hasText = document.getElementById('messageInput').value.trim().length > 0;
    document.getElementById('sendBtn').classList.toggle('hidden', !hasText);
    document.getElementById('micBtn').classList.toggle('hidden',  hasText);
}

// ── VOICE NOTE RECORDING ──────────────────────────────────────
let mediaRecorder    = null;
let audioChunks      = [];
let recTimerInterval = null;
let recSeconds       = 0;
let micStream        = null;  // keep reference for proper cleanup

async function startRecording(){
    if(!activePhone){ showToast('⚠️ Select a conversation first'); return; }

    // Request microphone
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch(e) {
        if(e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError')
            showToast('⚠️ Microphone access denied — allow it in browser settings');
        else
            showToast('⚠️ Could not access microphone: ' + e.message);
        return;
    }

    // Pick best supported mimeType — prefer webm/opus (Chrome), then ogg/opus (Firefox), then mp4 (Safari)
    const mimeType = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4','']
        .find(t => t === '' || MediaRecorder.isTypeSupported(t));

    audioChunks = [];
    try {
        mediaRecorder = new MediaRecorder(micStream, mimeType ? { mimeType } : {});
    } catch(e) {
        mediaRecorder = new MediaRecorder(micStream);
    }
    mediaRecorder.ondataavailable = e => { if(e.data && e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.start(100);

    // Show recording bar
    document.getElementById('recordingBar').classList.add('active');
    document.getElementById('attachBtn').style.visibility    = 'hidden';
    document.getElementById('messageInput').style.visibility = 'hidden';
    document.getElementById('sendBtn').style.visibility      = 'hidden';
    document.getElementById('micBtn').style.visibility       = 'hidden';

    // Start timer
    recSeconds = 0;
    document.getElementById('recTimer').textContent = '0:00';
    recTimerInterval = setInterval(() => {
        recSeconds++;
        const m = Math.floor(recSeconds / 60);
        const s = String(recSeconds % 60).padStart(2, '0');
        document.getElementById('recTimer').textContent = `${m}:${s}`;
        if(recSeconds >= 300) stopAndSendRecording(); // 5-min WhatsApp limit
    }, 1000);
}

function cancelRecording(){
    _stopMic();
    clearInterval(recTimerInterval);
    audioChunks = [];
    hideRecordingBar();
    showToast('🗑️ Recording cancelled');
}

function _stopMic(){
    if(mediaRecorder && mediaRecorder.state !== 'inactive') {
        try { mediaRecorder.stop(); } catch(_){}
    }
    if(micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
    }
}

// ── WAV encoder (Web Audio API → raw 16-bit PCM WAV) ──────────
// This converts ANY browser audio blob (webm/ogg/mp4) into a
// proper WAV file that Meta WhatsApp API accepts and delivers.
async function blobToWav(blob){
    const arrayBuf  = await blob.arrayBuffer();
    const audioCtx  = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    let decoded;
    try {
        decoded = await audioCtx.decodeAudioData(arrayBuf);
    } finally {
        audioCtx.close();
    }

    // Mix down to mono at 16 kHz
    const sampleRate   = decoded.sampleRate;
    const numChannels  = decoded.numberOfChannels;
    const numSamples   = decoded.length;

    // Mix channels to mono
    const monoData = new Float32Array(numSamples);
    for(let ch = 0; ch < numChannels; ch++){
        const channelData = decoded.getChannelData(ch);
        for(let i = 0; i < numSamples; i++) monoData[i] += channelData[i];
    }
    if(numChannels > 1) for(let i = 0; i < numSamples; i++) monoData[i] /= numChannels;

    // Convert float32 to int16
    const int16 = new Int16Array(numSamples);
    for(let i = 0; i < numSamples; i++){
        const s = Math.max(-1, Math.min(1, monoData[i]));
        int16[i] = s < 0 ? s * 32768 : s * 32767;
    }

    // Build WAV header
    const wavBuffer    = new ArrayBuffer(44 + int16.byteLength);
    const view         = new DataView(wavBuffer);
    const writeStr     = (offset, str) => { for(let i=0;i<str.length;i++) view.setUint8(offset+i, str.charCodeAt(i)); };
    const bitsPerSample = 16;
    const byteRate      = sampleRate * 1 * bitsPerSample / 8;
    const blockAlign    = 1 * bitsPerSample / 8;

    writeStr(0, 'RIFF');
    view.setUint32(4,  36 + int16.byteLength, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);           // PCM chunk size
    view.setUint16(20, 1, true);            // PCM format
    view.setUint16(22, 1, true);            // 1 channel (mono)
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeStr(36, 'data');
    view.setUint32(40, int16.byteLength, true);
    new Int16Array(wavBuffer, 44).set(int16);

    return new Blob([wavBuffer], { type: 'audio/wav' });
}

async function stopAndSendRecording(){
    if(!mediaRecorder || mediaRecorder.state === 'inactive') return;

    // Collect final data then stop
    const rawBlob = await new Promise(resolve => {
        mediaRecorder.onstop = () => resolve(
            new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
        );
        _stopMic();
    });
    clearInterval(recTimerInterval);

    if(rawBlob.size < 500){
        showToast('⚠️ Recording too short, try again');
        hideRecordingBar();
        return;
    }

    const sendBtn = document.getElementById('recSendBtn');
    sendBtn.classList.add('uploading');
    document.getElementById('recTimer').textContent = '⏳';

    // ── Convert to real WAV (Meta-compatible) ──────────────────
    let wavBlob;
    try {
        wavBlob = await blobToWav(rawBlob);
    } catch(e) {
        // Fallback: send raw blob if decode fails (e.g. very short clip)
        console.warn('WAV conversion failed, sending raw:', e);
        wavBlob = rawBlob;
    }

    const filename = `voice_${Date.now()}.wav`;
    const file     = new File([wavBlob], filename, { type: 'audio/wav' });

    // ── Step 1: Upload to Meta ─────────────────────────────────
    const fd = new FormData();
    fd.append('file', file, filename);
    let media_id;
    try {
        const upRes  = await fetch('/api/upload_media', { method: 'POST', body: fd });
        const upData = await upRes.json();
        if(upData.error){
            const msg = typeof upData.error === 'string'
                ? upData.error
                : (upData.error.message || upData.error.type || JSON.stringify(upData.error));
            throw new Error(msg);
        }
        media_id = upData.media_id;
    } catch(e){
        showToast('⚠️ Upload failed: ' + e.message, 4000);
        sendBtn.classList.remove('uploading');
        document.getElementById('recTimer').textContent = recSeconds + 's';
        return;
    }

    // ── Step 2: Send WhatsApp audio message ───────────────────
    try {
        const res  = await fetch('/api/send_audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: activePhone, media_id })
        });
        const data = await res.json();
        if(data.error){
            const msg = typeof data.error === 'string' ? data.error : (data.error.message || JSON.stringify(data.error));
            throw new Error(msg);
        }
        showToast('🎙️ Voice note sent!');
        loadMessages(); loadChats();
    } catch(e){
        showToast('⚠️ Send failed: ' + e.message, 3500);
    } finally {
        sendBtn.classList.remove('uploading');
        hideRecordingBar();
    }
}

function hideRecordingBar(){
    document.getElementById('recordingBar').classList.remove('active');
    document.getElementById('attachBtn').style.visibility    = '';
    document.getElementById('messageInput').style.visibility = '';
    document.getElementById('micBtn').style.visibility       = '';
    onInputChange();
}

// ── INTERACTIVE MESSAGES ──────────────────────────────────────
function toggleInteractiveFields() {
    const t = document.getElementById('int-type').value;
    const s = (id, show) => document.getElementById(id).style.display = show ? 'flex' : 'none';
    const sBlock = (id, show) => document.getElementById(id).style.display = show ? 'block' : 'none';

    // Reset all specific fields
    sBlock('int-f-button_text', false);
    sBlock('int-f-sections', false);
    s('int-f-buttons', false);
    s('int-f-catalog', false);
    s('int-f-address', false);
    s('int-f-flow1', false);
    s('int-f-flow2', false);
    s('int-f-header-footer', true); // Most support header/footer

    if(t === 'list') {
        sBlock('int-f-button_text', true);
        sBlock('int-f-sections', true);
    } else if(t === 'button') {
        s('int-f-buttons', true);
    } else if(t === 'product') {
        s('int-f-catalog', true);
    } else if(t === 'product_list') {
        sBlock('int-f-sections', true);
        s('int-f-catalog', true);
    } else if(t === 'catalog_message') {
        s('int-f-catalog', true); // reuse product_id for thumb_id
        s('int-f-header-footer', false);
    } else if(t === 'location_request_message') {
        s('int-f-header-footer', false);
    } else if(t === 'address_message') {
        s('int-f-address', true);
        s('int-f-header-footer', false);
    } else if(t === 'flow') {
        s('int-f-flow1', true);
        s('int-f-flow2', true);
    }
}

async function sendInteractiveMsg() {
    if(!activePhone){ showToast('⚠️ Select a conversation first'); return; }
    
    const btn = document.getElementById('send-interactive-btn');
    const oldHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Sending...';

    const t = document.getElementById('int-type').value;
    const payload = {
        phone: activePhone,
        itype: t,
        body: document.getElementById('int-body').value.trim(),
        header: document.getElementById('int-header').value.trim(),
        footer: document.getElementById('int-footer').value.trim()
    };

    try {
        if(t === 'list' || t === 'product_list') {
            const raw = document.getElementById('int-sections').value.trim();
            if(!raw) throw new Error("Sections JSON is required");
            try { payload.sections = JSON.parse(raw); } catch(e) { throw new Error("Invalid JSON in sections"); }
            if(t === 'list') payload.button_text = document.getElementById('int-button_text').value.trim();
            if(t === 'product_list') payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
        } else if(t === 'button') {
            const b1 = document.getElementById('int-btn1').value.trim();
            const b2 = document.getElementById('int-btn2').value.trim();
            const b3 = document.getElementById('int-btn3').value.trim();
            const arr = [];
            if(b1) arr.push({id: "btn1", title: b1});
            if(b2) arr.push({id: "btn2", title: b2});
            if(b3) arr.push({id: "btn3", title: b3});
            payload.buttons = arr;
        } else if(t === 'product') {
            payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
            payload.product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'catalog_message') {
            payload.thumbnail_product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'address_message') {
            payload.country_code = document.getElementById('int-country_code').value.trim();
        } else if(t === 'flow') {
            payload.flow_id = document.getElementById('int-flow_id').value.trim();
            payload.cta_text = document.getElementById('int-flow_cta').value.trim();
            payload.screen = document.getElementById('int-flow_screen').value.trim();
            payload.flow_token = document.getElementById('int-flow_token').value.trim();
        }

        const res = await fetch('/api/send_interactive_msg', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('✅ Interactive message sent!');
        closeModal('interactive');
        
        // Reset form completely
        document.getElementById('int-body').value = '';
        document.getElementById('int-header').value = '';
        document.getElementById('int-footer').value = '';
        document.getElementById('int-sections').value = '';
        
        loadMessages(); loadChats();
    } catch(e) {
        showToast('⚠️ Send failed: ' + e.message, 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
    }
}

// ── INTERACTIVE TEMPLATES ──────────────────────────────────────
let cachedIntTemplates = [];

async function fetchInteractiveTemplates() {
    try {
        const res = await fetch('/api/interactive_templates');
        cachedIntTemplates = await res.json();
        renderTemplateList();
    } catch(e) {
        console.error('Failed to load templates', e);
    }
}

function renderTemplateList() {
    const typeNode = document.getElementById('int-type');
    if(!typeNode) return;
    const type = typeNode.value;
    const listDiv = document.getElementById('int-template-list');
    if (!listDiv) return;
    
    listDiv.innerHTML = '';
    const filtered = cachedIntTemplates.filter(t => t.itype === type);
    
    if(filtered.length === 0) {
        listDiv.innerHTML = '<div style="color:var(--text-3); font-size:12px; text-align:center; padding:10px;">No saved templates for this type.</div>';
        return;
    }
    
    filtered.forEach(t => {
        const row = document.createElement('div');
        row.style.cssText = "background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:8px;";
        
        row.innerHTML = `
            <div style="font-size:14px; font-weight:600; color:var(--text-1);">${t.name}</div>
            <div style="display:flex; gap:6px;">
                <button onclick="sendInteractiveMsgDirectly(${t.id})" style="flex:1; padding:6px; background:var(--green); border:none; border-radius:6px; color:white; cursor:pointer; font-weight:500; font-size:12px; transition:transform 0.1s;">Send</button>
                <button onclick="openTemplateForm(${t.id})" style="flex:1; padding:6px; background:rgba(255,255,255,0.1); border:none; border-radius:6px; color:var(--text-1); cursor:pointer; font-weight:500; font-size:12px;">Edit</button>
                <button onclick="deleteInteractiveTemplate(${t.id})" style="flex:1; padding:6px; background:rgba(255,107,107,0.15); border:none; border-radius:6px; color:var(--danger); cursor:pointer; font-weight:500; font-size:12px;">Delete</button>
            </div>
        `;
        listDiv.appendChild(row);
    });
}

function openTemplateForm(idOrNew) {
    try {
        document.getElementById('int-template-list').style.display = 'none';
        document.getElementById('btn-create-new-template').style.display = 'none';
        document.getElementById('int-form-wrapper').style.display = 'block';
        
        document.querySelectorAll('#modal-interactive input:not([type="hidden"]), #modal-interactive textarea').forEach(el => {
            el.value = '';
        });
        
        if(idOrNew === 'new') {
            document.getElementById('int-editing-id').value = '';
            toggleInteractiveFields();
            return;
        }
        
        document.getElementById('int-editing-id').value = idOrNew;
        const t = cachedIntTemplates.find(x => x.id == idOrNew);
        if(!t) return;
        
        document.getElementById('int-body').value = t.payload.body || '';
        document.getElementById('int-header').value = t.payload.header || '';
        document.getElementById('int-footer').value = t.payload.footer || '';
        
        if(t.itype === 'list') {
            document.getElementById('int-button_text').value = t.payload.button_text || '';
            document.getElementById('int-sections').value = JSON.stringify(t.payload.sections || [], null, 2);
        } else if(t.itype === 'button') {
            if(t.payload.buttons && t.payload.buttons[0]) document.getElementById('int-btn1').value = t.payload.buttons[0].title;
            if(t.payload.buttons && t.payload.buttons[1]) document.getElementById('int-btn2').value = t.payload.buttons[1].title;
            if(t.payload.buttons && t.payload.buttons[2]) document.getElementById('int-btn3').value = t.payload.buttons[2].title;
        } else if(t.itype === 'product' || t.itype === 'catalog_message') {
            document.getElementById('int-catalog_id').value = t.payload.catalog_id || '';
            document.getElementById('int-product_id').value = t.payload.product_retailer_id || t.payload.thumbnail_product_retailer_id || '';
        } else if(t.itype === 'product_list') {
            document.getElementById('int-catalog_id').value = t.payload.catalog_id || '';
            document.getElementById('int-sections').value = JSON.stringify(t.payload.sections || [], null, 2);
        } else if(t.itype === 'address_message') {
            document.getElementById('int-country_code').value = t.payload.country_code || '';
        } else if(t.itype === 'flow') {
            document.getElementById('int-flow_id').value = t.payload.flow_id || '';
            document.getElementById('int-flow_cta').value = t.payload.cta_text || '';
            document.getElementById('int-flow_screen').value = t.payload.screen || '';
            document.getElementById('int-flow_token').value = t.payload.flow_token || '';
        }
        toggleInteractiveFields();
    } catch(e) {
        alert("Error opening form: " + e.message);
    }
}

function closeTemplateForm() {
    document.getElementById('int-template-list').style.display = 'flex';
    document.getElementById('btn-create-new-template').style.display = 'block';
    document.getElementById('int-form-wrapper').style.display = 'none';
}

async function deleteInteractiveTemplate(id) {
    if(!confirm("Are you sure you want to delete this template?")) return;
    try {
        const res = await fetch('/api/interactive_templates/' + id, {method: 'DELETE'});
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        showToast('✅ Template deleted');
        fetchInteractiveTemplates();
    } catch(e) {
        showToast('⚠️ Delete failed: ' + e.message);
    }
}

async function sendInteractiveMsgDirectly(id) {
    if(!activePhone){ showToast('⚠️ Select a conversation first'); return; }
    const t = cachedIntTemplates.find(x => x.id == id);
    if(!t) return;
    
    const payload = Object.assign({phone: activePhone, itype: t.itype}, t.payload);
    
    try {
        const res = await fetch('/api/send_interactive_msg', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        
        loadMessages(); loadChats();
        closeModal('interactive');
        showToast('✅ Sent successfully');
    } catch(e) {
        showToast('⚠️ Send failed: ' + e.message, 5000);
    }
}

async function saveInteractiveTemplate() {
    const t = document.getElementById('int-type').value;
    const editingId = document.getElementById('int-editing-id').value;
    const payload = {
        body: document.getElementById('int-body').value.trim(),
        header: document.getElementById('int-header').value.trim(),
        footer: document.getElementById('int-footer').value.trim()
    };
    
    try {
        if(t === 'list' || t === 'product_list') {
            const raw = document.getElementById('int-sections').value.trim();
            if(raw) payload.sections = JSON.parse(raw);
            if(t === 'list') payload.button_text = document.getElementById('int-button_text').value.trim();
            if(t === 'product_list') payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
        } else if(t === 'button') {
            const b1 = document.getElementById('int-btn1').value.trim();
            const b2 = document.getElementById('int-btn2').value.trim();
            const b3 = document.getElementById('int-btn3').value.trim();
            const arr = [];
            if(b1) arr.push({id: "btn1", title: b1});
            if(b2) arr.push({id: "btn2", title: b2});
            if(b3) arr.push({id: "btn3", title: b3});
            payload.buttons = arr;
        } else if(t === 'product') {
            payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
            payload.product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'catalog_message') {
            payload.thumbnail_product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'address_message') {
            payload.country_code = document.getElementById('int-country_code').value.trim();
        } else if(t === 'flow') {
            payload.flow_id = document.getElementById('int-flow_id').value.trim();
            payload.cta_text = document.getElementById('int-flow_cta').value.trim();
            payload.screen = document.getElementById('int-flow_screen').value.trim();
            payload.flow_token = document.getElementById('int-flow_token').value.trim();
        }
        
        let url = '/api/interactive_templates';
        let method = 'POST';
        let reqBody = {itype: t, payload: payload};
        
        if (editingId) {
            url += '/' + editingId;
            method = 'PUT';
        } else {
            const name = prompt('Enter a name for this new template:');
            if(!name) return;
            reqBody.name = name;
        }
        
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(reqBody)
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        
        showToast('✅ Template saved!');
        await fetchInteractiveTemplates();
        closeTemplateForm();
    } catch(e) {
        showToast('⚠️ Save failed: ' + e.message, 4000);
    }
}

// ── POLLING ───────────────────────────────────────────────────
setInterval(()=>{loadChats();loadMessages();},2000);
loadChats();
fetchInteractiveTemplates();
=======

'use strict';

// ── STATE ──────────────────────────────────────────────────────
let activePhone      = null;
let lastMessageCount = 0;
let allChats         = [];
// Per-type: store selected File object
const selectedFiles  = {image:null,video:null,document:null,audio:null,sticker:null};

const appContainer = document.getElementById('appContainer');
const messageArea  = document.getElementById('messageArea');
const scrollBtn    = document.getElementById('scrollBottomBtn');
const attachPopup  = document.getElementById('attachPopup');
const attachBtn    = document.getElementById('attachBtn');

// ── AVATAR ────────────────────────────────────────────────────
const AVC = [['#1a4a3a','#00a884'],['#1e2d5a','#4a80f5'],['#4a1a2a','#e05c8a'],['#3a2a10','#e08040'],['#1a1a4a','#8060e0'],['#0d3d2d','#40c090'],['#3a1010','#e05040'],['#103a3a','#40b0b0']];
function avatarStyle(phone){let h=0;for(let c of(phone||''))h=(h*31+c.charCodeAt(0))&0xffffffff;const[bg,fg]=AVC[Math.abs(h)%AVC.length];return{bg,fg,initials:(phone||'??').replace(/\D/g,'').slice(-2)||'??'};}
function setHeaderAvatar(p){const{bg,fg,initials}=avatarStyle(p);const el=document.getElementById('headerAvatar');el.style.background=bg;el.style.color=fg;el.textContent=initials;}

// ── TIME ──────────────────────────────────────────────────────
function relTime(ts){if(!ts||ts==='now')return'';try{const d=new Date(ts);if(isNaN(d))return'';const diff=(Date.now()-d)/1000;if(diff<60)return'just now';if(diff<3600)return Math.floor(diff/60)+'m';if(diff<86400)return Math.floor(diff/3600)+'h';return d.toLocaleDateString([],{month:'short',day:'numeric'});}catch{return'';}}
function fmtTime(ts){if(!ts||ts==='now')return new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});try{const d=new Date(ts);if(isNaN(d))return'';return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}catch{return'';}}
function fmtBytes(b){if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(1)+' MB';}

// ── UTILS ─────────────────────────────────────────────────────
function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function showToast(msg,dur=2600){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),dur);}
function copyPhone(){if(!activePhone)return;navigator.clipboard.writeText(activePhone).then(()=>showToast('📋 Phone number copied!'));}

// ── SCROLL ────────────────────────────────────────────────────
function scrollToBottom(s=false){messageArea.scrollTo({top:messageArea.scrollHeight,behavior:s?'smooth':'auto'});}
messageArea.addEventListener('scroll',()=>{scrollBtn.classList.toggle('visible',(messageArea.scrollHeight-messageArea.scrollTop-messageArea.clientHeight)>120);});

// ── ATTACH POPUP ──────────────────────────────────────────────
function toggleAttachPopup(){const o=attachPopup.classList.toggle('visible');attachBtn.classList.toggle('open',o);}
document.addEventListener('click',e=>{if(!attachBtn.contains(e.target)&&!attachPopup.contains(e.target)){attachPopup.classList.remove('visible');attachBtn.classList.remove('open');}});

// ── MODALS ────────────────────────────────────────────────────
function openModal(t){attachPopup.classList.remove('visible');attachBtn.classList.remove('open');document.getElementById('modal-'+t).classList.add('active');}
function closeModal(t){document.getElementById('modal-'+t).classList.remove('active');}
document.querySelectorAll('.modal-overlay').forEach(o=>o.addEventListener('click',e=>{if(e.target===o)o.classList.remove('active');}));
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.modal-overlay.active').forEach(o=>o.classList.remove('active'));});

// ── FILE DROP ZONE ────────────────────────────────────────────
function onDragOver(e,type){e.preventDefault();document.getElementById('fdz-'+type).classList.add('drag-over');}
function onDragLeave(type){document.getElementById('fdz-'+type).classList.remove('drag-over');}
function onDrop(e,type){e.preventDefault();onDragLeave(type);const file=e.dataTransfer.files[0];if(file){const inp=document.getElementById('file-'+type);const dt=new DataTransfer();dt.items.add(file);inp.files=dt.files;onFileSelect(type);}}
function changeFile(type){document.getElementById('file-'+type).click();}

function onFileSelect(type){
    const inp=document.getElementById('file-'+type);
    if(!inp.files||!inp.files[0])return;
    const file=inp.files[0];
    selectedFiles[type]=file;

    // Hide drop zone, show preview
    document.getElementById('fdz-'+type).style.display='none';
    const prev=document.getElementById('prev-'+type);
    prev.classList.add('visible');

    // Fill in name + size
    const nameEl=document.getElementById('prev-'+type+'-name');
    const sizeEl=document.getElementById('prev-'+type+'-size');
    if(nameEl) nameEl.textContent=file.name;
    if(sizeEl) sizeEl.textContent=fmtBytes(file.size);

    // Image/sticker: show thumbnail
    if(type==='image'||type==='sticker'){
        const thumb=document.getElementById('prev-'+type+'-thumb');
        if(thumb){const reader=new FileReader();reader.onload=e=>thumb.src=e.target.result;reader.readAsDataURL(file);}
    }

    // Enable send button
    document.getElementById('send-'+type+'-btn').disabled=false;

    // Reset progress
    resetProgress(type);
}

function resetProgress(type){
    const p=document.getElementById('prog-'+type);
    if(!p)return;
    p.classList.remove('visible');
    document.getElementById('prog-'+type+'-bar').style.width='0%';
    document.getElementById('prog-'+type+'-pct').textContent='0%';
    document.getElementById('prog-'+type+'-status').textContent='';
}

// ── UPLOAD + SEND (2-step for file types) ────────────────────
async function sendWithUpload(type){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const file=selectedFiles[type];
    if(!file){showToast('⚠️ Please select a file first');return;}

    const sendBtn=document.getElementById('send-'+type+'-btn');
    sendBtn.disabled=true;
    sendBtn.innerHTML=`<svg style="animation:spin .8s linear infinite;width:15px;height:15px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Uploading…`;

    // Show progress bar
    const prog=document.getElementById('prog-'+type);
    prog.classList.add('visible');
    const bar=document.getElementById('prog-'+type+'-bar');
    const pct=document.getElementById('prog-'+type+'-pct');
    const stat=document.getElementById('prog-'+type+'-status');

    // ── STEP 1: Upload to Meta via XHR (so we can track progress) ──
    let media_id;
    try {
        const fd=new FormData();
        fd.append('file',file,file.name);

        media_id = await new Promise((resolve,reject)=>{
            const xhr=new XMLHttpRequest();
            xhr.open('POST','/api/upload_media');
            xhr.upload.onprogress=e=>{
                if(e.lengthComputable){
                    const p=Math.round(e.loaded/e.total*90); // 90% for upload, 10% for send
                    bar.style.width=p+'%';
                    pct.textContent=p+'%';
                }
            };
            xhr.onload=()=>{
                const data=JSON.parse(xhr.responseText);
                if(data.error){reject(new Error(data.error));}
                else{resolve(data.media_id);}
            };
            xhr.onerror=()=>reject(new Error('Network error during upload'));
            xhr.send(fd);
        });
    } catch(e) {
        showToast('⚠️ Upload failed: '+e.message, 3500);
        stat.textContent='❌ Upload failed: '+e.message;
        sendBtn.disabled=false;
        sendBtn.innerHTML=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:15px;height:15px" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Send`;
        return;
    }

    // ── STEP 2: Send the message using the media_id ──
    bar.style.width='95%'; pct.textContent='95%'; stat.textContent='Sending…';

    const endpointMap={image:'/api/send_image',video:'/api/send_video',document:'/api/send_document',audio:'/api/send_audio',sticker:'/api/send_sticker'};
    const body={phone:activePhone,media_id};

    // Extra fields per type
    if(type==='image')    body.caption = (document.getElementById('img-caption')||{}).value||'';
    if(type==='video')    body.caption = (document.getElementById('vid-caption')||{}).value||'';
    if(type==='document'){body.caption = (document.getElementById('doc-caption')||{}).value||'';body.filename=file.name;}
    if(type==='audio')    {} // no extra
    if(type==='sticker')  {} // no extra

    try {
        const res=await fetch(endpointMap[type],{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data=await res.json();
        if(data.error){
            stat.textContent='❌ Send failed: '+data.error;
            showToast('⚠️ Send failed: '+data.error,3500);
        } else {
            bar.style.width='100%'; pct.textContent='100%'; stat.textContent='✅ Sent!';
            showToast('✅ '+type.charAt(0).toUpperCase()+type.slice(1)+' sent!');
            // Reset modal after a short delay
            setTimeout(()=>{closeModal(type);resetModalState(type);},800);
            loadMessages(); loadChats();
        }
    } catch(e) {
        stat.textContent='❌ Network error';
        showToast('⚠️ Network error while sending');
    } finally {
        sendBtn.disabled=false;
        const lbl=type.charAt(0).toUpperCase()+type.slice(1);
        sendBtn.innerHTML=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:15px;height:15px" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Send ${lbl}`;
    }
}

function resetModalState(type){
    selectedFiles[type]=null;
    const fdz=document.getElementById('fdz-'+type);
    if(fdz) fdz.style.display='';
    const prev=document.getElementById('prev-'+type);
    if(prev) prev.classList.remove('visible');
    const inp=document.getElementById('file-'+type);
    if(inp) inp.value='';
    const sb=document.getElementById('send-'+type+'-btn');
    if(sb) sb.disabled=true;
    resetProgress(type);
    // Clear captions
    const cap=document.getElementById(type.substring(0,3)+'-caption');
    if(cap) cap.value='';
}

// ── LOCATION ──────────────────────────────────────────────────
async function sendLocation(){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const lat=document.getElementById('loc-lat').value.trim();
    const lng=document.getElementById('loc-lng').value.trim();
    if(!lat||!lng){showToast('⚠️ Latitude and Longitude are required');return;}
    await simpleSend('/api/send_location',{phone:activePhone,latitude:parseFloat(lat),longitude:parseFloat(lng),name:document.getElementById('loc-name').value.trim(),address:document.getElementById('loc-address').value.trim()},'location','📍 Location sent!');
}

// ── CATALOG ───────────────────────────────────────────────────
async function sendCatalog(){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const body={phone:activePhone,body:document.getElementById('cat-body').value.trim()};
    const th=document.getElementById('cat-thumb').value.trim();
    if(th) body.thumbnail_product_id=th;
    await simpleSend('/api/send_catalog',body,'catalog','🛍️ Catalog sent!');
}

// ── QUICK REPLY ───────────────────────────────────────────────
async function sendQuickReply(){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const bodyText=document.getElementById('qr-body').value.trim();
    if(!bodyText){showToast('⚠️ Message body is required');return;}
    const rows=document.getElementById('qrButtonsWrap').querySelectorAll('.qr-btn-row');
    const buttons={};let valid=true;
    rows.forEach(r=>{const id=r.querySelector('[data-role=id]').value.trim();const t=r.querySelector('[data-role=title]').value.trim();if(!id||!t){valid=false;}else{buttons[id]=t;}});
    if(!valid||Object.keys(buttons).length===0){showToast('⚠️ Fill in all button IDs and labels');return;}
    await simpleSend('/api/send_quick_reply',{phone:activePhone,text:bodyText,buttons},'quickreply','⚡ Quick reply sent!');
}

// ── GENERIC SIMPLE SEND (no upload) ──────────────────────────
async function simpleSend(endpoint,body,modalType,successMsg){
    try{
        const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data=await res.json();
        if(data.error){showToast('⚠️ '+data.error,3500);}
        else{showToast(successMsg);closeModal(modalType);loadMessages();loadChats();}
    }catch(e){showToast('⚠️ Network error');console.error(e);}
}

// ── QUICK REPLY BUILDER ───────────────────────────────────────
function addQrRow(){const w=document.getElementById('qrButtonsWrap');if(w.querySelectorAll('.qr-btn-row').length>=3){showToast('⚠️ Max 3 buttons');return;}const r=document.createElement('div');r.className='qr-btn-row';r.innerHTML=`<input class="form-input qr-id-inp" placeholder="ID" data-role="id"><input class="form-input" placeholder="Label" data-role="title"><button class="qr-remove" onclick="removeQrRow(this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>`;w.appendChild(r);updateQrCounter();}
function removeQrRow(b){b.closest('.qr-btn-row').remove();updateQrCounter();}
function updateQrCounter(){const n=document.getElementById('qrButtonsWrap').querySelectorAll('.qr-btn-row').length;document.getElementById('qrCounter').textContent=`${n} / 3 buttons`;document.getElementById('addQrBtn').style.display=n>=3?'none':'flex';}

// ── QUICK ACTIONS (menu / order booking) ─────────────────────
async function qaAction(action){
    if(!activePhone){showToast('⚠️ Select a conversation first');return;}
    const id=action==='menu'?'qaMenuBtn':'qaOrderBtn';
    const ep=action==='menu'?'/api/send_menu':'/api/send_order_booking';
    const btn=document.getElementById(id);
    btn.classList.add('loading');
    try{
        const res=await fetch(ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:activePhone})});
        const data=await res.json();
        if(data.error){showToast('⚠️ '+data.error,3000);}
        else{btn.classList.add('success');showToast('✅ Sent!');loadMessages();loadChats();}
    }catch(e){showToast('⚠️ Network error');}
    finally{btn.classList.remove('loading');setTimeout(()=>btn.classList.remove('success'),2000);}
}

// ── LOAD CHATS ────────────────────────────────────────────────
async function loadChats(){
    try{const r=await fetch('/api/chats');allChats=await r.json();renderChatList(allChats);}
    catch(e){console.error('loadChats:',e);}
}
function renderChatList(chats){
    const el=document.getElementById('chatList');
    if(!chats||!chats.length){el.innerHTML='<div class="sidebar-empty"><p>No conversations yet.<br>Messages will appear here.</p></div>';return;}
    el.innerHTML=chats.map(c=>{const{bg,fg,initials}=avatarStyle(c.phone);const a=c.phone===activePhone?'active':'';return`<div class="chat-item ${a}" onclick="selectChat('${esc(c.phone)}')"><div class="avatar" style="width:46px;height:46px;font-size:16px;background:${bg};color:${fg};">${initials}</div><div class="chat-item-body"><div class="chat-item-top"><div class="phone-num">${esc(c.phone)}</div>${c.timestamp?`<div class="chat-time">${relTime(c.timestamp)}</div>`:''}</div><div class="preview-txt">${esc(c.last_message||'')}</div></div></div>`;}).join('');
}
function filterChats(q){q=q.trim().toLowerCase();renderChatList(q?allChats.filter(c=>c.phone.toLowerCase().includes(q)):allChats);}

// ── CHAT SELECTION ────────────────────────────────────────────
function selectChat(phone){activePhone=phone;lastMessageCount=0;document.getElementById('placeholderView').style.display='none';document.getElementById('activeChatContent').style.display='flex';document.getElementById('currentChatPhone').innerText=phone;setHeaderAvatar(phone);appContainer.classList.add('show-chat');loadMessages();loadChats();}
function goBackToList(){appContainer.classList.remove('show-chat');activePhone=null;}

// ── LOAD MESSAGES ─────────────────────────────────────────────
async function loadMessages(){
    if(!activePhone)return;
    try{
        const r=await fetch(`/api/messages/${activePhone}`);
        const msgs=await r.json();
        if(msgs.length===lastMessageCount)return;
        const atBottom=(messageArea.scrollHeight-messageArea.scrollTop-messageArea.clientHeight)<80;
        messageArea.innerHTML='';
        let lastDate=null;
        msgs.forEach(msg=>{
            const lbl='Today';
            if(lbl!==lastDate){lastDate=lbl;const sep=document.createElement('div');sep.className='date-separator';sep.innerHTML=`<div class="date-pill">${lbl}</div>`;messageArea.appendChild(sep);}
            const isOut=msg.type!=='incoming';
            const div=document.createElement('div');div.className=`msg ${isOut?'outgoing':'incoming'}`;
            const tick=isOut?`<span class="msg-tick"><svg viewBox="0 0 16 11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 5 4 8 9 2"/><polyline points="6 5 9 8 14 2"/></svg></span>`:'';
            div.innerHTML=`<div>${esc(msg.text)}</div><div class="msg-footer"><span class="msg-time">${fmtTime(msg.timestamp)}</span>${tick}</div>`;
            messageArea.appendChild(div);
        });
        if(atBottom||lastMessageCount===0)scrollToBottom(false);
        lastMessageCount=msgs.length;
    }catch(e){console.error('loadMessages:',e);}
}

// ── SEND TEXT ─────────────────────────────────────────────────
async function sendMessage(){
    const inp=document.getElementById('messageInput');
    const btn=document.getElementById('sendBtn');
    const text=inp.value.trim();
    if(!text||!activePhone)return;
    inp.value='';inp.focus();
    btn.classList.add('sending');setTimeout(()=>btn.classList.remove('sending'),400);
    try{await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:activePhone,message:text})});loadMessages();loadChats();}
    catch(e){console.error('sendMessage:',e);}
}

// ── INPUT TOGGLE (mic ↔ send arrow) ──────────────────────────
function onInputChange(){
    const hasText = document.getElementById('messageInput').value.trim().length > 0;
    document.getElementById('sendBtn').classList.toggle('hidden', !hasText);
    document.getElementById('micBtn').classList.toggle('hidden',  hasText);
}

// ── VOICE NOTE RECORDING ──────────────────────────────────────
let mediaRecorder    = null;
let audioChunks      = [];
let recTimerInterval = null;
let recSeconds       = 0;
let micStream        = null;  // keep reference for proper cleanup

async function startRecording(){
    if(!activePhone){ showToast('⚠️ Select a conversation first'); return; }

    // Request microphone
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch(e) {
        if(e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError')
            showToast('⚠️ Microphone access denied — allow it in browser settings');
        else
            showToast('⚠️ Could not access microphone: ' + e.message);
        return;
    }

    // Pick best supported mimeType — prefer webm/opus (Chrome), then ogg/opus (Firefox), then mp4 (Safari)
    const mimeType = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4','']
        .find(t => t === '' || MediaRecorder.isTypeSupported(t));

    audioChunks = [];
    try {
        mediaRecorder = new MediaRecorder(micStream, mimeType ? { mimeType } : {});
    } catch(e) {
        mediaRecorder = new MediaRecorder(micStream);
    }
    mediaRecorder.ondataavailable = e => { if(e.data && e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.start(100);

    // Show recording bar
    document.getElementById('recordingBar').classList.add('active');
    document.getElementById('attachBtn').style.visibility    = 'hidden';
    document.getElementById('messageInput').style.visibility = 'hidden';
    document.getElementById('sendBtn').style.visibility      = 'hidden';
    document.getElementById('micBtn').style.visibility       = 'hidden';

    // Start timer
    recSeconds = 0;
    document.getElementById('recTimer').textContent = '0:00';
    recTimerInterval = setInterval(() => {
        recSeconds++;
        const m = Math.floor(recSeconds / 60);
        const s = String(recSeconds % 60).padStart(2, '0');
        document.getElementById('recTimer').textContent = `${m}:${s}`;
        if(recSeconds >= 300) stopAndSendRecording(); // 5-min WhatsApp limit
    }, 1000);
}

function cancelRecording(){
    _stopMic();
    clearInterval(recTimerInterval);
    audioChunks = [];
    hideRecordingBar();
    showToast('🗑️ Recording cancelled');
}

function _stopMic(){
    if(mediaRecorder && mediaRecorder.state !== 'inactive') {
        try { mediaRecorder.stop(); } catch(_){}
    }
    if(micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
    }
}

// ── WAV encoder (Web Audio API → raw 16-bit PCM WAV) ──────────
// This converts ANY browser audio blob (webm/ogg/mp4) into a
// proper WAV file that Meta WhatsApp API accepts and delivers.
async function blobToWav(blob){
    const arrayBuf  = await blob.arrayBuffer();
    const audioCtx  = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    let decoded;
    try {
        decoded = await audioCtx.decodeAudioData(arrayBuf);
    } finally {
        audioCtx.close();
    }

    // Mix down to mono at 16 kHz
    const sampleRate   = decoded.sampleRate;
    const numChannels  = decoded.numberOfChannels;
    const numSamples   = decoded.length;

    // Mix channels to mono
    const monoData = new Float32Array(numSamples);
    for(let ch = 0; ch < numChannels; ch++){
        const channelData = decoded.getChannelData(ch);
        for(let i = 0; i < numSamples; i++) monoData[i] += channelData[i];
    }
    if(numChannels > 1) for(let i = 0; i < numSamples; i++) monoData[i] /= numChannels;

    // Convert float32 to int16
    const int16 = new Int16Array(numSamples);
    for(let i = 0; i < numSamples; i++){
        const s = Math.max(-1, Math.min(1, monoData[i]));
        int16[i] = s < 0 ? s * 32768 : s * 32767;
    }

    // Build WAV header
    const wavBuffer    = new ArrayBuffer(44 + int16.byteLength);
    const view         = new DataView(wavBuffer);
    const writeStr     = (offset, str) => { for(let i=0;i<str.length;i++) view.setUint8(offset+i, str.charCodeAt(i)); };
    const bitsPerSample = 16;
    const byteRate      = sampleRate * 1 * bitsPerSample / 8;
    const blockAlign    = 1 * bitsPerSample / 8;

    writeStr(0, 'RIFF');
    view.setUint32(4,  36 + int16.byteLength, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);           // PCM chunk size
    view.setUint16(20, 1, true);            // PCM format
    view.setUint16(22, 1, true);            // 1 channel (mono)
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeStr(36, 'data');
    view.setUint32(40, int16.byteLength, true);
    new Int16Array(wavBuffer, 44).set(int16);

    return new Blob([wavBuffer], { type: 'audio/wav' });
}

async function stopAndSendRecording(){
    if(!mediaRecorder || mediaRecorder.state === 'inactive') return;

    // Collect final data then stop
    const rawBlob = await new Promise(resolve => {
        mediaRecorder.onstop = () => resolve(
            new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
        );
        _stopMic();
    });
    clearInterval(recTimerInterval);

    if(rawBlob.size < 500){
        showToast('⚠️ Recording too short, try again');
        hideRecordingBar();
        return;
    }

    const sendBtn = document.getElementById('recSendBtn');
    sendBtn.classList.add('uploading');
    document.getElementById('recTimer').textContent = '⏳';

    // ── Convert to real WAV (Meta-compatible) ──────────────────
    let wavBlob;
    try {
        wavBlob = await blobToWav(rawBlob);
    } catch(e) {
        // Fallback: send raw blob if decode fails (e.g. very short clip)
        console.warn('WAV conversion failed, sending raw:', e);
        wavBlob = rawBlob;
    }

    const filename = `voice_${Date.now()}.wav`;
    const file     = new File([wavBlob], filename, { type: 'audio/wav' });

    // ── Step 1: Upload to Meta ─────────────────────────────────
    const fd = new FormData();
    fd.append('file', file, filename);
    let media_id;
    try {
        const upRes  = await fetch('/api/upload_media', { method: 'POST', body: fd });
        const upData = await upRes.json();
        if(upData.error){
            const msg = typeof upData.error === 'string'
                ? upData.error
                : (upData.error.message || upData.error.type || JSON.stringify(upData.error));
            throw new Error(msg);
        }
        media_id = upData.media_id;
    } catch(e){
        showToast('⚠️ Upload failed: ' + e.message, 4000);
        sendBtn.classList.remove('uploading');
        document.getElementById('recTimer').textContent = recSeconds + 's';
        return;
    }

    // ── Step 2: Send WhatsApp audio message ───────────────────
    try {
        const res  = await fetch('/api/send_audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: activePhone, media_id })
        });
        const data = await res.json();
        if(data.error){
            const msg = typeof data.error === 'string' ? data.error : (data.error.message || JSON.stringify(data.error));
            throw new Error(msg);
        }
        showToast('🎙️ Voice note sent!');
        loadMessages(); loadChats();
    } catch(e){
        showToast('⚠️ Send failed: ' + e.message, 3500);
    } finally {
        sendBtn.classList.remove('uploading');
        hideRecordingBar();
    }
}

function hideRecordingBar(){
    document.getElementById('recordingBar').classList.remove('active');
    document.getElementById('attachBtn').style.visibility    = '';
    document.getElementById('messageInput').style.visibility = '';
    document.getElementById('micBtn').style.visibility       = '';
    onInputChange();
}

// ── INTERACTIVE MESSAGES ──────────────────────────────────────
function toggleInteractiveFields() {
    const t = document.getElementById('int-type').value;
    const s = (id, show) => document.getElementById(id).style.display = show ? 'flex' : 'none';
    const sBlock = (id, show) => document.getElementById(id).style.display = show ? 'block' : 'none';

    // Reset all specific fields
    sBlock('int-f-button_text', false);
    sBlock('int-f-sections', false);
    s('int-f-buttons', false);
    s('int-f-catalog', false);
    s('int-f-address', false);
    s('int-f-flow1', false);
    s('int-f-flow2', false);
    s('int-f-header-footer', true); // Most support header/footer

    if(t === 'list') {
        sBlock('int-f-button_text', true);
        sBlock('int-f-sections', true);
    } else if(t === 'button') {
        s('int-f-buttons', true);
    } else if(t === 'product') {
        s('int-f-catalog', true);
    } else if(t === 'product_list') {
        sBlock('int-f-sections', true);
        s('int-f-catalog', true);
    } else if(t === 'catalog_message') {
        s('int-f-catalog', true); // reuse product_id for thumb_id
        s('int-f-header-footer', false);
    } else if(t === 'location_request_message') {
        s('int-f-header-footer', false);
    } else if(t === 'address_message') {
        s('int-f-address', true);
        s('int-f-header-footer', false);
    } else if(t === 'flow') {
        s('int-f-flow1', true);
        s('int-f-flow2', true);
    }
}

async function sendInteractiveMsg() {
    if(!activePhone){ showToast('⚠️ Select a conversation first'); return; }
    
    const btn = document.getElementById('send-interactive-btn');
    const oldHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Sending...';

    const t = document.getElementById('int-type').value;
    const payload = {
        phone: activePhone,
        itype: t,
        body: document.getElementById('int-body').value.trim(),
        header: document.getElementById('int-header').value.trim(),
        footer: document.getElementById('int-footer').value.trim()
    };

    try {
        if(t === 'list' || t === 'product_list') {
            const raw = document.getElementById('int-sections').value.trim();
            if(!raw) throw new Error("Sections JSON is required");
            try { payload.sections = JSON.parse(raw); } catch(e) { throw new Error("Invalid JSON in sections"); }
            if(t === 'list') payload.button_text = document.getElementById('int-button_text').value.trim();
            if(t === 'product_list') payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
        } else if(t === 'button') {
            const b1 = document.getElementById('int-btn1').value.trim();
            const b2 = document.getElementById('int-btn2').value.trim();
            const b3 = document.getElementById('int-btn3').value.trim();
            const arr = [];
            if(b1) arr.push({id: "btn1", title: b1});
            if(b2) arr.push({id: "btn2", title: b2});
            if(b3) arr.push({id: "btn3", title: b3});
            payload.buttons = arr;
        } else if(t === 'product') {
            payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
            payload.product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'catalog_message') {
            payload.thumbnail_product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'address_message') {
            payload.country_code = document.getElementById('int-country_code').value.trim();
        } else if(t === 'flow') {
            payload.flow_id = document.getElementById('int-flow_id').value.trim();
            payload.cta_text = document.getElementById('int-flow_cta').value.trim();
            payload.screen = document.getElementById('int-flow_screen').value.trim();
            payload.flow_token = document.getElementById('int-flow_token').value.trim();
        }

        const res = await fetch('/api/send_interactive_msg', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('✅ Interactive message sent!');
        closeModal('interactive');
        
        // Reset form completely
        document.getElementById('int-body').value = '';
        document.getElementById('int-header').value = '';
        document.getElementById('int-footer').value = '';
        document.getElementById('int-sections').value = '';
        
        loadMessages(); loadChats();
    } catch(e) {
        showToast('⚠️ Send failed: ' + e.message, 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
    }
}

// ── INTERACTIVE TEMPLATES ──────────────────────────────────────
let cachedIntTemplates = [];

async function fetchInteractiveTemplates() {
    try {
        const res = await fetch('/api/interactive_templates');
        cachedIntTemplates = await res.json();
        renderTemplateList();
    } catch(e) {
        console.error('Failed to load templates', e);
    }
}

function renderTemplateList() {
    const typeNode = document.getElementById('int-type');
    if(!typeNode) return;
    const type = typeNode.value;
    const listDiv = document.getElementById('int-template-list');
    if (!listDiv) return;
    
    listDiv.innerHTML = '';
    const filtered = cachedIntTemplates.filter(t => t.itype === type);
    
    if(filtered.length === 0) {
        listDiv.innerHTML = '<div style="color:var(--text-3); font-size:12px; text-align:center; padding:10px;">No saved templates for this type.</div>';
        return;
    }
    
    filtered.forEach(t => {
        const row = document.createElement('div');
        row.style.cssText = "background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:8px;";
        
        row.innerHTML = `
            <div style="font-size:14px; font-weight:600; color:var(--text-1);">${t.name}</div>
            <div style="display:flex; gap:6px;">
                <button onclick="sendInteractiveMsgDirectly(${t.id})" style="flex:1; padding:6px; background:var(--green); border:none; border-radius:6px; color:white; cursor:pointer; font-weight:500; font-size:12px; transition:transform 0.1s;">Send</button>
                <button onclick="openTemplateForm(${t.id})" style="flex:1; padding:6px; background:rgba(255,255,255,0.1); border:none; border-radius:6px; color:var(--text-1); cursor:pointer; font-weight:500; font-size:12px;">Edit</button>
                <button onclick="deleteInteractiveTemplate(${t.id})" style="flex:1; padding:6px; background:rgba(255,107,107,0.15); border:none; border-radius:6px; color:var(--danger); cursor:pointer; font-weight:500; font-size:12px;">Delete</button>
            </div>
        `;
        listDiv.appendChild(row);
    });
}

function openTemplateForm(idOrNew) {
    try {
        document.getElementById('int-template-list').style.display = 'none';
        document.getElementById('btn-create-new-template').style.display = 'none';
        document.getElementById('int-form-wrapper').style.display = 'block';
        
        document.querySelectorAll('#modal-interactive input:not([type="hidden"]), #modal-interactive textarea').forEach(el => {
            el.value = '';
        });
        
        if(idOrNew === 'new') {
            document.getElementById('int-editing-id').value = '';
            toggleInteractiveFields();
            return;
        }
        
        document.getElementById('int-editing-id').value = idOrNew;
        const t = cachedIntTemplates.find(x => x.id == idOrNew);
        if(!t) return;
        
        document.getElementById('int-body').value = t.payload.body || '';
        document.getElementById('int-header').value = t.payload.header || '';
        document.getElementById('int-footer').value = t.payload.footer || '';
        
        if(t.itype === 'list') {
            document.getElementById('int-button_text').value = t.payload.button_text || '';
            document.getElementById('int-sections').value = JSON.stringify(t.payload.sections || [], null, 2);
        } else if(t.itype === 'button') {
            if(t.payload.buttons && t.payload.buttons[0]) document.getElementById('int-btn1').value = t.payload.buttons[0].title;
            if(t.payload.buttons && t.payload.buttons[1]) document.getElementById('int-btn2').value = t.payload.buttons[1].title;
            if(t.payload.buttons && t.payload.buttons[2]) document.getElementById('int-btn3').value = t.payload.buttons[2].title;
        } else if(t.itype === 'product' || t.itype === 'catalog_message') {
            document.getElementById('int-catalog_id').value = t.payload.catalog_id || '';
            document.getElementById('int-product_id').value = t.payload.product_retailer_id || t.payload.thumbnail_product_retailer_id || '';
        } else if(t.itype === 'product_list') {
            document.getElementById('int-catalog_id').value = t.payload.catalog_id || '';
            document.getElementById('int-sections').value = JSON.stringify(t.payload.sections || [], null, 2);
        } else if(t.itype === 'address_message') {
            document.getElementById('int-country_code').value = t.payload.country_code || '';
        } else if(t.itype === 'flow') {
            document.getElementById('int-flow_id').value = t.payload.flow_id || '';
            document.getElementById('int-flow_cta').value = t.payload.cta_text || '';
            document.getElementById('int-flow_screen').value = t.payload.screen || '';
            document.getElementById('int-flow_token').value = t.payload.flow_token || '';
        }
        toggleInteractiveFields();
    } catch(e) {
        alert("Error opening form: " + e.message);
    }
}

function closeTemplateForm() {
    document.getElementById('int-template-list').style.display = 'flex';
    document.getElementById('btn-create-new-template').style.display = 'block';
    document.getElementById('int-form-wrapper').style.display = 'none';
}

async function deleteInteractiveTemplate(id) {
    if(!confirm("Are you sure you want to delete this template?")) return;
    try {
        const res = await fetch('/api/interactive_templates/' + id, {method: 'DELETE'});
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        showToast('✅ Template deleted');
        fetchInteractiveTemplates();
    } catch(e) {
        showToast('⚠️ Delete failed: ' + e.message);
    }
}

async function sendInteractiveMsgDirectly(id) {
    if(!activePhone){ showToast('⚠️ Select a conversation first'); return; }
    const t = cachedIntTemplates.find(x => x.id == id);
    if(!t) return;
    
    const payload = Object.assign({phone: activePhone, itype: t.itype}, t.payload);
    
    try {
        const res = await fetch('/api/send_interactive_msg', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        
        loadMessages(); loadChats();
        closeModal('interactive');
        showToast('✅ Sent successfully');
    } catch(e) {
        showToast('⚠️ Send failed: ' + e.message, 5000);
    }
}

async function saveInteractiveTemplate() {
    const t = document.getElementById('int-type').value;
    const editingId = document.getElementById('int-editing-id').value;
    const payload = {
        body: document.getElementById('int-body').value.trim(),
        header: document.getElementById('int-header').value.trim(),
        footer: document.getElementById('int-footer').value.trim()
    };
    
    try {
        if(t === 'list' || t === 'product_list') {
            const raw = document.getElementById('int-sections').value.trim();
            if(raw) payload.sections = JSON.parse(raw);
            if(t === 'list') payload.button_text = document.getElementById('int-button_text').value.trim();
            if(t === 'product_list') payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
        } else if(t === 'button') {
            const b1 = document.getElementById('int-btn1').value.trim();
            const b2 = document.getElementById('int-btn2').value.trim();
            const b3 = document.getElementById('int-btn3').value.trim();
            const arr = [];
            if(b1) arr.push({id: "btn1", title: b1});
            if(b2) arr.push({id: "btn2", title: b2});
            if(b3) arr.push({id: "btn3", title: b3});
            payload.buttons = arr;
        } else if(t === 'product') {
            payload.catalog_id = document.getElementById('int-catalog_id').value.trim();
            payload.product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'catalog_message') {
            payload.thumbnail_product_retailer_id = document.getElementById('int-product_id').value.trim();
        } else if(t === 'address_message') {
            payload.country_code = document.getElementById('int-country_code').value.trim();
        } else if(t === 'flow') {
            payload.flow_id = document.getElementById('int-flow_id').value.trim();
            payload.cta_text = document.getElementById('int-flow_cta').value.trim();
            payload.screen = document.getElementById('int-flow_screen').value.trim();
            payload.flow_token = document.getElementById('int-flow_token').value.trim();
        }
        
        let url = '/api/interactive_templates';
        let method = 'POST';
        let reqBody = {itype: t, payload: payload};
        
        if (editingId) {
            url += '/' + editingId;
            method = 'PUT';
        } else {
            const name = prompt('Enter a name for this new template:');
            if(!name) return;
            reqBody.name = name;
        }
        
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(reqBody)
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        
        showToast('✅ Template saved!');
        await fetchInteractiveTemplates();
        closeTemplateForm();
    } catch(e) {
        showToast('⚠️ Save failed: ' + e.message, 4000);
    }
}

// ── POLLING ───────────────────────────────────────────────────
setInterval(()=>{loadChats();loadMessages();},2000);
loadChats();
fetchInteractiveTemplates();
>>>>>>> aed7e9e5d444501ed3d150681887b2334c720e52
