/**
 * SmartMoney - Chart.js Configuration & Visualizations
 * Supports Light & Dark dynamic theme palette switching
 */

let categoryChartInstance = null;
let incomeExpenseChartInstance = null;
let reportsTrendChartInstance = null;

function getChartColors(isDark) {
  return {
    textColor: isDark ? '#94a3b8' : '#475569',
    gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)',
    tooltipBg: isDark ? '#1e293b' : '#0f172a',
    tooltipText: '#ffffff',
    palette: [
      '#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6',
      '#06b6d4', '#f97316', '#14b8a6', '#6366f1', '#84cc16', '#64748b'
    ]
  };
}

/**
 * Initialize Category Breakdown Donut Chart
 */
function initCategoryChart(canvasId, categories, dataValues, currency = '₹') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const colors = getChartColors(isDark);

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  categoryChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: categories,
      datasets: [{
        data: dataValues,
        backgroundColor: colors.palette.slice(0, categories.length),
        borderWidth: 2,
        borderColor: isDark ? '#111827' : '#ffffff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: colors.textColor,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 500 },
            padding: 14,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: colors.tooltipBg,
          titleColor: colors.tooltipText,
          bodyColor: colors.tooltipText,
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.chart._metasets[context.datasetIndex].total;
              const pct = total > 0 ? Math.round((value / total) * 100) : 0;
              return ` ${label}: ${currency}${value.toLocaleString()} (${pct}%)`;
            }
          }
        }
      },
      cutout: '68%'
    }
  });
}

/**
 * Initialize Income vs Expenses Bar Chart (Dashboard)
 */
function initIncomeExpenseChart(canvasId, labels, incomes, expenses, currency = '₹') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const colors = getChartColors(isDark);

  if (incomeExpenseChartInstance) {
    incomeExpenseChartInstance.destroy();
  }

  incomeExpenseChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Income',
          data: incomes,
          backgroundColor: '#10b981',
          borderRadius: 6,
          barPercentage: 0.6,
          categoryPercentage: 0.65
        },
        {
          label: 'Expenses',
          data: expenses,
          backgroundColor: '#f43f5e',
          borderRadius: 6,
          barPercentage: 0.6,
          categoryPercentage: 0.65
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: {
            color: colors.textColor,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 600 },
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 15
          }
        },
        tooltip: {
          backgroundColor: colors.tooltipBg,
          titleColor: colors.tooltipText,
          bodyColor: colors.tooltipText,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              return ` ${context.dataset.label}: ${currency}${context.raw.toLocaleString()}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: colors.textColor,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }
          }
        },
        y: {
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.textColor,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
            callback: function(val) {
              return `${currency}${val.toLocaleString()}`;
            }
          }
        }
      }
    }
  });
}

/**
 * Initialize 12-Month Historical Financial Trend (Reports)
 */
function initReportsTrendChart(canvasId, labels, incomes, expenses, savings, currency = '₹') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const colors = getChartColors(isDark);

  if (reportsTrendChartInstance) {
    reportsTrendChartInstance.destroy();
  }

  reportsTrendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Total Income',
          data: incomes,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.08)',
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: '#10b981'
        },
        {
          label: 'Total Expenses',
          data: expenses,
          borderColor: '#f43f5e',
          backgroundColor: 'rgba(244, 63, 94, 0.06)',
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: '#f43f5e'
        },
        {
          label: 'Savings Contributions',
          data: savings,
          borderColor: '#6366f1',
          borderDash: [5, 5],
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 4,
          pointBackgroundColor: '#6366f1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: {
            color: colors.textColor,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 600 },
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 15
          }
        },
        tooltip: {
          backgroundColor: colors.tooltipBg,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              return ` ${context.dataset.label}: ${currency}${context.raw.toLocaleString()}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: colors.gridColor },
          ticks: { color: colors.textColor }
        },
        y: {
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.textColor,
            callback: function(val) {
              return `${currency}${val.toLocaleString()}`;
            }
          }
        }
      }
    }
  });
}

/**
 * Dynamic theme update listener
 */
window.updateChartsTheme = function(newTheme) {
  const isDark = newTheme === 'dark';
  const colors = getChartColors(isDark);

  [categoryChartInstance, incomeExpenseChartInstance, reportsTrendChartInstance].forEach(chart => {
    if (!chart) return;
    if (chart.options.scales) {
      if (chart.options.scales.x) chart.options.scales.x.ticks.color = colors.textColor;
      if (chart.options.scales.y) {
        chart.options.scales.y.ticks.color = colors.textColor;
        chart.options.scales.y.grid.color = colors.gridColor;
      }
    }
    if (chart.options.plugins && chart.options.plugins.legend) {
      chart.options.plugins.legend.labels.color = colors.textColor;
    }
    chart.update();
  });
};
