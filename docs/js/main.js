// main.js - Core dashboard functionality

// Global variables
let trendData = {};
let currentTab = 'dashboard';
let charts = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Load trend data
    fetchTrendData();
    
    // Set up navigation
    setupNavigation();
    
    // Set up refresh button
    document.getElementById('refreshData').addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Refreshing...';
        
        // Make the API call to trigger data refresh (if you have an endpoint)
        // For now, just reload the data
        setTimeout(() => {
            fetchTrendData();
            this.disabled = false;
            this.innerHTML = 'Refresh Data';
        }, 2000);
    });
});

// Fetch trend data from JSON file
function fetchTrendData() {
    fetch('trendData.json')
        .then(response => response.json())
        .then(data => {
            trendData = data;
            updateDashboard();
            updateHashtagsSection();
            updateSongsSection();
            updateAIInsights();
            document.getElementById('updateTime').textContent = data.last_updated || 'Unknown';
        })
        .catch(error => {
            console.error('Error loading trend data:', error);
            document.getElementById('lastUpdated').className = 'alert alert-danger';
            document.getElementById('updateTime').textContent = 'Failed to load data';
        });
}

// Set up navigation
function setupNavigation() {
    // Tab navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            
            // Update navigation
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide sections
            document.querySelectorAll('section').forEach(section => {
                if (section.id === targetId) {
                    section.classList.remove('d-none');
                    currentTab = targetId;
                } else {
                    section.classList.add('d-none');
                }
            });
        });
    });
    
    // Tab content navigation
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            
            // Update tabs
            this.closest('.nav-tabs').querySelectorAll('.nav-link').forEach(t => {
                t.classList.remove('active');
            });
            this.classList.add('active');
            
            // Update tab content
            this.closest('section').querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('show', 'active');
            });
            target.classList.add('show', 'active');
        });
    });
}

// Update dashboard with trend data
function updateDashboard() {
    if (!trendData) return;
    
    // Update summary cards
    const totalTrends = (trendData.hashtags_7d?.length || 0) + (trendData.trending_songs?.length || 0);
    document.getElementById('totalTrends').textContent = totalTrends;
    
    // Count rising trends
    const risingTrends = [
        ...(trendData.hashtags_7d || []),
        ...(trendData.trending_songs || [])
    ].filter(item => item.lifecycle_stage === 'rising').length;
    document.getElementById('risingTrends').textContent = risingTrends;
    
    // Get top category
    const topCategory = trendData.category_analysis?.[0]?.name || 'N/A';
    document.getElementById('topCategory').textContent = topCategory.charAt(0).toUpperCase() + topCategory.slice(1);
    
    // Count emerging trends
    const emergingCount = trendData.emerging_trends?.length || 0;
    document.getElementById('emergingCount').textContent = emergingCount;
    
    // Render category chart
    renderCategoryChart();
    
    // Render lifecycle chart
    renderLifecycleChart();
    
    // Display emerging trends
    displayEmergingTrends();
}

// Render category distribution chart
function renderCategoryChart() {
    const categoryData = trendData.category_analysis || [];
    
    if (categoryData.length === 0) return;
    
    const labels = categoryData.map(c => c.name.charAt(0).toUpperCase() + c.name.slice(1));
    const data = categoryData.map(c => c.percentage);
    const colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(199, 199, 199, 0.7)'
    ];
    
    if (charts.categoryChart) {
        charts.categoryChart.destroy();
    }
    
    const ctx = document.getElementById('categoryChart').getContext('2d');
    charts.categoryChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

