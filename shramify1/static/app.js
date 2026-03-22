async function suggestServices(inputEl){
  const q = inputEl.value.trim();
  if (q.length < 1) return;
  try{
    const res = await fetch(`/api/suggest/services?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    // Simple datalist-like dropdown via title attribute for now
    inputEl.title = data.slice(0,5).join(', ');
  }catch(e){console.error(e)}
}

function addService(){
  const list = document.getElementById('services-list');
  const div = document.createElement('div');
  div.className='service-item';
  div.innerHTML = `
    <input name="service_type" placeholder="Type (e.g., electrician)">
    <input name="service_price" type="number" placeholder="Price">
    <input name="service_desc" placeholder="Short description">
    <button type="button" onclick="removeService(this)">Remove</button>
  `;
  list.appendChild(div);
}

function removeService(btn){
  btn.parentElement.remove();
}

// Simple function to ensure all elements are visible
function ensureElementsVisible() {
  const allElements = document.querySelectorAll('.landing, .promo-card, .landing-text, .landing-cards, main');
  allElements.forEach((el) => {
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
    el.style.visibility = 'visible';
    el.style.display = '';
  });
  
  // Ensure grid layouts are preserved
  const landing = document.querySelector('.landing');
  const landingCards = document.querySelector('.landing-cards');
  if (landing) landing.style.display = 'grid';
  if (landingCards) landingCards.style.display = 'grid';
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  // Ensure everything is visible immediately
  ensureElementsVisible();
  
  // Add a small delay to ensure styles are applied
  setTimeout(ensureElementsVisible, 100);

  // Only handle back button, let all other buttons work normally
  document.addEventListener('click', (e) => {
    // Only handle back button specifically
    if (e.target.id === 'back-btn' || e.target.closest('#back-btn')) {
      e.preventDefault();
      if (typeof window.smartBack === 'function') {
        window.smartBack();
      } else if (window.history.length > 1) {
        window.history.back();
      } else {
        window.location.href = '/';
      }
      return;
    }
    
    // For all other clicks, do nothing - let browser handle naturally
  });

  // Scroll reveal for smooth transitions
  try {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // Reset and trigger animation
          entry.target.style.opacity = '0';
          entry.target.style.transform = 'translateY(6px)';
          setTimeout(() => {
            entry.target.classList.add('fade-in');
          }, 10);
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 });

    const sel = [
      '.card',
      '.promo-card',
      '.landing',
      '.grid > *',
      '.list .card',
      'section',
    ].join(',');
    
    // Only observe elements that don't already have fade-in class
    document.querySelectorAll(sel).forEach(el => {
      if (!el.classList.contains('fade-in')) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(6px)';
        io.observe(el);
      }
    });
  } catch(_) {}
});
