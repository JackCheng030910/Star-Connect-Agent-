/**
 * BenzMind — Mercedes-Benz AI Agent Platform
 * Frontend Application Logic
 */

const API_BASE = 'http://localhost:5000/api';

// ============ State ============
const state = {
  currentPanel: 'chat',
  currentMode: 'simulation',
  isLoading: false,
  chatStarted: false,
  vehicles: [],
  quotes: [],
  conversationCount: 0,
  currentAgent: 'sales_consultant',
  leadStage: 'lead_generation',
  lifecycle: null,
  eventCount: 0
};

// ============ DOM References ============
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const chatMessages = $('#chatMessages');
const chatInput = $('#chatInput');
const sendBtn = $('#sendBtn');
const welcomeScreen = $('#welcomeScreen');

// ============ Init ============
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initChat();
  initModeSwitch();
  initModal();
  loadVehicles();
  loadLifecycle();
  initQuickActions();
  initWorkflowActions();
});

// ============ Navigation ============
function initNavigation() {
  $$('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const panel = item.dataset.panel;
      switchPanel(panel);
    });
  });
}

function switchPanel(panelId) {
  // Update nav
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  const navItem = $(`[data-panel="${panelId}"]`);
  if (navItem) navItem.classList.add('active');

  // Update panels
  $$('.panel').forEach(p => p.classList.remove('active'));
  const panel = $(`#panel-${panelId}`);
  if (panel) panel.classList.add('active');

  state.currentPanel = panelId;

  // Refresh data when switching
  if (panelId === 'dashboard') updateDashboard();
  if (panelId === 'vehicles') renderVehicles();
}

// ============ Chat ============
function initChat() {
  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  // Welcome cards
  $$('.welcome-card').forEach(card => {
    card.addEventListener('click', () => {
      const prompt = card.dataset.prompt;
      if (prompt) {
        chatInput.value = prompt;
        sendMessage();
      }
    });
  });
}

function initQuickActions() {
  $$('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.action) {
        handleWorkflowAction(btn.dataset.action);
        return;
      }

      const prompt = btn.dataset.prompt;
      if (prompt) {
        chatInput.value = prompt;
        sendMessage();
      }
    });
  });
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message || state.isLoading) return;

  // Hide welcome screen
  if (!state.chatStarted) {
    state.chatStarted = true;
    if (welcomeScreen) welcomeScreen.style.display = 'none';
  }

  // Add user message
  appendMessage('user', message);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // Show typing indicator
  const typingId = showTypingIndicator();

  state.isLoading = true;
  sendBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    const data = await response.json();

    // Remove typing indicator
    removeTypingIndicator(typingId);

    // Update active agent
    if (data.agent) {
      updateActiveAgent(data.agent);
      state.currentAgent = data.agent;
    }

    // Add bot reply
    appendMessage('bot', data.reply, data.agent);

    if (data.handoff && data.handoff.target_agent) {
      updateActiveAgent(data.handoff.target_agent);
      state.currentAgent = data.handoff.target_agent;
      appendMessage('bot', data.handoff.message || `🔁 已自动转接至 ${data.handoff.target_agent}，继续为您承接后续需求。`, 'system');
    }

    // Update conversation count
    state.conversationCount++;

    // Show recommendations if any
    if (data.recommendations && data.recommendations.length > 0) {
      appendRecommendationCards(data.recommendations);
    }

    // Update user profile
    if (data.user_profile) {
      updateProfileDisplay(data.user_profile);
    }

    if (data.lead_stage || data.events) {
      state.leadStage = data.lead_stage || state.leadStage;
      state.eventCount = Array.isArray(data.events) ? data.events.length : state.eventCount;
      updateLifecycleDisplay(data);
    }

  } catch (error) {
    removeTypingIndicator(typingId);
    appendMessage('bot', '⚠️ 无法连接到服务器。请确保后端服务已启动：`python server.py`', 'system');
  }

  state.isLoading = false;
  sendBtn.disabled = false;
}

