/**
 * Stock Portfolio Monitor - Frontend Application
 */

const API_BASE = '';

// State
let portfolio = null;

// DOM Elements
const totalValueEl = document.getElementById('total-value');
const costBasisEl = document.getElementById('cost-basis');
const todayGainEl = document.getElementById('today-gain');
const todayGainPctEl = document.getElementById('today-gain-pct');
const totalGainEl = document.getElementById('total-gain');
const totalGainPctEl = document.getElementById('total-gain-pct');
const lastUpdatedEl = document.getElementById('last-updated');
const positionsBody = document.getElementById('positions-body');
const positionsTable = document.getElementById('positions-table');
const loadingEl = document.getElementById('loading');
const emptyStateEl = document.getElementById('empty-state');
const refreshBtn = document.getElementById('refresh-btn');
const errorBanner = document.getElementById('error-banner');
const errorMessage = document.getElementById('error-message');
const staleWarning = document.getElementById('stale-warning');

// Tab elements
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');

// News tab elements
const newsLoading = document.getElementById('news-loading');
const newsContent = document.getElementById('news-content');
const newsEmpty = document.getElementById('news-empty');
const refreshNewsBtn = document.getElementById('refresh-news-btn');

// Opportunities tab elements
const opportunitiesLoading = document.getElementById('opportunities-loading');
const opportunitiesContent = document.getElementById('opportunities-content');
const opportunitiesEmpty = document.getElementById('opportunities-empty');
const refreshOpportunitiesBtn = document.getElementById('refresh-opportunities-btn');

// Format helpers
function formatCurrency(value) {
    const absValue = Math.abs(value);
    const formatted = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(absValue);
    return value < 0 ? `-${formatted}` : formatted;
}

function formatPercent(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function formatTimestamp(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function isStale(lastFetch) {
    if (!lastFetch) return true;
    const fetchDate = new Date(lastFetch);
    const now = new Date();
    const ageMinutes = (now - fetchDate) / 1000 / 60;
    return ageMinutes > 15;
}

// UI Updates
function showError(message) {
    errorMessage.textContent = message;
    errorBanner.style.display = 'flex';
}

function closeErrorBanner() {
    errorBanner.style.display = 'none';
}

function updateSummary(summary) {
    // Total Value
    totalValueEl.textContent = formatCurrency(summary.total_value);

    // Cost Basis
    costBasisEl.textContent = formatCurrency(summary.total_cost_basis);

    // Today's Gain/Loss
    const todayClass = summary.total_today_gain >= 0 ? 'positive' : 'negative';
    todayGainEl.textContent = formatCurrency(summary.total_today_gain);
    todayGainEl.className = `value ${todayClass}`;
    todayGainPctEl.textContent = formatPercent(summary.total_today_gain_percent);
    todayGainPctEl.className = `sub-value ${todayClass}`;

    // Total Gain/Loss
    const totalClass = summary.total_gain >= 0 ? 'positive' : 'negative';
    totalGainEl.textContent = formatCurrency(summary.total_gain);
    totalGainEl.className = `value ${totalClass}`;
    totalGainPctEl.textContent = formatPercent(summary.total_gain_percent);
    totalGainPctEl.className = `sub-value ${totalClass}`;

    // Last Updated
    lastUpdatedEl.textContent = formatTimestamp(summary.last_updated);
}

function updatePositions(positions) {
    positionsBody.innerHTML = '';

    if (positions.length === 0) {
        positionsTable.style.display = 'none';
        emptyStateEl.style.display = 'block';
        return;
    }

    emptyStateEl.style.display = 'none';
    positionsTable.style.display = 'table';

    for (const pos of positions) {
        const row = document.createElement('tr');
        
        const todayClass = pos.today_gain >= 0 ? 'positive-cell' : 'negative-cell';
        const totalClass = pos.total_gain >= 0 ? 'positive-cell' : 'negative-cell';

        // Use textContent for user-controlled data to prevent XSS
        const symbolCell = document.createElement('td');
        symbolCell.className = 'symbol-cell';
        symbolCell.textContent = pos.symbol;

        const qtyCell = document.createElement('td');
        qtyCell.className = 'num';
        qtyCell.textContent = pos.quantity;

        const costBasisCell = document.createElement('td');
        costBasisCell.className = 'num';
        costBasisCell.textContent = formatCurrency(pos.cost_basis);

        const priceCell = document.createElement('td');
        priceCell.className = 'num';
        priceCell.textContent = formatCurrency(pos.current_price);

        const valueCell = document.createElement('td');
        valueCell.className = 'num';
        valueCell.textContent = formatCurrency(pos.current_value);

        const todayCell = document.createElement('td');
        todayCell.className = `num ${todayClass}`;
        todayCell.innerHTML = `${formatCurrency(pos.today_gain)}<br><span class="small">${formatPercent(pos.today_gain_percent)}</span>`;

        const totalCell = document.createElement('td');
        totalCell.className = `num ${totalClass}`;
        totalCell.innerHTML = `${formatCurrency(pos.total_gain)}<br><span class="small">${formatPercent(pos.total_gain_percent)}</span>`;

        const pctCell = document.createElement('td');
        pctCell.className = 'num';
        pctCell.textContent = formatPercent(pos.percent_of_account);

        row.appendChild(symbolCell);
        row.appendChild(qtyCell);
        row.appendChild(costBasisCell);
        row.appendChild(priceCell);
        row.appendChild(valueCell);
        row.appendChild(todayCell);
        row.appendChild(totalCell);
        row.appendChild(pctCell);

        positionsBody.appendChild(row);
    }
}

// API Calls
async function fetchPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/api/portfolio`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        throw new Error(`Failed to fetch portfolio: ${error.message}`);
    }
}

async function refreshPrices() {
    try {
        const response = await fetch(`${API_BASE}/api/prices/refresh`, {
            method: 'POST'
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        throw new Error(`Failed to refresh prices: ${error.message}`);
    }
}

async function getPrices() {
    try {
        const response = await fetch(`${API_BASE}/api/prices`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        throw new Error(`Failed to get prices: ${error.message}`);
    }
}

async function fetchReport(type) {
    try {
        const response = await fetch(`${API_BASE}/api/reports/${type}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        throw new Error(`Failed to fetch ${type} report: ${error.message}`);
    }
}

