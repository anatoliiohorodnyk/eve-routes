// EVE Routes - Frontend JavaScript

class EVERoutesApp {
    constructor() {
        this.currentRequest = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateDisplays();
    }

    bindEvents() {
        // Form submission
        document.getElementById('tradeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.searchOpportunities();
        });

        // Range input updates
        const cargoSlider = document.getElementById('cargoCapacity');
        const profitSlider = document.getElementById('minProfit');
        const taxSlider = document.getElementById('salesTax');

        cargoSlider.addEventListener('input', (e) => {
            this.updateCargoDisplay(e.target.value);
        });

        profitSlider.addEventListener('input', (e) => {
            this.updateProfitDisplay(e.target.value);
        });

        taxSlider.addEventListener('input', (e) => {
            this.updateTaxDisplay(e.target.value);
        });

        // Preset buttons
        document.querySelectorAll('.preset-btn[data-cargo]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const cargo = e.target.dataset.cargo;
                cargoSlider.value = cargo;
                this.updateCargoDisplay(cargo);
            });
        });

        document.querySelectorAll('.preset-btn[data-profit]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const profit = e.target.dataset.profit;
                profitSlider.value = profit;
                this.updateProfitDisplay(profit);
            });
        });

        document.querySelectorAll('.preset-btn[data-tax]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tax = e.target.dataset.tax;
                taxSlider.value = tax;
                this.updateTaxDisplay(tax);
            });
        });

        // Retry button
        document.getElementById('retryBtn').addEventListener('click', () => {
            this.hideError();
            this.searchOpportunities();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.searchOpportunities();
            }
        });
    }

    updateDisplays() {
        const cargoValue = document.getElementById('cargoCapacity').value;
        const profitValue = document.getElementById('minProfit').value;
        const taxValue = document.getElementById('salesTax').value;
        
        this.updateCargoDisplay(cargoValue);
        this.updateProfitDisplay(profitValue);
        this.updateTaxDisplay(taxValue);
    }

    updateCargoDisplay(value) {
        const display = document.getElementById('cargoDisplay');
        display.textContent = `${parseInt(value).toLocaleString()} m³`;
    }

    updateProfitDisplay(value) {
        const display = document.getElementById('profitDisplay');
        if (value >= 1000000) {
            display.textContent = `${(value / 1000000).toFixed(1)}M ISK`;
        } else if (value >= 1000) {
            display.textContent = `${(value / 1000).toFixed(0)}k ISK`;
        } else {
            display.textContent = `${parseInt(value).toLocaleString()} ISK`;
        }
    }

    updateTaxDisplay(value) {
        const display = document.getElementById('taxDisplay');
        display.textContent = `${parseFloat(value).toFixed(2)}%`;
    }

    formatISK(value) {
        if (value >= 1000000000) {
            return `${(value / 1000000000).toFixed(2)}B`;
        } else if (value >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`;
        } else if (value >= 1000) {
            return `${(value / 1000).toFixed(0)}k`;
        }
        return value.toLocaleString();
    }

    formatNumber(value) {
        return parseInt(value).toLocaleString();
    }

    async searchOpportunities() {
        // Abort previous request if still running
        if (this.currentRequest) {
            this.currentRequest.abort();
        }

        // Get form data
        const formData = new FormData(document.getElementById('tradeForm'));
        const fromStation = formData.get('fromStation');
        const toStation = formData.get('toStation');
        const cargoCapacity = formData.get('cargoCapacity');
        const minProfit = formData.get('minProfit');
        const salesTax = formData.get('salesTax');

        // Validate
        if (!fromStation) {
            this.showError('Please select departure station');
            return;
        }

        if (!toStation) {
            this.showError('Please select destination station');
            return;
        }

        if (fromStation === toStation) {
            this.showError('Departure and destination stations cannot be the same');
            return;
        }

        // Show loading
        this.showLoading();

        // Build URL
        const params = new URLSearchParams({
            from_station: fromStation,
            to_station: toStation,
            max_cargo: cargoCapacity,
            min_profit: minProfit,
            sales_tax: salesTax
        });

        const url = `/api/opportunities?${params}`;

        try {
            // Create AbortController for request cancellation
            const controller = new AbortController();
            this.currentRequest = controller;

            // Start progress animation
            this.animateProgress();

            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.showResults(data);

        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request was cancelled');
                return;
            }

            console.error('Search error:', error);
            this.showError(error.message || 'An unexpected error occurred');
        } finally {
            this.currentRequest = null;
        }
    }

    showLoading() {
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('errorSection').classList.add('hidden');
        document.getElementById('loadingSection').classList.remove('hidden');
        
        // Update search button
        const searchBtn = document.getElementById('searchBtn');
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Searching...</span>';
    }

    animateProgress() {
        const progressFill = document.getElementById('progressFill');
        const loadingText = document.getElementById('loadingText');
        
        const messages = [
            'Fetching market orders from EVE ESI API...',
            'Analyzing price differences...',
            'Calculating profit opportunities...',
            'Sorting results by profitability...',
            'Almost done...'
        ];

        let progress = 0;
        let messageIndex = 0;

        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress > 95) progress = 95;

            progressFill.style.width = `${progress}%`;
            
            if (messageIndex < messages.length - 1 && progress > (messageIndex + 1) * 20) {
                messageIndex++;
                loadingText.textContent = messages[messageIndex];
            }

            // Clear interval when request is complete or cancelled
            if (!this.currentRequest) {
                clearInterval(interval);
                progressFill.style.width = '100%';
            }
        }, 500);
    }

    showResults(data) {
        document.getElementById('loadingSection').classList.add('hidden');
        document.getElementById('errorSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

        // Update search button
        const searchBtn = document.getElementById('searchBtn');
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="fas fa-search"></i> <span>Find Trade Opportunities</span>';

        // Update metadata
        const metadata = data.metadata;
        const metaElement = document.getElementById('resultsMeta');
        metaElement.innerHTML = `
            <div>Found ${metadata.total_found} opportunities in ${metadata.query_time_seconds}s</div>
            <div>Route: ${metadata.from_station.toUpperCase()} → ${metadata.to_station.toUpperCase()}</div>
            ${metadata.cached ? '<div style="color: var(--warning-color);">📋 Cached Result</div>' : ''}
        `;

        // Update summary
        this.updateSummary(data.opportunities);

        // Update table
        this.updateTable(data.opportunities);
    }

    updateSummary(opportunities) {
        if (opportunities.length === 0) {
            document.getElementById('resultsSummary').innerHTML = 
                '<div class="summary-card"><h4>No Results</h4><div class="value">0</div></div>';
            return;
        }

        const totalProfit = opportunities.reduce((sum, opp) => sum + opp.total_profit, 0);
        const totalInvestment = opportunities.reduce((sum, opp) => sum + opp.investment, 0);
        const totalCargo = opportunities.reduce((sum, opp) => sum + opp.total_weight, 0);
        const avgMargin = opportunities.reduce((sum, opp) => sum + opp.profit_margin, 0) / opportunities.length;

        document.getElementById('resultsSummary').innerHTML = `
            <div class="summary-card profit">
                <h4>Total Profit</h4>
                <div class="value">${this.formatISK(totalProfit)} ISK</div>
            </div>
            <div class="summary-card investment">
                <h4>Investment Required</h4>
                <div class="value">${this.formatISK(totalInvestment)} ISK</div>
            </div>
            <div class="summary-card cargo">
                <h4>Cargo Used</h4>
                <div class="value">${this.formatNumber(totalCargo)} m³</div>
            </div>
            <div class="summary-card">
                <h4>Average Margin</h4>
                <div class="value">${avgMargin.toFixed(1)}%</div>
            </div>
        `;
    }

    updateTable(opportunities) {
        const tbody = document.getElementById('resultsBody');
        
        if (opportunities.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                        No profitable opportunities found with current parameters.<br>
                        Try adjusting your cargo capacity or minimum profit threshold.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = opportunities.map((opp, index) => `
            <tr>
                <td class="rank-cell">${index + 1}</td>
                <td class="item-name" title="${opp.item_name}">${opp.item_name}</td>
                <td class="price-cell">${this.formatISK(opp.buy_price)}</td>
                <td class="price-cell">${this.formatISK(opp.sell_price)}</td>
                <td class="profit-cell">${this.formatISK(opp.profit_per_unit)}</td>
                <td class="margin-cell ${this.getMarginClass(opp.profit_margin)}">${opp.profit_margin.toFixed(1)}%</td>
                <td class="price-cell">${this.formatNumber(opp.max_units)}</td>
                <td class="price-cell">${this.formatNumber(opp.total_weight)} m³</td>
                <td class="profit-cell">${this.formatISK(opp.total_profit)}</td>
                <td class="price-cell">${this.formatISK(opp.investment)}</td>
            </tr>
        `).join('');
    }

    getMarginClass(margin) {
        if (margin >= 50) return 'positive';
        if (margin >= 20) return 'neutral';
        return 'negative';
    }

    showError(message) {
        document.getElementById('loadingSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('errorSection').classList.remove('hidden');
        
        document.getElementById('errorMessage').textContent = message;

        // Update search button
        const searchBtn = document.getElementById('searchBtn');
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="fas fa-search"></i> <span>Find Trade Opportunities</span>';
    }

    hideError() {
        document.getElementById('errorSection').classList.add('hidden');
    }

    // Utility method to handle rate limiting
    async retryWithBackoff(fn, maxRetries = 3) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await fn();
            } catch (error) {
                if (error.name === 'AbortError') {
                    throw error; // Don't retry cancelled requests
                }
                
                if (i === maxRetries - 1) {
                    throw error; // Last attempt failed
                }

                // Check if it's a rate limit error
                if (error.message.includes('Rate limit') || error.message.includes('429')) {
                    const delay = Math.pow(2, i) * 1000; // Exponential backoff
                    console.log(`Rate limited, retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                } else {
                    throw error; // Not a rate limit error, don't retry
                }
            }
        }
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.eveRoutesApp = new EVERoutesApp();
    
    // Add some visual enhancements
    addVisualEnhancements();
    
    // Service worker registration for offline support (optional)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    }
});

function addVisualEnhancements() {
    // Add loading animations to form elements
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });

    // Add hover effects to preset buttons
    const presetButtons = document.querySelectorAll('.preset-btn');
    presetButtons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                left: ${x}px;
                top: ${y}px;
                width: ${size}px;
                height: ${size}px;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });

    // Add CSS for ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(2);
                opacity: 0;
            }
        }
        
        .form-group.focused {
            transform: translateY(-2px);
        }
        
        .form-group {
            transition: transform 0.3s ease;
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--dark-bg);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-color);
        }
    `;
    document.head.appendChild(style);
}

// Export for potential testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EVERoutesApp };
}