// Render lifecycle stages chart
function renderLifecycleChart() {
    // Combine hashtags and songs
    const allItems = [
        ...(trendData.hashtags_7d || []),
        ...(trendData.trending_songs || [])
    ];
    
    // Count lifecycle stages
    const lifecycleCounts = {
        rising: 0,
        growing: 0,
        stable: 0,
        declining: 0
    };
    
    allItems.forEach(item => {
        const stage = item.lifecycle_stage || 'stable';
        if (lifecycleCounts.hasOwnProperty(stage)) {
            lifecycleCounts[stage]++;
        }
    });
    
    if (charts.lifecycleChart) {
        charts.lifecycleChart.destroy();
    }
    
    const ctx = document.getElementById('lifecycleChart').getContext('2d');
    charts.lifecycleChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Rising', 'Growing', 'Stable', 'Declining'],
            datasets: [{
                data: [
                    lifecycleCounts.rising,
                    lifecycleCounts.growing,
                    lifecycleCounts.stable,
                    lifecycleCounts.declining
                ],
                backgroundColor: [
                    'rgba(40, 167, 69, 0.7)',
                    'rgba(23, 162, 184, 0.7)',
                    'rgba(108, 117, 125, 0.7)',
                    'rgba(220, 53, 69, 0.7)'
                ],
                borderColor: [
                    'rgb(40, 167, 69)',
                    'rgb(23, 162, 184)',
                    'rgb(108, 117, 125)',
                    'rgb(220, 53, 69)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Trends'
                    }
                }
            }
        }
    });
}

// Display emerging trends
function displayEmergingTrends() {
    const emergingContainer = document.getElementById('emergingTrends');
    emergingContainer.innerHTML = '';
    
    const emergingTrends = trendData.emerging_trends || [];
    
    if (emergingTrends.length === 0) {
        emergingContainer.innerHTML = '<div class="col-12">No emerging trends detected.</div>';
        return;
    }
    
    emergingTrends.forEach(trend => {
        const card = document.createElement('div');
        card.className = 'col-md-4 mb-3';
        
        // Create category badges
        const badges = (trend.categories || []).map(category => {
            return `<span class="badge bg-secondary category-badge">${category}</span>`;
        }).join('');
        
        card.innerHTML = `
            <div class="card trend-card h-100" data-id="${trend.item}" data-type="${trend.type}">
                <div class="card-body">
                    <h5 class="card-title">${trend.item}</h5>
                    <div class="mb-2">${badges}</div>
                    <p class="card-text">
                        <strong>Type:</strong> ${trend.type.charAt(0).toUpperCase() + trend.type.slice(1)}<br>
                        <strong>Confidence:</strong> ${trend.confidence}%<br>
                        <strong>Posts:</strong> ${trend.post_count || 'N/A'}
                    </p>
                </div>
            </div>
        `;
        
        card.querySelector('.trend-card').addEventListener('click', function() {
            showTrendDetails(trend);
        });
        
        emergingContainer.appendChild(card);
    });
}

// Update hashtags section
function updateHashtagsSection() {
    // Update 7-day hashtags
    const hashtags7dContainer = document.getElementById('hashtags7dList');
    hashtags7dContainer.innerHTML = '';
    
    const hashtags7d = trendData.hashtags_7d || [];
    hashtags7d.forEach(hashtag => {
        displayHashtagCard(hashtag, hashtags7dContainer);
    });
    
    // Update 30-day hashtags
    const hashtags30dContainer = document.getElementById('hashtags30dList');
    hashtags30dContainer.innerHTML = '';
    
    const hashtags30d = trendData.hashtags_30d || [];
    hashtags30d.forEach(hashtag => {
        displayHashtagCard(hashtag, hashtags30dContainer);
    });
    
    // Update hashtag clusters
    const clustersContainer = document.getElementById('clustersList');
    clustersContainer.innerHTML = '';
    
    const clusters = trendData.hashtag_clusters || [];
    clusters.forEach(cluster => {
        displayClusterCard(cluster, clustersContainer);
    });
}

