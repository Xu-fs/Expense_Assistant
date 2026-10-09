document.querySelectorAll('[data-demo-account]').forEach(button => {
  button.addEventListener('click', () => {
    document.getElementById('username').value = button.dataset.demoAccount;
    document.getElementById('password').value = 'demo123';
    document.querySelectorAll('[data-demo-account]').forEach(item => item.classList.remove('selected'));
    button.classList.add('selected');
    document.getElementById('username').focus();
  });
});