async function generateReport(type) {
    try {
        const response = await fetch(`${API_BASE}/api/reports/${type}/generate`, {
            method: 'POST'
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        throw new Error(`Failed to generate ${type} report: ${error.message}`);
    }
}

// Main load
async function loadPortfolio() {
    closeErrorBanner();
    loadingEl.style.display = 'block';
    positionsTable.style.display = 'none';
    emptyStateEl.style.display = 'none';
    refreshBtn.disabled = true;

    try {
        const data = await fetchPortfolio();
        portfolio = data;

        updateSummary(data);
        updatePositions(data.positions);

        // Check if prices are stale
        const prices = await getPrices();
        if (isStale(prices.last_fetch)) {
            staleWarning.style.display = 'block';
        } else {
            staleWarning.style.display = 'none';
        }
    } catch (error) {
        showError(error.message);
    } finally {
        loadingEl.style.display = 'none';
        refreshBtn.disabled = false;
    }
}

async function handleRefresh() {
    refreshBtn.querySelector('.btn-text').style.display = 'none';
    refreshBtn.querySelector('.btn-loading').style.display = 'inline';
    refreshBtn.disabled = true;
    closeErrorBanner();

    try {
        await refreshPrices();
        await loadPortfolio();
        staleWarning.style.display = 'none';
    } catch (error) {
        showError(error.message);
    } finally {
        refreshBtn.querySelector('.btn-text').style.display = 'inline';
        refreshBtn.querySelector('.btn-loading').style.display = 'none';
        refreshBtn.disabled = false;
    }
}

// Report loading
async function loadReport(type, loadingEl, contentEl, emptyEl, btnEl) {
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';
    emptyEl.style.display = 'none';
    btnEl.disabled = true;

    try {
        // First try to get existing report
        const data = await fetchReport(type);
        
        if (data.report && data.report.length > 100) {
            contentEl.innerHTML = markdownToHtml(data.report);
            contentEl.style.display = 'block';
        } else {
            emptyEl.style.display = 'block';
        }
    } catch (error) {
        showError(error.message);
    } finally {
        loadingEl.style.display = 'none';
        btnEl.disabled = false;
    }
}

async function handleRefreshReport(type, loadingEl, contentEl, emptyEl, btnEl) {
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';
    emptyEl.style.display = 'none';
    btnEl.disabled = true;

    try {
        const result = await generateReport(type);
        if (result.report) {
            contentEl.innerHTML = markdownToHtml(result.report);
            contentEl.style.display = 'block';
        }
    } catch (error) {
        showError(error.message);
    } finally {
        loadingEl.style.display = 'none';
        btnEl.disabled = false;
    }
}

// Simple markdown to HTML converter
function markdownToHtml(text) {
    if (!text) return '<p>No content available.</p>';
    
    // Escape HTML first
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Headers
    html = html.replace(/^# (.*)$/gm, '<h1>$1</h1>');
    html = html.replace(/^## (.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^### (.*)$/gm, '<h3>$1</h3>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Lists
    html = html.replace(/^- (.*)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Paragraphs
    html = '<p>' + html + '</p>';
    html = html.replace(/<p><(h[123]|ul|li)/g, '<$1');
    html = html.replace(/<\/(h[123]|ul)><\/p>/g, '</$1>');
    html = html.replace(/<p><\/p>/g, '');
    
    return html;
}

// Tab switching
function switchTab(tabName) {
    tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    tabPanels.forEach(panel => {
        const panelId = panel.id.replace('tab-', 'tab-');
        panel.style.display = panel.id === `tab-${tabName}` ? 'block' : 'none';
    });
    
    // Load report if needed
    if (tabName === 'news') {
        loadReport('portfolio', newsLoading, newsContent, newsEmpty, refreshNewsBtn);
    } else if (tabName === 'opportunities') {
        loadReport('opportunities', opportunitiesLoading, opportunitiesContent, opportunitiesEmpty, refreshOpportunitiesBtn);
    }
}

// Event Listeners
refreshBtn.addEventListener('click', handleRefresh);

refreshNewsBtn.addEventListener('click', () => {
    handleRefreshReport('portfolio', newsLoading, newsContent, newsEmpty, refreshNewsBtn);
});

refreshOpportunitiesBtn.addEventListener('click', () => {
    handleRefreshReport('opportunities', opportunitiesLoading, opportunitiesContent, opportunitiesEmpty, refreshOpportunitiesBtn);
});

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// Initial load
loadPortfolio();

// Auto-refresh every 10 minutes
setInterval(loadPortfolio, 10 * 60 * 1000);