// Display hashtag card
function displayHashtagCard(hashtag, container) {
    const col = document.createElement('div');
    col.className = 'col-md-4 mb-3';
    
    // Create category badges
    const badges = (hashtag.categories || []).map(category => {
        return `<span class="badge bg-secondary category-badge">${category}</span>`;
    }).join('');
    
    // Determine ranking icon and class
    let rankingIcon = '';
    let rankingClass = '';
    if (hashtag.ranking_direction === 'up') {
        rankingIcon = '<i class="bi bi-arrow-up-circle-fill"></i>';
        rankingClass = 'text-success';
    } else if (hashtag.ranking_direction === 'down') {
        rankingIcon = '<i class="bi bi-arrow-down-circle-fill"></i>';
        rankingClass = 'text-danger';
    }
    
    // Determine lifecycle class
    let lifecycleClass = `lifecycle-${hashtag.lifecycle_stage || 'stable'}`;
    
    col.innerHTML = `
        <div class="card trend-card h-100" data-id="${hashtag.hashtag}" data-type="hashtag">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span>Rank #${hashtag.rank}</span>
                <span class="${rankingClass}">${rankingIcon} ${hashtag.ranking_change || 0}</span>
            </div>
            <div class="card-body">
                <h5 class="card-title">${hashtag.hashtag}</h5>
                <div class="mb-2">${badges}</div>
                <p class="card-text">
                    <strong>Posts:</strong> ${hashtag.post_count || 'N/A'}<br>
                    <strong>Stage:</strong> <span class="${lifecycleClass}">${(hashtag.lifecycle_stage || 'stable').charAt(0).toUpperCase() + (hashtag.lifecycle_stage || 'stable').slice(1)}</span>
                </p>
                ${hashtag.period_momentum ? `<p class="card-text"><strong>Momentum:</strong> ${hashtag.period_momentum}</p>` : ''}
            </div>
        </div>
    `;
    
    col.querySelector('.trend-card').addEventListener('click', function() {
        showTrendDetails(hashtag);
    });
    
    container.appendChild(col);
}

// Display cluster card
function displayClusterCard(cluster, container) {
    const card = document.createElement('div');
    card.className = 'card mb-3';
    
    // Create category badges
    const badges = (cluster.categories || []).map(category => {
        return `<span class="badge bg-secondary category-badge">${category}</span>`;
    }).join('');
    
    // List hashtags in cluster
    const hashtagsList = cluster.items.map(item => {
        return `<li class="list-group-item d-flex justify-content-between align-items-center">
            ${item.hashtag}
            <span class="badge bg-primary">#${item.rank}</span>
        </li>`;
    }).join('');
    
    card.innerHTML = `
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Cluster #${cluster.id.split('_')[1]}</h5>
            <span class="badge bg-info">${cluster.size} hashtags</span>
        </div>
        <div class="card-body">
            <div class="mb-3">${badges}</div>
            <p><strong>Trend Strength:</strong> ${cluster.trend_strength}/${cluster.size}</p>
        </div>
        <ul class="list-group list-group-flush">
            ${hashtagsList}
        </ul>
    `;
    
    container.appendChild(card);
}

// Update songs section
function updateSongsSection() {
    // Update trending songs
    const trendingSongsContainer = document.getElementById('trendingSongsList');
    trendingSongsContainer.innerHTML = '';
    
    const trendingSongs = trendData.trending_songs || [];
    trendingSongs.forEach(song => {
        displaySongCard(song, trendingSongsContainer);
    });
    
    // Update breakout songs
    const breakoutSongsContainer = document.getElementById('breakoutSongsList');
    breakoutSongsContainer.innerHTML = '';
    
    const breakoutSongs = trendData.breakout_songs || [];
    breakoutSongs.forEach(song => {
        displaySongCard(song, breakoutSongsContainer, true);
    });
}