function appendMessage(type, text, agent = null) {
  const div = document.createElement('div');
  div.className = `message ${type === 'user' ? 'user' : 'bot'}`;

  const agentIcons = {
    'sales_consultant': '🎯',
    'vehicle_configurator': '🔧',
    'service_advisor': '🛡️',
    'experience_designer': '🧠',
    'system': '⚠️'
  };

  const agentNames = {
    'sales_consultant': '销售顾问 · 星辰',
    'vehicle_configurator': '配置专家 · 晨曦',
    'service_advisor': '售后助理 · 守护',
    'experience_designer': '体验设计师 · 灵感',
    'system': '系统'
  };

  const avatarIcon = type === 'user' ? '👤' : (agentIcons[agent] || '⭐');
  const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  let bodyHTML = '';
  if (type !== 'user' && agent && agentNames[agent]) {
    bodyHTML += `<div class="message-agent-tag">${agentNames[agent]}</div>`;
  }

  // Parse markdown-like formatting
  const formattedText = formatMessageText(text);
  bodyHTML += `<div class="message-text">${formattedText}</div>`;
  bodyHTML += `<div class="message-time">${time}</div>`;

  div.innerHTML = `
    <div class="message-avatar">${avatarIcon}</div>
    <div class="message-body">${bodyHTML}</div>
  `;

  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessageText(text) {
  if (!text) return '';
  // Bold: **text**
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Line breaks
  text = text.replace(/\n/g, '<br>');
  // Inline code: `text`
  text = text.replace(/`([^`]+)`/g, '<code style="background:rgba(0,173,239,0.1);padding:2px 6px;border-radius:4px;font-size:0.82em;color:#00adef;">$1</code>');
  return text;
}

function appendRecommendationCards(vehicles) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message bot';
  wrapper.style.maxWidth = '95%';

  let cardsHTML = '<div style="display:flex;gap:12px;overflow-x:auto;padding:4px 0;">';
  vehicles.forEach(v => {
    const emojis = { '轿车': '🚘', 'SUV': '🚙', '纯电EQ': '⚡' };
    cardsHTML += `
      <div style="min-width:240px;background:var(--gradient-card);border:1px solid var(--glass-border);border-radius:14px;padding:16px;flex-shrink:0;cursor:pointer;" 
           onclick="chatInput.value='详细介绍一下${v.name}';sendMessage();">
        <div style="font-size:2rem;margin-bottom:8px;">${emojis[v.category] || '🚗'}</div>
        <div style="font-weight:600;color:var(--benz-white);margin-bottom:4px;">${v.name}</div>
        <div style="font-size:0.72rem;color:var(--benz-star-blue);margin-bottom:8px;">${v.engine} · ${v.power}</div>
        <div style="font-size:0.95rem;font-weight:700;color:var(--benz-gold);">${v.priceRange}</div>
      </div>
    `;
  });
  cardsHTML += '</div>';

  wrapper.innerHTML = `
    <div class="message-avatar">💡</div>
    <div class="message-body">
      <div class="message-agent-tag">为您推荐</div>
      ${cardsHTML}
    </div>
  `;

  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'message bot';
  div.id = id;
  div.innerHTML = `
    <div class="message-avatar">⭐</div>
    <div class="message-body">
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    </div>
  `;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ============ Agent Status ============
function updateActiveAgent(agentId) {
  $$('.agent-chip').forEach(chip => {
    chip.classList.remove('active');
    if (chip.dataset.agent === agentId) {
      chip.classList.add('active');
    }
  });
}

// ============ Mode Switch ============
function initModeSwitch() {
  $$('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.mode;

      if (mode === 'openai') {
        // Show API key modal
        showApiKeyModal();
      } else {
        switchMode('simulation');
      }
    });
  });
}

function initWorkflowActions() {
  $$('.workflow-btn').forEach(btn => {
    btn.addEventListener('click', () => handleWorkflowAction(btn.dataset.action));
  });
}

async function handleWorkflowAction(action) {
  if (action === 'lead') {
    await captureLeadDialog();
  } else if (action === 'test-drive') {
    await requestTestDriveDialog();
  } else if (action === 'quote') {
    await createQuoteDialog();
  }
}

async function captureLeadDialog() {
  const name = window.prompt('客户姓名（可留空）', '');
  const phone = window.prompt('客户手机号（可留空）', '');
  const vehicle = window.prompt('意向车型（例如：GLE 450 / EQE 350+）', 'GLE 450');
  const notes = window.prompt('补充备注（例如：预算、用途、竞品）', '预算70万，关注后排和试驾体验');

  try {
    const response = await fetch(`${API_BASE}/lead/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone, preferred_vehicle: vehicle, notes, source: 'frontend' })
    });
    const data = await response.json();
    appendMessage('bot', `已登记线索：${data.lead?.id || 'SUCCESS'}，当前阶段：${formatStageLabel(data.lead?.stage || 'lead_generation')}`, 'sales_consultant');
    await loadLifecycle();
  } catch (error) {
    appendMessage('bot', '线索登记失败，请确认后端已启动。', 'system');
  }
}

