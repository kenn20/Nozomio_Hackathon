/**
 * CogWatch Dashboard — Frontend Application
 *
 * Connects to InsForge edge functions for data.
 * Configure INSFORGE_URL below or via query param ?api=<url>
 */

// Configuration — set this to your InsForge project URL
const params = new URLSearchParams(window.location.search);
const API_BASE = params.get('api') || window.INSFORGE_URL || 'https://m6y5u4zr.functions.insforge.app';

// State
let currentPage = 'alerts';
let alertsFilter = 'all';
let timelineFilter = 'all';

// Navigation
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const page = link.dataset.page;
    switchPage(page);
  });
});

function switchPage(page) {
  currentPage = page;
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelector(`[data-page="${page}"]`).classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');

  if (page === 'alerts') loadAlerts();
  if (page === 'timeline') loadDecisions();
  if (page === 'settings') loadPersonas();
}

// Alerts Page
document.querySelectorAll('#page-alerts .filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#page-alerts .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    alertsFilter = btn.dataset.filter;
    loadAlerts();
  });
});

async function loadAlerts() {
  const container = document.getElementById('alerts-container');

  if (!API_BASE) {
    container.innerHTML = renderDemoAlerts();
    return;
  }

  container.innerHTML = '<div class="loading">Loading alerts...</div>';

  try {
    let url = `${API_BASE}/get-alerts`;
    if (alertsFilter === 'unacknowledged') url += '?acknowledged=false';
    if (alertsFilter === 'acknowledged') url += '?acknowledged=true';

    const res = await fetch(url);
    const { data } = await res.json();
    container.innerHTML = data.length ? data.map(renderAlertCard).join('') : renderEmptyAlerts();
  } catch (err) {
    console.error('Failed to load alerts:', err);
    container.innerHTML = renderDemoAlerts();
  }
}

