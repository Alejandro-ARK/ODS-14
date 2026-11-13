/*
 * Reto en vivo · cliente (documento técnico, fase 5).
 *
 * Usa el WebSocket nativo del navegador. El servidor manda eventos JSON:
 *   estado      → foto completa al conectar o reconectar (RF-08)
 *   lobby       → lista de jugadores en la sala
 *   pregunta    → pregunta abierta SIN la respuesta correcta (RF-05)
 *   conteo      → cuántos han respondido (lo muestra el docente)
 *   respuesta_recibida → confirmación privada para quien respondió
 *   resultados  → respuesta correcta, aciertos y top 5 (RF-07)
 *   podio       → final de la partida
 * Todo se dibuja con textContent: los nombres de los jugadores nunca se interpretan como HTML.
 */
(function () {
  'use strict';

  var raiz = document.getElementById('reto');
  if (!raiz) return;

  var PIN = raiz.dataset.pin;
  var ES_DOCENTE = raiz.dataset.rol === 'docente';
  var COLORES = ['coral', 'azul', 'sol', 'verde'];
  var FIGURAS = ['fa-circle', 'fa-square', 'fa-star', 'fa-heart'];

  var ws = null;
  var intentos = 0;
  var relojId = null;
  var estado = 'espera';
  var preguntaActual = null;

  // ------------------------------------------------------------------ utilidades
  function $(sel, base) { return (base || raiz).querySelector(sel); }
  function $$(sel, base) { return Array.prototype.slice.call((base || raiz).querySelectorAll(sel)); }
  function texto(sel, valor, base) { var el = $(sel, base); if (el) el.textContent = valor; }
  function vaciar(el) { while (el && el.firstChild) el.removeChild(el.firstChild); }
  function crear(tag, clase, contenido) {
    var el = document.createElement(tag);
    if (clase) el.className = clase;
    if (contenido !== undefined) el.textContent = contenido;
    return el;
  }

  function mostrarVista(nombre) {
    $$('[data-vista]').forEach(function (v) { v.hidden = v.dataset.vista !== nombre; });
  }

  // ------------------------------------------------------------------ conexión
  function conectar() {
    var proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(proto + '://' + location.host + '/ws/vivo/' + PIN + '/');
    ws.onopen = function () { intentos = 0; marcarConexion(true); };
    ws.onmessage = function (e) { manejar(JSON.parse(e.data)); };
    ws.onclose = function () {
      marcarConexion(false);
      // Reintento exponencial: 1 s, 2 s, 4 s… hasta 10 s.
      setTimeout(conectar, Math.min(1000 * Math.pow(2, intentos++), 10000));
    };
  }

  function enviar(datos) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(datos));
  }

  function marcarConexion(ok) {
    var el = $('[data-conexion]');
    el.textContent = ok ? 'En vivo' : 'Sin conexión · reconectando…';
    el.classList.toggle('ok', ok);
  }

  // ------------------------------------------------------------------ eventos
  function manejar(ev) {
    switch (ev.tipo) {
      case 'estado':
        pintarJugadores(ev.jugadores);
        if (ev.yo) pintarMiMarcador(ev.yo);
        if (ev.estado === 'espera') { estado = 'espera'; mostrarVista('espera'); }
        else if (ev.estado === 'pregunta') {
          mostrarPregunta(ev.actual, ev.yo && ev.yo.respondio);
          if (ev.conteo) pintarConteo(ev.conteo);
        }
        else if (ev.estado === 'resultados') mostrarResultados(ev.actual, ev.yo);
        else if (ev.estado === 'finalizada') mostrarPodio(ev.actual, ev.yo);
        break;
      case 'lobby': pintarJugadores(ev.jugadores); break;
      case 'pregunta': mostrarPregunta(ev, false); break;
      case 'conteo': pintarConteo(ev); break;
      case 'respuesta_recibida':
        if (ev.aceptada) { mostrarVista('enviada'); texto('[data-motivo]', 'Espera a que se cierre la pregunta para saber si acertaste.'); }
        else {
          mostrarVista('enviada');
          texto('[data-motivo]', 'No se aceptó tu respuesta: ' + ev.motivo + '.');
        }
        break;
      case 'resultados': mostrarResultados(ev, ev.yo); break;
      case 'podio': mostrarPodio(ev, ev.yo); break;
    }
    actualizarControles();
  }

  // ------------------------------------------------------------------ pintar
  function pintarJugadores(jugadores) {
    $$('[data-num-jugadores]').forEach(function (el) { el.textContent = jugadores.length; });
    texto('[data-total-jugadores]', jugadores.length);
    var lista = $('[data-jugadores]');
    if (!lista) return;
    vaciar(lista);
    jugadores.forEach(function (nombre) { lista.appendChild(crear('li', '', nombre)); });
  }

  function pintarConteo(c) {
    texto('[data-respondidas]', c.respondidas);
    texto('[data-total-jugadores]', c.jugadores);
  }

  function pintarMiMarcador(yo) {
    if (!yo) return;
    texto('[data-mi-puntaje]', yo.puntaje);
    texto('[data-mi-posicion]', yo.posicion);
  }

  // Avatar del jugador: las mismas capas PNG apiladas que usa {% avatar %} en Django.
  function crearAvatar(capas, tamano, modo) {
    var cont = crear('span', 'mo-avatar-pixel mo-avatar-' + (modo || 'busto'));
    cont.style.setProperty('--tam', tamano + 'px');
    (capas || []).forEach(function (url) {
      var img = document.createElement('img');
      img.src = url; img.alt = ''; img.draggable = false;
      cont.appendChild(img);
    });
    return cont;
  }

  function pintarRanking(lista, top, avisarSiVacio) {
    vaciar(lista);
    lista.hidden = !top.length && !avisarSiVacio;
    top.forEach(function (j) {
      var li = crear('li');
      li.appendChild(crearAvatar(j.avatar, 36));
      li.appendChild(crear('span', 'nombre', j.nombre));
      li.appendChild(crear('span', 'pts', j.puntaje + ' pts'));
      lista.appendChild(li);
    });
    if (!top.length && avisarSiVacio) lista.appendChild(crear('li', 'text-muted', 'Nadie ha sumado puntos todavía.'));
  }

  function mostrarPregunta(p, yaRespondio) {
    estado = 'pregunta';
    preguntaActual = p;
    var vista = $('[data-vista="pregunta"]');
    texto('[data-progreso]', 'Pregunta ' + (p.indice + 1) + ' de ' + p.total, vista);
    texto('[data-enunciado]', p.pregunta.enunciado, vista);
    texto('[data-respondidas]', 0);

    var cont = $('[data-opciones]', vista);
    vaciar(cont);
    p.pregunta.opciones.forEach(function (op, i) {
      var b = crear(ES_DOCENTE ? 'div' : 'button', 'mo-reto-opcion mo-reto-' + COLORES[i % 4]);
      if (!ES_DOCENTE) {
        b.type = 'button';
        b.addEventListener('click', function () { responder(p.pregunta.id, op.id); });
      }
      var icono = crear('i', 'fas ' + FIGURAS[i % 4]);
      b.appendChild(icono);
      b.appendChild(crear('span', '', op.texto));
      cont.appendChild(b);
    });

    iniciarReloj(p.restante_ms, p.segundos);
    mostrarVista(yaRespondio && !ES_DOCENTE ? 'enviada' : 'pregunta');
  }

  function responder(preguntaId, opcionId) {
    $$('.mo-reto-opcion').forEach(function (b) { b.disabled = true; });   // bloquearBotones()
    enviar({ tipo: 'responder', pregunta: preguntaId, opcion: opcionId });
  }

  function iniciarReloj(restanteMs, segundos) {
    clearInterval(relojId);
    // Se usa el tiempo RESTANTE que manda el servidor: no depende del reloj del celular.
    var fin = performance.now() + restanteMs;
    function tic() {
      var ms = Math.max(0, fin - performance.now());
      $$('[data-reloj]').forEach(function (el) { el.textContent = Math.ceil(ms / 1000); });
      $$('[data-barra]').forEach(function (el) { el.style.width = (100 * ms / (segundos * 1000)) + '%'; });
      if (ms <= 0) {
        clearInterval(relojId);
        $$('button.mo-reto-opcion').forEach(function (b) { b.disabled = true; });
      }
    }
    tic();
    relojId = setInterval(tic, 100);
  }

  function mostrarResultados(r, yo) {
    estado = r.ultima ? 'ultima' : 'resultados';
    clearInterval(relojId);
    var vista = $('[data-vista="resultados"]');
    texto('[data-progreso]', 'Pregunta ' + (r.indice + 1) + ' de ' + r.total, vista);
    texto('[data-enunciado]', r.pregunta.enunciado, vista);
    texto('[data-correcta]', r.correcta ? r.correcta.texto : '—', vista);
    texto('[data-aciertos]', r.aciertos + ' de ' + r.jugadores + ' acertaron', vista);
    pintarRanking($('[data-ranking]', vista), r.top, true);

    var mio = $('[data-mi-resultado]', vista);
    if (mio && yo) {
      pintarMiMarcador(yo);
      vaciar(mio);
      var u = yo.ultima;
      mio.className = 'mo-reto-mi-resultado ' + (u && u.correcta ? 'acierto' : 'fallo');
      var titulo = !u ? 'No respondiste a tiempo' : (u.correcta ? '¡Correcto! +' + u.puntos + ' pts' : 'Incorrecto');
      mio.appendChild(crear('h3', '', titulo));
      mio.appendChild(crear('p', 'mb-0', 'Vas en el puesto ' + yo.posicion + ' con ' + yo.puntaje + ' puntos.'));
    }
    mostrarVista('resultados');
  }

  function mostrarPodio(p, yo) {
    estado = 'finalizada';
    clearInterval(relojId);
    var podio = $('[data-podio]');
    vaciar(podio);
    var medallas = ['🥇', '🥈', '🥉'];
    p.top.slice(0, 3).forEach(function (j, i) {
      var col = crear('div', 'mo-reto-escalon mo-reto-escalon-' + (i + 1));
      col.appendChild(crear('div', 'medalla', medallas[i]));
      col.appendChild(crearAvatar(j.avatar, i === 0 ? 96 : 72));
      col.appendChild(crear('div', 'nombre', j.nombre));
      col.appendChild(crear('div', 'pts', j.puntaje + ' pts'));
      podio.appendChild(col);
    });
    if (!p.top.length) podio.appendChild(crear('p', 'text-muted', 'Nadie participó en esta partida.'));
    var resto = $('[data-ranking-resto]');
    if (resto) pintarRanking(resto, p.top.slice(3));

    var mio = $('[data-mi-final]');
    if (mio && yo) {
      pintarMiMarcador(yo);
      vaciar(mio);
      mio.className = 'mo-reto-mi-resultado acierto';
      mio.appendChild(crear('h4', '', 'Quedaste en el puesto ' + yo.posicion + ' con ' + yo.puntaje + ' puntos'));
      mio.appendChild(crear('p', 'mb-0', yo.puntos_cuenta
        ? '¡Se sumaron ' + yo.puntos_cuenta + ' puntos a tu cuenta!'
        : 'Esta vez no sumaste puntos a tu cuenta. ¡A la próxima!'));
      if (yo.cuenta) {   // actualiza los contadores de la barra de navegación
        $$('.js-puntos-usuario', document).forEach(function (el) { el.textContent = yo.cuenta.disponibles; });
        $$('.js-nivel-usuario', document).forEach(function (el) { el.textContent = yo.cuenta.nivel; });
      }
    }
    mostrarVista('podio');
  }

  // ------------------------------------------------------------------ docente
  function actualizarControles() {
    if (!ES_DOCENTE) return;
    var sig = $('[data-accion="siguiente"]');
    var cerrar = $('[data-accion="cerrar"]');
    var fin = $('[data-accion="finalizar"]');
    var volver = $('[data-volver]');
    sig.hidden = estado === 'pregunta' || estado === 'finalizada';
    sig.textContent = estado === 'espera' ? 'Comenzar' : (estado === 'ultima' ? 'Ver podio' : 'Siguiente pregunta');
    cerrar.hidden = estado !== 'pregunta';
    fin.hidden = estado === 'pregunta' || estado === 'finalizada' || estado === 'ultima';
    volver.hidden = estado !== 'finalizada';
    // Durante el juego el QR se achica; al terminar ya no hace falta.
    $('[data-columna-qr]').classList.toggle('mo-reto-qr-chico', estado !== 'espera');
    $('[data-columna-qr]').hidden = estado === 'finalizada';
    $('[data-columna-escenario]').classList.toggle('mx-auto', estado === 'finalizada');
  }

  if (ES_DOCENTE) {
    $('[data-accion="siguiente"]').addEventListener('click', function () { enviar({ tipo: 'siguiente' }); });
    $('[data-accion="cerrar"]').addEventListener('click', function () { enviar({ tipo: 'cerrar' }); });
    $('[data-accion="finalizar"]').addEventListener('click', function () {
      if (confirm('¿Terminar la partida ahora? Se mostrará el podio y se sumarán los puntos.')) enviar({ tipo: 'finalizar' });
    });

    // RF-03: pedir un QR nuevo cada 5 minutos (cada token vence a los 10).
    var qr = document.getElementById('qr');
    var urlQr = raiz.dataset.urlQr;
    setInterval(function () {
      if (estado !== 'finalizada') qr.src = urlQr + '?v=' + Date.now();
    }, parseInt(raiz.dataset.qrRefresco, 10));
  }

  conectar();
})();
