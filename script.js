/* ============================================
   21 день с ИИ — Landing Page Scripts
   ============================================ */

(function () {
  'use strict';

  /* ----------------------------------------
     Header: scroll shadow + burger menu
     ---------------------------------------- */
  const header = document.getElementById('header');
  const burger = document.getElementById('burger');
  const nav = document.getElementById('nav');

  window.addEventListener('scroll', function () {
    header.classList.toggle('header--scrolled', window.scrollY > 20);
  });

  burger.addEventListener('click', function () {
    burger.classList.toggle('active');
    nav.classList.toggle('open');
  });

  nav.querySelectorAll('.header__link').forEach(function (link) {
    link.addEventListener('click', function () {
      burger.classList.remove('active');
      nav.classList.remove('open');
    });
  });

  /* ----------------------------------------
     Scroll-reveal animation
     ---------------------------------------- */
  var revealTargets =
    '.problem-card, .whom-card, .day-card, .result-card, .tool-tag, ' +
    '.method-card, .price-card, .bonus-card, .faq-item, .week__header';

  document.querySelectorAll(revealTargets).forEach(function (el) {
    el.classList.add('reveal');
  });

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  document.querySelectorAll('.reveal').forEach(function (el) {
    observer.observe(el);
  });

  /* ----------------------------------------
     Staggered reveal for grid children
     ---------------------------------------- */
  document.querySelectorAll('.reveal').forEach(function (el, i) {
    var siblings = Array.from(el.parentElement.children).filter(function (c) {
      return c.classList.contains('reveal');
    });
    var idx = siblings.indexOf(el);
    el.style.transitionDelay = (idx * 0.07) + 's';
  });

  /* ----------------------------------------
     Smooth anchor offset (account for header)
     ---------------------------------------- */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var id = this.getAttribute('href');
      if (id === '#') return;
      var target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        var offset = header.offsetHeight + 16;
        var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });

})();

/* ============================================
   Modal
   ============================================ */
var modalOverlay = document.getElementById('modalOverlay');
var modalForm = document.getElementById('enrollForm');
var modalSuccess = document.getElementById('modalSuccess');
var selectedPlanEl = document.getElementById('selectedPlan');
var userPlanSelect = document.getElementById('userPlan');

function openModal(planLabel) {
  modalForm.style.display = '';
  modalSuccess.style.display = 'none';
  modalForm.reset();

  if (planLabel) {
    selectedPlanEl.textContent = planLabel;
    if (planLabel.indexOf('14') !== -1) {
      userPlanSelect.value = '14';
    } else {
      userPlanSelect.value = '21';
    }
  } else {
    selectedPlanEl.textContent = '';
  }

  modalOverlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modalOverlay.classList.remove('active');
  document.body.style.overflow = '';
}

modalOverlay.addEventListener('click', function (e) {
  if (e.target === modalOverlay) closeModal();
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    if (document.getElementById('rulesModalOverlay').classList.contains('active')) closeRulesModal();
    else if (modalOverlay.classList.contains('active')) closeModal();
  }
});

function openRulesModal() {
  document.getElementById('rulesModalOverlay').classList.add('active');
  document.body.style.overflow = 'hidden';
}
function closeRulesModal() {
  document.getElementById('rulesModalOverlay').classList.remove('active');
  document.body.style.overflow = '';
}
document.getElementById('rulesModalOverlay').addEventListener('click', function (e) {
  if (e.target === this) closeRulesModal();
});

/* ============================================
   Form submission — Robokassa
   ============================================ */
function handleSubmit(e) {
  e.preventDefault();

  var data = {
    name: document.getElementById('userName').value,
    email: document.getElementById('userEmail').value,
    phone: document.getElementById('userPhone').value,
    plan: userPlanSelect.value,
    specialty: document.getElementById('userSpecialty').value,
    origin: window.location.origin
  };

  var btn = modalForm.querySelector('button[type="submit"]');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Переход к оплате...';
  }

  fetch('/api/create-payment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.paymentUrl) {
        window.location.href = result.paymentUrl;
      } else {
        throw new Error(result.error || 'Ошибка создания платежа');
      }
    })
    .catch(function (err) {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Записаться и оплатить';
      }
      alert('Не удалось перейти к оплате. Попробуйте позже или свяжитесь с нами: info@i-integrator.com');
      console.error(err);
    });
}

/* Phone: без маски — любой формат (+7, +1, +44 и т.д.) */