async function requestTestDriveDialog() {
  const vehicle = window.prompt('试驾车型（例如：GLE 450 / S 450 L）', 'GLE 450');
  const date = window.prompt('试驾时间（例如：4月20日 14:00）', '4月20日 14:00');
  const location = window.prompt('门店或地点', '上海浦东之星');

  try {
    const response = await fetch(`${API_BASE}/test-drive/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_id: vehicle, date, location })
    });
    const data = await response.json();
    appendMessage('bot', `试驾已创建：${data.appointment_id}，当前阶段：${formatStageLabel(data.stage || 'showroom_test_drive')}`, 'sales_consultant');
    await loadLifecycle();
  } catch (error) {
    appendMessage('bot', '试驾预约失败，请确认后端已启动。', 'system');
  }
}

async function createQuoteDialog() {
  const vehicle = window.prompt('报价车型（例如：EQS 450+ / GLC 300 L）', 'EQS 450+');
  const budget = window.prompt('预算或总价（例如：90万）', '90万');
  const finance = window.prompt('金融方案偏好（可留空）', '分期 / 融资租赁');

  try {
    const response = await fetch(`${API_BASE}/deal/quote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_id: vehicle, budget, finance })
    });
    const data = await response.json();
    appendMessage('bot', `报价已生成：${data.quote_id}，当前阶段：${formatStageLabel(data.stage || 'closing')}`, 'sales_consultant');
    await loadLifecycle();
  } catch (error) {
    appendMessage('bot', '报价生成失败，请确认后端已启动。', 'system');
  }
}

async function loadLifecycle() {
  try {
    const response = await fetch(`${API_BASE}/lifecycle`);
    const data = await response.json();
    state.lifecycle = data;
    state.leadStage = data.lead_stage || state.leadStage;
    state.eventCount = Array.isArray(data.events) ? data.events.length : state.eventCount;
    updateLifecycleDisplay(data);
  } catch (error) {
    console.debug('Lifecycle API unavailable:', error);
  }
}

