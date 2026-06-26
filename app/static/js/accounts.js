let selectedAccount = null;

function escapeHtml(value){
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function ensureSearchForm(){
  const container = document.getElementById('account-search-container');
  if(!container || document.getElementById('account-search-form')) return;
  container.innerHTML = `<form id="account-search-form" class="inline-search"><input id="account-search" name="search" placeholder="Search transactions"><button class="btn" type="submit">Search</button></form>`;
  document.getElementById('account-search-form').addEventListener('submit', event => {
    event.preventDefault();
    if(selectedAccount){ loadAccount(selectedAccount, document.getElementById('account-search').value.trim()); }
  });
}

function renderAccounts(data){
  const greeting = document.getElementById('accounts-greeting');
  if(greeting && data.customer && data.customer.name){
    const firstName = String(data.customer.name).trim().split(/\s+/)[0] || data.customer.name;
    greeting.textContent = `Welcome back, ${firstName}`;
  }
  const container = document.getElementById('accounts-container');
  if(!data.accounts || !data.accounts.length){
    container.innerHTML = '<p class="muted empty-state">No accounts available.</p>';
    return;
  }
  container.innerHTML = data.accounts.map(a => `
    <article class="account-tile" data-account-tile="${escapeHtml(a.account_number)}">
      <div>
        <span class="muted">${escapeHtml(a.account_type)}</span>
        <h2>${escapeHtml(a.account_number)}</h2>
        <p class="balance">${escapeHtml(a.balance)} ${escapeHtml(a.currency)}</p>
      </div>
      <button type="button" class="btn view-details" data-account="${escapeHtml(a.account_number)}">View details</button>
    </article>
  `).join('');
  document.querySelectorAll('.view-details').forEach(btn => {
    btn.addEventListener('click', () => { const searchBox = document.getElementById('account-search'); loadAccount(btn.dataset.account, searchBox ? searchBox.value.trim() : ''); });
  });
}

function renderTransactions(data){
  document.getElementById('transactions-panel').style.display = 'block';
  ensureSearchForm();
  if(data.error){
    document.getElementById('transaction-list').innerHTML = `<p class="error">${escapeHtml(data.error)}</p>`;
    return;
  }
  document.getElementById('selected-account-label').textContent = `Account ${data.account.account_number} — ${data.account.account_type}`;
  document.querySelectorAll('[data-account-tile]').forEach(t => t.classList.toggle('selected', t.dataset.accountTile === data.account.account_number));
  const target = document.getElementById('transaction-list');
  if(!data.transactions.length){ target.innerHTML = '<p class="muted empty-state">No transactions found.</p>'; return; }
  target.innerHTML = data.transactions.map(t => {
    const cls = t.signed_amount.startsWith('+') ? 'credit' : 'debit';
    const date = (t.created_at || '').slice(0,16).replace('T',' ');
    return `<div class="transaction-row">
      <a class="receipt-link" href="/receipts/${encodeURIComponent(t.receipt_id)}">View receipt</a>
      <div class="transaction-main">
        <strong>${escapeHtml(t.description)}</strong>
        <span class="muted">${escapeHtml(date)} · ${escapeHtml(t.from_account)} → ${escapeHtml(t.to_account)}</span><span class="muted">Fee: ${escapeHtml(t.fee)} ${escapeHtml(t.currency)}</span>
      </div>
      <div class="transaction-amount ${cls}">${escapeHtml(t.signed_amount)} ${escapeHtml(t.currency)}</div>
    </div>`;
  }).join('');
}

async function loadAccount(account, search=''){
  selectedAccount = account;
  const url = `/api/accounts/${encodeURIComponent(account)}/transactions` + (search ? `?search=${encodeURIComponent(search)}` : '');
  const response = await fetch(url);
  const data = await response.json();
  renderTransactions(data);
}

async function loadAccounts(){
  const response = await fetch('/api/accounts');
  const data = await response.json();
  renderAccounts(data);
}


document.addEventListener('DOMContentLoaded', loadAccounts);
