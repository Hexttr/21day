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
    '.method-card, .principle, .price-card, .bonus-card, .faq-item, ' +
    '.week__header';

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
  if (e.key === 'Escape') closeModal();
});

/* ============================================
   Form submission
   
   ROBOKASSA: Замените содержимое handleSubmit
   на редирект к Робокассе при подключении оплаты.
   Пример интеграции:
   
   function handleSubmit(e) {
     e.preventDefault();
     var formData = new FormData(modalForm);
     // 1. Отправить данные на ваш бэкенд
     // 2. Бэкенд создает заказ и возвращает URL Робокассы
     // 3. Редирект: window.location.href = robokassaUrl;
   }
   ============================================ */
function handleSubmit(e) {
  e.preventDefault();

  var data = {
    name: document.getElementById('userName').value,
    email: document.getElementById('userEmail').value,
    phone: document.getElementById('userPhone').value,
    plan: userPlanSelect.value,
    specialty: document.getElementById('userSpecialty').value,
    timestamp: new Date().toISOString()
  };

  console.log('Заявка:', data);

  /* 
     TODO: Отправка данных на сервер
     
     fetch('/api/enroll', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(data)
     })
     .then(res => res.json())
     .then(result => {
       // Редирект на оплату Робокасса
       // window.location.href = result.paymentUrl;
     });
  */

  modalForm.style.display = 'none';
  modalSuccess.style.display = '';
}

/* ============================================
   Phone input mask (basic)
   ============================================ */
(function () {
  var phoneInput = document.getElementById('userPhone');
  phoneInput.addEventListener('input', function (e) {
    var x = e.target.value.replace(/\D/g, '');
    if (x.length === 0) {
      e.target.value = '';
      return;
    }
    var formatted = '+7';
    if (x.length > 1) formatted += ' (' + x.substring(1, 4);
    if (x.length >= 4) formatted += ') ' + x.substring(4, 7);
    if (x.length >= 7) formatted += '-' + x.substring(7, 9);
    if (x.length >= 9) formatted += '-' + x.substring(9, 11);
    e.target.value = formatted;
  });
})();
