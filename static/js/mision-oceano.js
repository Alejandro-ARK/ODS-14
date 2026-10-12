/* ===========================================================
   Misión Océano - lógica compartida (quiz, juego, checklist)
   Se ejecuta de forma progresiva: cada bloque revisa si sus
   elementos existen en la página antes de activarse.
   =========================================================== */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    inicializarQuiz();
    inicializarMemoria();
    inicializarRecolector();
    inicializarChecklistActua();
  });

  /* Envía puntos ganados al servidor (solo si el usuario está logueado).
     La URL del endpoint viene de <body data-url-guardar-puntos="...">, que
     Django solo escribe cuando hay sesión iniciada. */
  function guardarPuntos(puntos, motivo) {
    var url = document.body.dataset.urlGuardarPuntos;
    if (!url) return; // visitante sin sesión: no hay nada que guardar

    var meta = document.querySelector('meta[name="csrf-token"]');
    var body = new URLSearchParams();
    body.set('puntos', puntos);
    body.set('motivo', motivo || '');

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': meta ? meta.content : ''
      },
      body: body.toString()
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.ok) {
          var badges = document.querySelectorAll('.js-puntos-usuario');
          badges.forEach(function (b) { b.textContent = data.puntos; });
          var niveles = document.querySelectorAll('.js-nivel-usuario');
          niveles.forEach(function (n) { n.textContent = data.nivel; });
        }
      })
      .catch(function () { /* si falla, no interrumpe la experiencia */ });
  }
  window.MisionOceano = window.MisionOceano || {};
  window.MisionOceano.guardarPuntos = guardarPuntos;

  /* ======================= QUIZ ======================= */
  function inicializarQuiz() {
    var contenedor = document.getElementById('quiz-contenedor');
    if (!contenedor) return;

    var preguntas = Array.prototype.slice.call(contenedor.querySelectorAll('.quiz-pregunta'));
    var total = preguntas.length;
    var indice = 0;
    var aciertos = 0;

    var barra = document.getElementById('quiz-progreso');
    var contador = document.getElementById('quiz-contador');
    var resultado = document.getElementById('quiz-resultado');
    var resumen = document.getElementById('quiz-resumen') || resultado;
    var guardarBtn = document.getElementById('quiz-guardar-puntos');

    function mostrarPregunta(i) {
      preguntas.forEach(function (p, idx) {
        p.classList.toggle('activa', idx === i);
      });
      if (contador) contador.textContent = 'Pregunta ' + (i + 1) + ' de ' + total;
      if (barra) barra.style.width = Math.round((i / total) * 100) + '%';
    }

    preguntas.forEach(function (pregunta) {
      var opciones = pregunta.querySelectorAll('.quiz-opcion');
      opciones.forEach(function (opcion) {
        opcion.addEventListener('click', function () {
          if (pregunta.dataset.respondida === '1') return;
          pregunta.dataset.respondida = '1';

          var esCorrecta = opcion.dataset.correcta === '1';
          opciones.forEach(function (o) { o.disabled = true; });

          if (esCorrecta) {
            opcion.classList.add('correcta');
            aciertos++;
          } else {
            opcion.classList.add('incorrecta');
            var correctaReal = pregunta.querySelector('[data-correcta="1"]');
            if (correctaReal) correctaReal.classList.add('correcta');
          }

          setTimeout(function () {
            if (indice < total - 1) {
              indice++;
              mostrarPregunta(indice);
            } else {
              finalizarQuiz();
            }
          }, 900);
        });
      });
    });

    function finalizarQuiz() {
      if (barra) barra.style.width = '100%';
      if (contador) contador.textContent = 'Quiz completado';
      preguntas.forEach(function (p) { p.classList.remove('activa'); });

      if (resultado) {
        resultado.style.display = 'block';
        var puntaje = Math.round((aciertos / total) * 100);
        var puntosGanados = aciertos * 10;
        resumen.innerHTML =
          '<h4><i class="fas fa-medal text-warning mr-1"></i> Obtuviste ' + aciertos + ' de ' + total + ' (' + puntaje + '%)</h4>' +
          '<p>' + mensajeSegunPuntaje(puntaje) + '</p>';

        if (guardarBtn) {
          guardarBtn.style.display = 'inline-block';
          guardarBtn.dataset.puntos = puntosGanados;
        }
      }
    }

    function mensajeSegunPuntaje(p) {
      if (p === 100) return '¡Perfecto! Conoces muy bien el ODS 14. 🌊';
      if (p >= 70) return '¡Muy bien! Vas por buen camino para ser un defensor del océano.';
      if (p >= 40) return 'Buen intento, repasa la sección "Aprende" y vuelve a intentarlo.';
      return 'No te preocupes, visita "Aprende" para reforzar estos temas y vuelve a intentarlo.';
    }

    if (guardarBtn) {
      guardarBtn.addEventListener('click', function () {
        var puntos = parseInt(guardarBtn.dataset.puntos || '0', 10);
        guardarPuntos(puntos, 'quiz');
        guardarBtn.disabled = true;
        guardarBtn.textContent = '¡Puntos guardados!';
      });
    }

    mostrarPregunta(0);
  }

  /* ======================= JUEGO DE MEMORIA ======================= */
  function inicializarMemoria() {
    var tablero = document.getElementById('memoria-tablero');
    if (!tablero) return;

    var simbolosBase = ['🐠', '🐢', '🐬', '🦀', '🐙', '🦈', '🪸', '🦑'];
    var estadoMensaje = document.getElementById('memoria-mensaje');
    var reiniciarBtn = document.getElementById('memoria-reiniciar');

    var cartas = [];
    var primeraCarta = null;
    var segundaCarta = null;
    var bloqueado = false;
    var paresEncontrados = 0;
    var intentos = 0;

    function crearBaraja() {
      var simbolos = simbolosBase.concat(simbolosBase);
      for (var i = simbolos.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = simbolos[i];
        simbolos[i] = simbolos[j];
        simbolos[j] = tmp;
      }
      return simbolos;
    }

    function construirTablero() {
      tablero.innerHTML = '';
      cartas = [];
      primeraCarta = null;
      segundaCarta = null;
      bloqueado = false;
      paresEncontrados = 0;
      intentos = 0;
      if (estadoMensaje) estadoMensaje.textContent = 'Encuentra las parejas de criaturas marinas.';

      var simbolos = crearBaraja();
      simbolos.forEach(function (simbolo) {
        var carta = document.createElement('div');
        carta.className = 'memoria-carta';
        carta.innerHTML =
          '<span class="cara-oculta"><i class="fas fa-water"></i></span>' +
          '<span class="cara-simbolo">' + simbolo + '</span>';
        carta.dataset.simbolo = simbolo;
        carta.addEventListener('click', function () { voltear(carta); });
        tablero.appendChild(carta);
        cartas.push(carta);
      });
    }

    function voltear(carta) {
      if (bloqueado) return;
      if (carta.classList.contains('volteada') || carta.classList.contains('encontrada')) return;

      carta.classList.add('volteada');

      if (!primeraCarta) {
        primeraCarta = carta;
        return;
      }

      segundaCarta = carta;
      intentos++;
      bloqueado = true;

      if (primeraCarta.dataset.simbolo === segundaCarta.dataset.simbolo) {
        primeraCarta.classList.add('encontrada');
        segundaCarta.classList.add('encontrada');
        paresEncontrados++;
        resetearSeleccion();

        if (paresEncontrados === simbolosBase.length) {
          var puntos = Math.max(80 - intentos * 2, 20);
          if (estadoMensaje) {
            estadoMensaje.innerHTML =
              '¡Completaste el juego en ' + intentos + ' intentos! Ganaste <strong>' + puntos + ' puntos</strong>.';
          }
          guardarPuntos(puntos, 'memoria');
        }
      } else {
        setTimeout(function () {
          primeraCarta.classList.remove('volteada');
          segundaCarta.classList.remove('volteada');
          resetearSeleccion();
        }, 800);
      }
    }

    function resetearSeleccion() {
      primeraCarta = null;
      segundaCarta = null;
      bloqueado = false;
    }

    if (reiniciarBtn) {
      reiniciarBtn.addEventListener('click', construirTablero);
    }

    construirTablero();
  }

  /* ======================= RECOLECTA LA BASURA ======================= */
  function inicializarRecolector() {
    var canvas = document.getElementById('recolector-canvas');
    if (!canvas) return;

    var ctx = canvas.getContext('2d');
    var overlay = document.getElementById('recolector-overlay');
    var iniciarBtn = document.getElementById('recolector-iniciar');
    var puntosEl = document.getElementById('recolector-puntos');
    var vidasEl = document.getElementById('recolector-vidas');
    var tiempoEl = document.getElementById('recolector-tiempo');

    var ANCHO = canvas.width;
    var ALTO = canvas.height;
    var DURACION_TOTAL = 45; // segundos
    var VIDAS_INICIALES = 3;

    var BASURA = ['🗑️', '🛍️', '🧴', '🥤', '🧃'];
    var ANIMALES = ['🐠', '🐢', '🐬', '🦀', '🐙'];

    var basket = { x: ANCHO / 2, anchoMedio: 42, y: ALTO - 34, alto: 26 };
    var items = [];
    var puntos = 0;
    var vidas = VIDAS_INICIALES;
    var tiempoRestante = DURACION_TOTAL;
    var jugando = false;
    var acumuladorSpawn = 0;
    var intervaloSpawn = 1000;
    var ultimoTimestamp = null;
    var intervaloReloj = null;

    function posicionPuntero(evento) {
      var rect = canvas.getBoundingClientRect();
      var clientX = evento.touches ? evento.touches[0].clientX : evento.clientX;
      var escalaX = ANCHO / rect.width;
      var x = (clientX - rect.left) * escalaX;
      basket.x = Math.max(basket.anchoMedio, Math.min(ANCHO - basket.anchoMedio, x));
    }
    canvas.addEventListener('mousemove', posicionPuntero);
    canvas.addEventListener('touchmove', function (e) {
      posicionPuntero(e);
      e.preventDefault();
    }, { passive: false });

    function nuevoItem() {
      var esBasura = Math.random() < 0.7; // 70% basura, 30% animales a evitar
      var lista = esBasura ? BASURA : ANIMALES;
      items.push({
        x: Math.random() * (ANCHO - 40) + 20,
        y: -20,
        velocidad: 60 + Math.random() * 60 + (DURACION_TOTAL - tiempoRestante) * 1.2,
        simbolo: lista[Math.floor(Math.random() * lista.length)],
        tipo: esBasura ? 'basura' : 'animal',
        radio: 16,
        atrapado: false
      });
    }

    function actualizar(dt) {
      acumuladorSpawn += dt * 1000;
      if (acumuladorSpawn > intervaloSpawn) {
        acumuladorSpawn = 0;
        nuevoItem();
      }

      for (var i = items.length - 1; i >= 0; i--) {
        var it = items[i];
        it.y += it.velocidad * dt;

        var chocaConRed =
          it.y + it.radio >= basket.y &&
          it.y - it.radio <= basket.y + basket.alto &&
          it.x >= basket.x - basket.anchoMedio &&
          it.x <= basket.x + basket.anchoMedio;

        if (chocaConRed) {
          if (it.tipo === 'basura') {
            puntos += 10;
          } else {
            puntos = Math.max(0, puntos - 5);
            vidas -= 1;
          }
          items.splice(i, 1);
          actualizarMarcador();
          if (vidas <= 0) {
            terminarJuego(false);
            return;
          }
          continue;
        }

        if (it.y - it.radio > ALTO) {
          items.splice(i, 1);
        }
      }
    }

    function dibujar() {
      ctx.clearRect(0, 0, ANCHO, ALTO);

      // Suelo marino
      ctx.fillStyle = 'rgba(2,48,71,0.25)';
      ctx.fillRect(0, ALTO - 14, ANCHO, 14);

      // Items
      ctx.font = '28px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      items.forEach(function (it) {
        ctx.fillText(it.simbolo, it.x, it.y);
      });

      // Red / canasta
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(basket.x - basket.anchoMedio, basket.y);
      ctx.lineTo(basket.x + basket.anchoMedio, basket.y);
      ctx.lineTo(basket.x + basket.anchoMedio - 10, basket.y + basket.alto);
      ctx.lineTo(basket.x - basket.anchoMedio + 10, basket.y + basket.alto);
      ctx.closePath();
      ctx.stroke();
      ctx.font = '22px sans-serif';
      ctx.fillText('🥅', basket.x, basket.y + basket.alto / 2);
    }

    function bucle(timestamp) {
      if (!jugando) return;
      if (!ultimoTimestamp) ultimoTimestamp = timestamp;
      var dt = Math.min((timestamp - ultimoTimestamp) / 1000, 0.05);
      ultimoTimestamp = timestamp;

      actualizar(dt);
      if (!jugando) return; // pudo terminar dentro de actualizar()
      dibujar();
      requestAnimationFrame(bucle);
    }

    function actualizarMarcador() {
      if (puntosEl) puntosEl.textContent = puntos;
      if (vidasEl) vidasEl.textContent = vidas;
      if (tiempoEl) tiempoEl.textContent = tiempoRestante;
    }

    function iniciarJuego() {
      items = [];
      puntos = 0;
      vidas = VIDAS_INICIALES;
      tiempoRestante = DURACION_TOTAL;
      jugando = true;
      ultimoTimestamp = null;
      acumuladorSpawn = 0;
      actualizarMarcador();
      if (overlay) overlay.style.display = 'none';

      intervaloReloj = setInterval(function () {
        tiempoRestante -= 1;
        actualizarMarcador();
        if (tiempoRestante <= 0) {
          terminarJuego(true);
        }
      }, 1000);

      requestAnimationFrame(bucle);
    }

    function terminarJuego(porTiempo) {
      jugando = false;
      clearInterval(intervaloReloj);
      dibujar();

      if (overlay) {
        overlay.style.display = 'flex';
        var titulo = porTiempo ? '¡Tiempo!' : '¡Te quedaste sin vidas!';
        overlay.innerHTML =
          '<h4>' + titulo + '</h4>' +
          '<p>Puntaje final: <strong>' + puntos + '</strong></p>' +
          '<button id="recolector-iniciar" class="btn btn-lg btn-success mt-2">' +
          '<i class="fas fa-rotate-right mr-1"></i> Jugar de nuevo</button>';
        document.getElementById('recolector-iniciar').addEventListener('click', iniciarJuego);
      }

      if (puntos > 0) {
        guardarPuntos(Math.min(puntos, 100), 'recolector');
      }
    }

    if (iniciarBtn) iniciarBtn.addEventListener('click', iniciarJuego);
    dibujar();
  }

  /* ======================= CHECKLIST "ACTÚA" ======================= */
  function inicializarChecklistActua() {
    var lista = document.getElementById('checklist-actua');
    if (!lista) return;

    var CLAVE = 'mision-oceano-checklist';
    var guardados = {};
    try {
      guardados = JSON.parse(localStorage.getItem(CLAVE) || '{}');
    } catch (e) {
      guardados = {};
    }

    var casillas = lista.querySelectorAll('.checklist-item input[type="checkbox"]');

    function actualizarContador() {
      var contador = document.getElementById('checklist-contador');
      if (!contador) return;
      var marcadas = lista.querySelectorAll('.checklist-item input[type="checkbox"]:checked').length;
      contador.textContent = marcadas + ' de ' + casillas.length + ' acciones completadas';
    }

    casillas.forEach(function (casilla) {
      var id = casilla.id;
      if (guardados[id]) {
        casilla.checked = true;
        casilla.closest('.checklist-item').classList.add('completado');
      }
      casilla.addEventListener('change', function () {
        guardados[id] = casilla.checked;
        localStorage.setItem(CLAVE, JSON.stringify(guardados));
        casilla.closest('.checklist-item').classList.toggle('completado', casilla.checked);
        actualizarContador();
      });
    });

    actualizarContador();
  }
})();