function formatStageLabel(stage) {
  const labels = {
    lead_generation: '线上留资引流',
    showroom_test_drive: '展厅体验与试驾',
    closing: '逼单交付',
    aftersales: '售后跟进'
  };
  return labels[stage] || stage;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function updateLifecycleDisplay(data) {
  if (!data) return;
  const stage = data.lead_stage || state.leadStage;
  const lead = data.lead || {};

  const stageEl = $('#statStage');
  if (stageEl) stageEl.textContent = formatStageLabel(stage);

  const eventEl = $('#statEvents');
  if (eventEl) eventEl.textContent = `${Array.isArray(data.events) ? data.events.length : state.eventCount}条`;

  const actionEl = $('#stageAction');
  if (actionEl) actionEl.textContent = data.recommended_action || '继续推进客户旅程';

  const leadIdEl = $('#leadId');
  if (leadIdEl) leadIdEl.textContent = lead.id || '待生成';

  const leadVehicleEl = $('#leadVehicle');
  if (leadVehicleEl) leadVehicleEl.textContent = lead.preferred_vehicle || '待采集';

  const leadPhoneEl = $('#leadPhone');
  if (leadPhoneEl) leadPhoneEl.textContent = lead.phone || '待采集';

  renderEventTimeline(data.events || []);
}

function renderEventTimeline(events) {
  const container = $('#eventTimeline');
  if (!container) return;

  if (!events.length) {
    container.innerHTML = '<div class="timeline-empty">尚未产生事件，先从留资或试驾开始。</div>';
    return;
  }

  container.innerHTML = events.slice().reverse().map((event) => {
    const payloadText = escapeHtml(JSON.stringify(event.payload || {}, null, 0));
    return `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-body">
          <div class="timeline-title">${escapeHtml(event.type)}</div>
          <div class="timeline-meta">${escapeHtml(new Date(event.timestamp).toLocaleString('zh-CN'))}</div>
          <div class="timeline-text">${payloadText}</div>
        </div>
      </div>
    `;
  }).join('');
}

async function switchMode(mode, apiKey = '', baseUrl = '', model = '') {
  try {
    const response = await fetch(`${API_BASE}/mode/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, api_key: apiKey, base_url: baseUrl, model: model })
    });
    const data = await response.json();

    if (data.success) {
      state.currentMode = mode;
      $$('.mode-btn').forEach(b => b.classList.remove('active'));
      $(`[data-mode="${mode}"]`).classList.add('active');
    }
  } catch (e) {
    console.error('Failed to switch mode:', e);
    // Still update UI in case server is not running
    state.currentMode = mode;
    $$('.mode-btn').forEach(b => b.classList.remove('active'));
    $(`[data-mode="${mode}"]`).classList.add('active');
  }
}

// ============ Modal ============
function initModal() {
  $('#modalCancel').addEventListener('click', hideApiKeyModal);
  $('#modalConfirm').addEventListener('click', () => {
    const apiKey = $('#apiKeyInput').value.trim();
    const baseUrl = $('#apiBaseUrl').value.trim();
    let model = $('#apiModel').value.trim();
    
    // Default to moonshot if moonshot url is provided without model
    if (baseUrl.includes('moonshot') && !model) {
      model = 'moonshot-v1-8k';
    }
    
    if (apiKey) {
      switchMode('openai', apiKey, baseUrl, model);
      hideApiKeyModal();
    }
  });

  // Click outside to close
  $('#apiKeyModal').addEventListener('click', (e) => {
    if (e.target.id === 'apiKeyModal') hideApiKeyModal();
  });
}

function showApiKeyModal() {
  $('#apiKeyModal').classList.add('active');
  setTimeout(() => $('#apiKeyInput').focus(), 300);
}

function hideApiKeyModal() {
  $('#apiKeyModal').classList.remove('active');
  $('#apiKeyInput').value = '';
}

// ============ Vehicles ============
async function loadVehicles() {
  try {
    const response = await fetch(`${API_BASE}/vehicles`);
    const data = await response.json();
    state.vehicles = data.vehicles || [];
  } catch (e) {
    // Load from embedded data as fallback
    try {
      const response = await fetch('data/vehicles.json');
      const data = await response.json();
      state.vehicles = data.vehicles || [];
    } catch (e2) {
      console.log('Using empty vehicles list');
      state.vehicles = [];
    }
  }
  if (state.currentPanel === 'vehicles') renderVehicles();
}

function renderVehicles(category = 'all') {
  const grid = $('#vehiclesGrid');
  if (!grid) return;

  const filtered = category === 'all'
    ? state.vehicles
    : state.vehicles.filter(v => v.category === category);

  const emojis = { '轿车': '🚘', 'SUV': '🚙', '纯电EQ': '⚡' };

  grid.innerHTML = filtered.map(v => `
    <div class="vehicle-card slide-up" onclick="openVehicleChat('${v.id}', '${v.name}')">
      <div class="vehicle-card-image" style="background-image: url('${v.image || ''}'); background-size: cover; background-position: center;">
        ${v.category === '纯电EQ' ? `<div class="vehicle-card-badge">纯电</div>` : ''}
        ${v.id === 'amg_g63' ? `<div class="vehicle-card-badge">经典传奇</div>` : ''}
      </div>
      <div class="vehicle-card-body">
        <div class="vehicle-card-series">${v.series}</div>
        <div class="vehicle-card-name">${v.name}</div>
        <div class="vehicle-card-specs">
          <span class="vehicle-spec">⚡ ${v.power}</span>
          <span class="vehicle-spec">🔧 ${v.engine}</span>
          <span class="vehicle-spec">💺 ${v.seats}座</span>
        </div>
        <div class="vehicle-card-highlights">
          ${v.highlights.slice(0, 3).map(h => `<span class="highlight-tag">${h}</span>`).join('')}
        </div>
        <div class="vehicle-card-price">${v.priceRange}</div>
      </div>
    </div>
  `).join('');

  // Category tab handler
  $$('#categoryTabs .category-tab').forEach(tab => {
    tab.onclick = () => {
      $$('#categoryTabs .category-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderVehicles(tab.dataset.category);
    };
  });
}

function openVehicleChat(vehicleId, vehicleName) {
  switchPanel('chat');
  chatInput.value = `详细介绍一下${vehicleName}`;
  sendMessage();
}

// ============ Public Dataset UI Removed ============

// ============ Dashboard ============
function updateDashboard() {
  $('#statConversations').textContent = state.conversationCount;

  const loraAdapters = {
    'sales_consultant': 'Sales_LoRA_v2.bin',
    'vehicle_configurator': 'Config_LoRA_v1.bin',
    'service_advisor': 'Aftersales_LoRA.bin',
    'experience_designer': 'MBUX_LoRA_v3.bin'
  };
  
  const loraVal = loraAdapters[state.currentAgent];
  $('#statLora').textContent = loraVal ? `${loraVal}` : '基础模型运行中';
  $('#statMode').textContent = state.currentMode === 'openai' ? 'OpenAI' : '模拟';
  $('#statStage').textContent = formatStageLabel(state.leadStage);
  $('#statEvents').textContent = `${state.eventCount}条`;
}

function updateProfileDisplay(profile) {
  if (!profile) return;
  const usageMap = {
    'family': '家庭用车', 'business': '商务出行',
    'commute': '日常通勤', 'offroad': '越野出行',
    'sport': '运动驾驶', 'travel': '自驾旅行'
  };

  if (profile.budget) {
    $('#profileBudget').textContent = `${(profile.budget / 10000).toFixed(0)}万`;
  }
  if (profile.usage) {
    $('#profileUsage').textContent = usageMap[profile.usage] || profile.usage;
  }
  if (profile.family_size) {
    $('#profileFamily').textContent = `${profile.family_size}人`;
  }
}
