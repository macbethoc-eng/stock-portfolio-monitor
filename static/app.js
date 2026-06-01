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

function formatNumber(value, decimals = 2) {
    return value.toFixed(decimals);
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

// Event Listeners
refreshBtn.addEventListener('click', handleRefresh);

// Initial load
loadPortfolio();

// Auto-refresh every 5 minutes
setInterval(loadPortfolio, 5 * 60 * 1000);