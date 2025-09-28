// script.js
document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  if (form) {
    form.addEventListener('submit', () => {
      // small feedback on submit
      alert('Your form is being submitted!');
    });
  }
});