function renderAlertCard(alert) {
  const old = alert.old_decision || {};
  const newD = alert.new_decision || {};
  const responses = alert.persona_responses || [];
  const date = new Date(alert.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  return `
    <div class="alert-card ${alert.acknowledged ? 'acknowledged' : ''}">
      <div class="alert-header">
        <div class="alert-type">
          <span class="severity-badge severity-${alert.severity}">${alert.severity}</span>
          <span class="contradiction-type">${formatType(alert.contradiction_type)}</span>
        </div>
        <span class="alert-timestamp">${date}</span>
      </div>
      <p class="alert-explanation">${escapeHtml(alert.explanation)}</p>
      <div class="decision-pair">
        <div class="decision-box">
          <div class="decision-label old">Previous Decision</div>
          <div class="decision-content">${escapeHtml(old.content || 'N/A')}</div>
          <div class="decision-meta">${escapeHtml(old.context || '')} &middot; ${old.source || ''}</div>
        </div>
        <div class="decision-box">
          <div class="decision-label new">Current Activity</div>
          <div class="decision-content">${escapeHtml(newD.content || 'N/A')}</div>
          <div class="decision-meta">${escapeHtml(newD.context || '')} &middot; ${newD.source || ''}</div>
        </div>
      </div>
      ${responses.length ? `
        <div class="persona-responses">
          ${responses.map(r => `
            <div class="persona-card">
              <div class="persona-name">${escapeHtml(r.persona_name)}</div>
              <div class="persona-response">${escapeHtml(r.response)}</div>
            </div>
          `).join('')}
        </div>
      ` : ''}
      ${!alert.acknowledged ? `
        <div class="alert-actions">
          <button class="action-btn" onclick="acknowledgeAlert('${alert.id}', 'old_was_right')">Old Was Right</button>
          <button class="action-btn" onclick="acknowledgeAlert('${alert.id}', 'new_is_right')">New Is Right</button>
          <button class="action-btn primary" onclick="acknowledgeAlert('${alert.id}', 'acknowledged')">Acknowledge</button>
        </div>
      ` : '<div class="alert-actions"><span style="color: var(--accent-green); font-size: 13px;">Resolved</span></div>'}
    </div>
  `;
}

async function acknowledgeAlert(id, resolution) {
  if (!API_BASE) {
    // Demo mode: just toggle visually
    document.querySelector(`[onclick*="${id}"]`).closest('.alert-card').classList.add('acknowledged');
    return;
  }

  try {
    await fetch(`${API_BASE}/acknowledge-alert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, resolution })
    });
    loadAlerts();
  } catch (err) {
    console.error('Failed to acknowledge alert:', err);
  }
}

// Timeline Page
document.querySelectorAll('#page-timeline .filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#page-timeline .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    timelineFilter = btn.dataset.filter;
    loadDecisions();
  });
});

async function loadDecisions() {
  const container = document.getElementById('timeline-container');

  if (!API_BASE) {
    container.innerHTML = renderDemoTimeline();
    return;
  }

  container.innerHTML = '<div class="loading">Loading decisions...</div>';

  try {
    let url = `${API_BASE}/get-decisions`;
    if (timelineFilter !== 'all') url += `?source=${timelineFilter}`;

    const res = await fetch(url);
    const { data } = await res.json();
    container.innerHTML = data.length ? data.map(renderTimelineItem).join('') : '<div class="empty-state"><h3>No decisions yet</h3><p>Connect your data sources to start tracking decisions.</p></div>';
  } catch (err) {
    console.error('Failed to load decisions:', err);
    container.innerHTML = renderDemoTimeline();
  }
}

function renderTimelineItem(item) {
  const date = new Date(item.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const tags = item.tags || [];

  return `
    <div class="timeline-item">
      <div class="timeline-dot ${item.source}"></div>
      <div class="timeline-content">
        <div class="timeline-source ${item.source}">${formatSource(item.source)}</div>
        <div class="timeline-text">${escapeHtml(item.content)}</div>
        <div class="timeline-meta">
          <span>${escapeHtml(item.context)}</span>
          <span>${date}</span>
        </div>
        ${tags.length ? `<div class="timeline-tags">${tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
      </div>
    </div>
  `;
}

// Settings Page
async function loadPersonas() {
  const container = document.getElementById('personas-container');

  if (!API_BASE) {
    container.innerHTML = renderDemoPersonas();
    return;
  }

  container.innerHTML = '<div class="loading">Loading personas...</div>';

  try {
    const res = await fetch(`${API_BASE}/get-personas`);
    const { data } = await res.json();
    container.innerHTML = data.map(renderPersonaEdit).join('');
  } catch (err) {
    console.error('Failed to load personas:', err);
    container.innerHTML = renderDemoPersonas();
  }
}

function renderPersonaEdit(persona) {
  return `
    <div class="persona-edit">
      <div class="persona-edit-header">
        <span class="persona-edit-name">${escapeHtml(persona.name)}</span>
        <button class="action-btn primary" onclick="savePersona('${persona.id}')">Save</button>
      </div>
      <textarea class="persona-prompt-input" id="prompt-${persona.id}">${escapeHtml(persona.system_prompt)}</textarea>
    </div>
  `;
}

async function savePersona(id) {
  const prompt = document.getElementById(`prompt-${id}`).value;

  if (!API_BASE) {
    alert('Saved (demo mode)');
    return;
  }

  try {
    await fetch(`${API_BASE}/update-persona`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, system_prompt: prompt })
    });
    alert('Persona saved!');
  } catch (err) {
    console.error('Failed to save persona:', err);
  }
}

// Threshold slider
const threshold = document.getElementById('threshold');
const thresholdValue = document.getElementById('threshold-value');
threshold.addEventListener('input', () => {
  thresholdValue.textContent = threshold.value;
});

// Utilities
function formatType(type) {
  return (type || '').replace(/_/g, ' ');
}

function formatSource(source) {
  const map = { obsidian: 'Obsidian', github: 'GitHub', claude_session: 'Claude Session' };
  return map[source] || source;
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderEmptyAlerts() {
  return '<div class="empty-state"><h3>No alerts yet</h3><p>CogWatch is monitoring your activity. Alerts will appear when contradictions are detected.</p></div>';
}

// Demo data for when API is not connected
function renderDemoAlerts() {
  const demoAlerts = [
    {
      id: 'demo-1',
      severity: 'high',
      contradiction_type: 'direct_contradiction',
      explanation: 'You decided to use REST API 3 weeks ago citing simplicity and team familiarity, but are now switching to GraphQL citing flexibility needs. This contradicts your earlier reasoning.',
      created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
      acknowledged: false,
      old_decision: { content: 'Decided to use REST API for all backend services. REST is simpler, better tooling, team knows it well. GraphQL adds unnecessary complexity for our use case.', context: 'PR #42 — Architecture Decision Record', source: 'github' },
      new_decision: { content: 'Going with GraphQL for the new API layer. Need flexible querying for the dashboard, and the frontend team wants to avoid over-fetching.', context: 'Note: API Architecture Rethink', source: 'obsidian' },
      persona_responses: [
        { persona_name: 'Elon Musk', response: 'You said REST was simpler — what changed? If the real problem is over-fetching, fix your REST endpoints. Don\'t add a whole new paradigm to solve a data-shaping problem. Delete the complexity, don\'t add more.' },
        { persona_name: 'Jensen Huang', response: 'This could be a platform shift moment. GraphQL enables a fundamentally different frontend architecture. But ask yourself: is this a genuine evolution of your needs, or are you just chasing what\'s trendy? Your original REST reasoning was sound.' }
      ]
    },
    {
      id: 'demo-2',
      severity: 'medium',
      contradiction_type: 'direct_contradiction',
      explanation: 'Previously committed to PostgreSQL-only architecture, now adding MongoDB for event store. This fragments the data layer you explicitly wanted to keep unified.',
      created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
      acknowledged: false,
      old_decision: { content: 'We\'re using PostgreSQL for everything. Relational model fits our domain perfectly. NoSQL would fragment our data model unnecessarily.', context: 'Claude session: database-design', source: 'claude_session' },
      new_decision: { content: 'Adding MongoDB for the event store. PostgreSQL can\'t handle the write throughput we need for real-time events.', context: 'PR #67 — Adding event store', source: 'github' },
      persona_responses: [
        { persona_name: 'Elon Musk', response: 'Have you actually benchmarked PostgreSQL\'s write throughput? I bet it handles more than you think. Adding MongoDB means two databases to maintain, two failure modes, two sets of expertise. First principles: prove Postgres can\'t do it before adding complexity.' },
        { persona_name: 'Jensen Huang', response: 'Real-time events are a different computational pattern — this might genuinely need a different tool. But consider: PostgreSQL with proper partitioning and UNLOGGED tables handles millions of writes per second. The question is whether you need document flexibility or just throughput.' }
      ]
    },
    {
      id: 'demo-3',
      severity: 'low',
      contradiction_type: 'forgotten_resolution',
      explanation: 'You already researched and decided on JWT with refresh tokens for authentication 3 weeks ago, but are now asking the same question again as if it was never resolved.',
      created_at: new Date(Date.now() - 86400000).toISOString(),
      acknowledged: false,
      old_decision: { content: 'After researching auth solutions, decided on JWT with refresh tokens stored in httpOnly cookies. This gives us stateless auth with secure token storage.', context: 'Claude session: auth-research', source: 'claude_session' },
      new_decision: { content: 'What\'s the best approach for authentication? Should we use sessions or JWTs? Need to figure out token storage strategy.', context: 'Claude session: new-feature-planning', source: 'claude_session' },
      persona_responses: [
        { persona_name: 'Elon Musk', response: 'You solved this 3 weeks ago. JWT with httpOnly cookie refresh tokens. Stop re-deriving solved problems — that\'s context rot in action. Ship with the decision you already made.' },
        { persona_name: 'Jensen Huang', response: 'Classic context rot — you did thorough research and made a sound decision, but lost that context. The good news: your earlier analysis was solid. Trust past-you on this one and focus your energy on unsolved problems.' }
      ]
    }
  ];

  return demoAlerts.map(renderAlertCard).join('');
}

function renderDemoTimeline() {
  const demoItems = [
    { source: 'github', content: 'Going with GraphQL for the new API layer. Need flexible querying for the dashboard.', context: 'PR #73 in main/api', timestamp: new Date(Date.now() - 2 * 86400000).toISOString(), tags: ['architecture', 'api', 'graphql'] },
    { source: 'github', content: 'Adding MongoDB for the event store. PostgreSQL can\'t handle the write throughput.', context: 'PR #67 in main/events', timestamp: new Date(Date.now() - 3 * 86400000).toISOString(), tags: ['database', 'events'] },
    { source: 'obsidian', content: 'Extracting notification service into its own microservice. Monolith too large.', context: 'Note: Architecture Decisions', timestamp: new Date(Date.now() - 5 * 86400000).toISOString(), tags: ['architecture', 'microservices'] },
    { source: 'claude_session', content: 'Decided to use REST API for all backend services. REST is simpler, better tooling.', context: 'Claude session: api-design', timestamp: new Date(Date.now() - 21 * 86400000).toISOString(), tags: ['architecture', 'api', 'rest'] },
    { source: 'claude_session', content: 'Using PostgreSQL for everything. Relational model fits our domain perfectly.', context: 'Claude session: database-design', timestamp: new Date(Date.now() - 30 * 86400000).toISOString(), tags: ['database', 'architecture'] },
    { source: 'obsidian', content: 'Keeping everything in the monolith for now. Microservices are premature optimization.', context: 'Note: Architecture Principles', timestamp: new Date(Date.now() - 45 * 86400000).toISOString(), tags: ['architecture', 'infrastructure'] },
  ];

  return demoItems.map(renderTimelineItem).join('');
}

function renderDemoPersonas() {
  const personas = [
    { id: 'demo-elon', name: 'Elon Musk', system_prompt: 'You think from first principles. You challenge assumptions ruthlessly. You believe most processes exist because of inertia, not logic. When you see a contradiction, you ask: "What is the physics of this problem?" You favor speed, iteration, and deleting unnecessary complexity. You are direct to the point of being blunt. Reference the user\'s specific history when advising.' },
    { id: 'demo-jensen', name: 'Jensen Huang', system_prompt: 'You think about accelerated computing and parallel execution. You believe in betting big on platform shifts and riding exponential curves. When you see a contradiction, you ask: "Is this a sign of a platform shift they are not acknowledging, or just drift?" You value long-term vision over short-term consistency. You are encouraging but intellectually honest. Reference the user\'s specific history when advising.' }
  ];
  return personas.map(renderPersonaEdit).join('');
}

// Initialize
loadAlerts();