// Display song card
function displaySongCard(song, container, isBreakout = false) {
    const col = document.createElement('div');
    col.className = 'col-md-4 mb-3';
    
    // Determine lifecycle class
    let lifecycleClass = `lifecycle-${song.lifecycle_stage || 'stable'}`;
    
    // Determine ranking info
    let rankingInfo = '';
    if (!isBreakout && song.ranking_direction && song.ranking_change) {
        let rankingClass = song.ranking_direction === 'up' ? 'text-success' : 'text-danger';
        let rankingIcon = song.ranking_direction === 'up' ? 
            '<i class="bi bi-arrow-up-circle-fill"></i>' : 
            '<i class="bi bi-arrow-down-circle-fill"></i>';
        
        rankingInfo = `
            <span class="${rankingClass}">${rankingIcon} ${song.ranking_change}</span>
        `;
    } else if (isBreakout) {
        rankingInfo = '<span class="badge bg-danger">Breakout</span>';
    }
    
    col.innerHTML = `
        <div class="card trend-card h-100" data-id="${song.song_name}" data-type="song">
            <div class="card-header d-flex justify-content-between align-items-center">
                ${isBreakout ? '' : `<span>Rank #${song.rank || 'N/A'}</span>`}
                ${rankingInfo}
            </div>
            <div class="card-body">
                <h5 class="card-title">${song.song_name}</h5>
                <h6 class="card-subtitle mb-2 text-muted">${song.artist || 'Unknown Artist'}</h6>
                <p class="card-text">
                    <strong>Posts:</strong> ${song.post_count || 'N/A'}<br>
                    <strong>Stage:</strong> <span class="${lifecycleClass}">${(song.lifecycle_stage || 'stable').charAt(0).toUpperCase() + (song.lifecycle_stage || 'stable').slice(1)}</span>
                </p>
            </div>
        </div>
    `;
    
    col.querySelector('.trend-card').addEventListener('click', function() {
        showTrendDetails(song);
    });
    
    container.appendChild(col);
}

// Show trend details in modal
function showTrendDetails(trend) {
    const modal = new bootstrap.Modal(document.getElementById('detailModal'));
    
    // Set modal title
    document.getElementById('detailModalTitle').textContent = 
        trend.type === 'hashtag' ? trend.hashtag : `${trend.song_name} - ${trend.artist || 'Unknown'}`;
    
    // Populate detail stats
    const detailStats = document.getElementById('detailStats');
    
    if (trend.type === 'hashtag') {
        detailStats.innerHTML = `
            <h4>Hashtag Statistics</h4>
            <p><strong>Rank:</strong> #${trend.rank || 'N/A'}</p>
            <p><strong>Posts:</strong> ${trend.post_count || 'N/A'}</p>
            <p><strong>Lifecycle Stage:</strong> ${(trend.lifecycle_stage || 'stable').charAt(0).toUpperCase() + (trend.lifecycle_stage || 'stable').slice(1)}</p>
            <p><strong>Ranking Change:</strong> ${trend.ranking_direction || 'stable'} ${trend.ranking_change || 0}</p>
            ${trend.period_momentum ? `<p><strong>Momentum:</strong> ${trend.period_momentum}</p>` : ''}
            <p><strong>Categories:</strong> ${(trend.categories || []).join(', ')}</p>
        `;
    } else {
        detailStats.innerHTML = `
            <h4>Song Statistics</h4>
            <p><strong>Artist:</strong> ${trend.artist || 'Unknown'}</p>
            <p><strong>Rank:</strong> #${trend.rank || 'N/A'}</p>
            <p><strong>Posts:</strong> ${trend.post_count || 'N/A'}</p>
            <p><strong>Lifecycle Stage:</strong> ${(trend.lifecycle_stage || 'stable').charAt(0).toUpperCase() + (trend.lifecycle_stage || 'stable').slice(1)}</p>
            ${trend.ranking_direction ? `<p><strong>Ranking Change:</strong> ${trend.ranking_direction} ${trend.ranking_change || 0}</p>` : ''}
        `;
    }
    
    // Show the chart if available
    const chartCanvas = document.getElementById('detailChart');
    if (trend.chart_image) {
        // For now, just display text - in a real implementation you'd load the chart
        chartCanvas.style.display = 'block';
        // Here you would load the chart image
    } else {
        chartCanvas.style.display = 'none';
    }
    
    // Show AI analysis
    document.getElementById('aiAnalysis').innerHTML = `
        <h4>AI Analysis</h4>
        <div id="aiTrendInsight">Loading AI insights...</div>
    `;
    
    // Open the modal
    modal.show();
    
    // Once modal is shown, trigger AI analysis
    setTimeout(() => {
        // This would be replaced with a call to your AI integration
        document.getElementById('aiTrendInsight').innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h5>Trend Prediction</h5>
                    <p>Based on current momentum and engagement patterns, this trend is likely to 
                    ${trend.lifecycle_stage === 'rising' ? 'continue rising for approximately 5-7 days.' : 
                    trend.lifecycle_stage === 'declining' ? 'decline steadily over the next 7-10 days.' : 
                    'maintain stable engagement for the next 2-3 weeks.'}</p>
                    
                    <h5>Content Opportunity</h5>
                    <p>This trend aligns well with ${(trend.categories || ['general'])[0]} content and would be most effective 
                    when combined with authentic, ${trend.type === 'hashtag' ? 'visually engaging' : 'energetic'} content that 
                    resonates with ${trend.type === 'hashtag' ? 
                    trend.hashtag.toLowerCase().includes('challenge') ? 'challenge participants' : 'your target demographic' : 
                    'music enthusiasts'}.</p>
                </div>
            </div>
        `;
    }, 1000);
}

