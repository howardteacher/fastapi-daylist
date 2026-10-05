// 集中取得頁面節點；後續資料變動都交由 render() 更新畫面。
const list = document.querySelector('#todo-list');
const form = document.querySelector('#add-form');
const titleInput = document.querySelector('#new-title');
const message = document.querySelector('#message');
const filters = document.querySelectorAll('.filter');
// 日期只在使用者本機顯示，不影響後端的 Todo 資料。
document.querySelector('#today-date').textContent = new Intl.DateTimeFormat('zh-TW', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
}).format(new Date());
let todos = []; // 從 API 載入的完整清單，也是目前畫面的資料來源。
let currentFilter = 'all'; // all / active / completed 僅控制顯示項目。

function showError(error) {
  // 使用 textContent 顯示訊息，避免將伺服器訊息當成 HTML 執行。
  message.textContent = error.message || '操作失敗，請稍後再試。';
  message.hidden = false;
}

function clearError() {
  message.hidden = true;
  message.textContent = '';
}

async function request(path, options = {}) {
  // 共用 fetch 與錯誤處理；204 刪除回應沒有 JSON 內容。
  if (options.method && options.method !== 'GET') {
    options.headers = { ...options.headers, 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content };
  }
  const response = await fetch(path, options);
  if (response.status === 401) { window.location.assign('/login'); throw new Error('請先登入'); }
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* HTTP error without JSON */ }
    throw new Error(typeof detail === 'string' ? detail : `操作失敗（${response.status}），請稍後再試。`);
  }
  return response.status === 204 ? null : response.json();
}

document.querySelector('#logout-button').addEventListener('click', async () => {
  try {
    await request('/auth/logout', { method: 'POST' });
    window.location.assign('/login');
  } catch (error) { showError(error); }
});

async function loadTodos() {
  // API 每頁最多回傳 100 筆；持續請求直到讀完全部任務。
  const results = [];
  let page;
  do {
    page = await request(`/todos/?skip=${results.length}&limit=100`);
    results.push(...page);
  } while (page.length === 100);
  todos = results;
  render();
}

async function changeTodo(id, changes) {
  // PATCH 只提交有變動的欄位；成功後用回傳值更新本機清單。
  try {
    clearError();
    const updated = await request(`/todos/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(changes),
    });
    todos = todos.map(todo => todo.id === id ? updated : todo);
    render();
  } catch (error) {
    showError(error);
  }
}

function actionButton(text, label, onClick, className = '') {
  // 建立可供鍵盤操作的按鈕，並以 aria-label 說明操作對象。
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `icon-button ${className}`;
  button.textContent = text;
  button.setAttribute('aria-label', label);
  button.addEventListener('click', onClick);
  return button;
}

function startEdit(item, todo) {
  // 原地編輯：把任務名稱換成輸入欄，Enter 儲存、Esc 取消。
  const title = item.querySelector('.todo-title');
  const actions = item.querySelector('.todo-actions');
  const input = document.createElement('input');
  input.className = 'edit-input';
  input.type = 'text';
  input.maxLength = 255;
  input.value = todo.title;
  input.setAttribute('aria-label', '編輯任務名稱');
  title.replaceWith(input);
  actions.replaceChildren();
  const save = async () => {
    // 前端先檢查空白內容；後端仍會進行完整資料驗證。
    const value = input.value.trim();
    if (!value) { showError(new Error('任務名稱不可空白')); input.focus(); return; }
    if (value === todo.title) { render(); return; }
    saveButton.disabled = true;
    await changeTodo(todo.id, { title: value });
    saveButton.disabled = false;
  };
  const saveButton = actionButton('儲存', '儲存任務', save);
  actions.append(saveButton, actionButton('取消', '取消編輯', render));
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); save(); }
    if (event.key === 'Escape') render();
  });
  input.focus();
  input.select();
}

function render() {
  // 每次資料或篩選條件改變，統一重繪統計、分頁狀態與任務列表。
  const completed = todos.filter(todo => todo.completed).length;
  const remaining = todos.length - completed;
  document.querySelector('#progress-text').textContent = `${completed} / ${todos.length} 已完成`;
  document.querySelector('#remaining-count').textContent = `還有 ${remaining} 件待完成`;
  filters.forEach(button => {
    const selected = button.dataset.filter === currentFilter;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  });

  // 篩選後只改變畫面內容，不會刪除或修改原始清單。
  const visible = todos.filter(todo => currentFilter === 'all' || (currentFilter === 'completed' ? todo.completed : !todo.completed));
  list.replaceChildren();
  const empty = document.querySelector('#empty-state');
  empty.hidden = visible.length !== 0;
  if (visible.length === 0) {
    document.querySelector('#empty-title').textContent = todos.length ? '這裡暫時沒有任務' : '還沒有任務';
    document.querySelector('#empty-description').textContent = todos.length ? '切換其他分類，查看任務。' : '在上方輸入任務名稱，開始建立清單。';
  }

  for (const todo of visible) {
    // 使用 DOM API 與 textContent 放入任務名稱，避免 HTML 注入。
    const item = document.createElement('li');
    item.className = `todo-item${todo.completed ? ' done' : ''}`;
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'toggle';
    toggle.textContent = todo.completed ? '✓' : '';
    toggle.setAttribute('aria-label', `${todo.completed ? '標記為未完成' : '標記為完成'}：${todo.title}`);
    toggle.setAttribute('aria-pressed', String(todo.completed));
    toggle.addEventListener('click', () => changeTodo(todo.id, { completed: !todo.completed }));
    const title = document.createElement('span');
    title.className = 'todo-title';
    title.textContent = todo.title;
    const actions = document.createElement('div');
    actions.className = 'todo-actions';
    actions.append(
      actionButton('編輯', `編輯：${todo.title}`, () => startEdit(item, todo)),
      actionButton('刪除', `刪除：${todo.title}`, async () => {
        // 刪除屬於不可復原的操作，先由使用者確認。
        if (!window.confirm(`確定刪除「${todo.title}」嗎？`)) return;
        try {
          clearError();
          await request(`/todos/${todo.id}`, { method: 'DELETE' });
          todos = todos.filter(entry => entry.id !== todo.id);
          render();
        } catch (error) { showError(error); }
      }, 'danger'),
    );
    item.append(toggle, title, actions);
    list.append(item);
  }
}

form.addEventListener('submit', async event => {
  // 攔截表單送出以避免整頁重整；成功後切回「全部」顯示新任務。
  event.preventDefault();
  const title = titleInput.value.trim();
  if (!title) { showError(new Error('請輸入任務名稱')); titleInput.focus(); return; }
  const button = document.querySelector('#add-button');
  button.disabled = true;
  try {
    clearError();
    const created = await request('/todos/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    todos.unshift(created);
    titleInput.value = '';
    currentFilter = 'all';
    render();
    titleInput.focus();
  } catch (error) { showError(error); }
  finally { button.disabled = false; }
});

filters.forEach(button => button.addEventListener('click', () => {
  // 篩選不需要額外請求，直接重繪現有任務資料。
  currentFilter = button.dataset.filter;
  render();
}));

// 載入失敗時保留錯誤訊息，方便使用者辨認並排除連線問題。
loadTodos().catch(error => {
  showError(error);
  document.querySelector('#progress-text').textContent = '無法載入任務';
});
