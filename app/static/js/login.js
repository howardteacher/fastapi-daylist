const form = document.querySelector('#auth-form');
const message = document.querySelector('#message');
let registering = false;

document.querySelector('#switch-button').addEventListener('click', () => {
  registering = !registering;
  document.querySelector('#auth-title').textContent = registering ? '註冊帳號' : '登入帳號';
  document.querySelector('#submit-button').textContent = registering ? '註冊' : '登入';
  document.querySelector('#switch-button').textContent = registering ? '已有帳號？登入' : '還沒有帳號？註冊';
  document.querySelector('#password').autocomplete = registering ? 'new-password' : 'current-password';
  message.hidden = true;
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.querySelector('#submit-button');
  button.disabled = true;
  message.hidden = true;
  try {
    const response = await fetch(registering ? '/auth/register' : '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content },
      body: JSON.stringify({ username: document.querySelector('#username').value, password: document.querySelector('#password').value }),
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(typeof result.detail === 'string' ? result.detail : '帳號或密碼格式錯誤');
    }
    window.location.assign('/');
  } catch (error) {
    message.textContent = error.message || '連線失敗，請稍後再試';
    message.hidden = false;
  } finally {
    button.disabled = false;
  }
});