// Update AI Insights section
function updateAIInsights() {
    // This would be replaced with real AI-generated content
    document.getElementById('trendPredictions').innerHTML = `
        <div class="alert alert-info">
            <h5>Trend Forecast</h5>
            <p>Based on current data patterns, we predict the following trends will gain significant traction in the next 7-14 days:</p>
            <ol>
                ${(trendData.emerging_trends || []).slice(0, 3).map(trend => 
                    `<li><strong>${trend.item}</strong> - ${trend.confidence}% confidence</li>`
                ).join('')}
            </ol>
        </div>
    `;
    
    document.getElementById('contentRecommendations').innerHTML = `
        <div class="card mb-3">
            <div class="card-body">
                <h5>Content Strategy Recommendations</h5>
                <p>Based on current trend analysis, consider these content approaches:</p>
                
                <h6>1. Leverage Top Categories</h6>
                <p>Focus on ${(trendData.category_analysis || []).slice(0, 2).map(c => c.name).join(' and ')} 
                content, which currently dominates the trending space.</p>
                
                <h6>2. Trend Combinations</h6>
                <p>Combine emerging hashtags with trending songs for maximum visibility:</p>
                <ul>
                    ${generateTrendCombinations()}
                </ul>
                
                <h6>3. Timing Strategy</h6>
                <p>Post content using these trends during peak engagement hours (typically 6-9 PM local time) 
                for maximum initial boost.</p>
            </div>
        </div>
    `;
    
    document.getElementById('aiTrendAnalysis').innerHTML = `
        <div class="card">
            <div class="card-body">
                <h5>Trend Correlation Analysis</h5>
                <p>Our AI has identified these key insights from the current trend data:</p>
                
                <ul>
                    <li>There's a strong correlation between ${(trendData.category_analysis || []).slice(0, 1).map(c => c.name)[0] || 'entertainment'} 
                    hashtags and rapid growth patterns (${calculateCorrelationPercentage()}% correlation)</li>
                    
                    <li>${(trendData.hashtag_clusters || []).length} distinct trend clusters identified, 
                    suggesting ${(trendData.hashtag_clusters || []).length > 3 ? 'a diverse' : 'a focused'} content landscape</li>
                    
                    <li>Breakout songs show ${(trendData.breakout_songs || []).length > 0 ? 'stronger' : 'weaker'} 
                    performance than hashtag trends in the current cycle</li>
                </ul>
            </div>
        </div>
    `;
}

// Helper function to generate trend combinations
function generateTrendCombinations() {
    const hashtags = trendData.hashtags_7d || [];
    const songs = trendData.trending_songs || [];
    
    if (hashtags.length === 0 || songs.length === 0) {
        return '<li>No combinations available with current data</li>';
    }
    
    const combinations = [];
    const topHashtags = hashtags.slice(0, 3);
    const topSongs = songs.slice(0, 2);
    
    for (let i = 0; i < Math.min(3, topHashtags.length); i++) {
        const song = topSongs[i % topSongs.length];
        combinations.push(`<li><strong>${topHashtags[i].hashtag}</strong> with song "${song.song_name}" by ${song.artist || 'Unknown'}</li>`);
    }
    
    return combinations.join('');
}

// Helper function to calculate a mock correlation percentage
function calculateCorrelationPercentage() {
    // This would be replaced with real analysis
    return Math.floor(65 + Math.random() * 20);
}