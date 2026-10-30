const VERSION = 'v1';
const PREFIJO = 'sgd-personal-';
const CACHE = PREFIJO + VERSION;
const ESPERA_MS = 4000;

const PAGINA = new URL('generador_personal.html', self.location).href;
const CALCULO = new URL('personal_calculo.js', self.location).href;
const ESTADO = new URL('personal_estado.js', self.location).href;
const ARCHIVOS = [PAGINA, CALCULO, ESTADO];

function urlLimpia(valor) {
  const url = new URL(valor);
  url.search = '';
  url.hash = '';
  return url.href;
}

async function guardarDesdeRed(cache, url) {
  try {
    const respuesta = await fetch(url, { cache: 'no-cache' });
    if (respuesta.ok) {
      await cache.put(url, respuesta);
    }
  } catch (error) {
    // Cada archivo se intenta de forma independiente.
  }
}

async function instalar() {
  const cache = await caches.open(CACHE);
  await Promise.all(ARCHIVOS.map(function (url) {
    return guardarDesdeRed(cache, url);
  }));

  if (!await cache.match(PAGINA)) {
    throw new Error('No se pudo guardar la pagina principal');
  }

  await self.skipWaiting();
}

self.addEventListener('install', function (evento) {
  evento.waitUntil(instalar());
});

async function activar() {
  const nombres = await caches.keys();
  const antiguas = nombres.filter(function (nombre) {
    return nombre.startsWith(PREFIJO) && nombre !== CACHE;
  });

  await Promise.all(antiguas.map(function (nombre) {
    return caches.delete(nombre);
  }));
  await self.clients.claim();
}

self.addEventListener('activate', function (evento) {
  evento.waitUntil(activar());
});

async function guardarRespuesta(clave, respuesta) {
  if (!respuesta.ok) {
    return;
  }

  try {
    const cache = await caches.open(CACHE);
    await cache.put(clave, respuesta.clone());
  } catch (error) {
    // La respuesta de red sigue siendo valida aunque falle la cache.
  }
}

async function pedirRed(peticion, clave) {
  const respuesta = await fetch(peticion.url, { cache: 'no-cache' });
  if (respuesta.ok) {
    await guardarRespuesta(clave, respuesta);
  }
  return respuesta;
}

function demora() {
  return new Promise(function (resolver) {
    setTimeout(function () {
      resolver({ tipo: 'tiempo' });
    }, ESPERA_MS);
  });
}

async function marcarCopia(respuesta, esEstado) {
  if (!esEstado) {
    return respuesta;
  }
  const salto = String.fromCharCode(10);
  const texto = await respuesta.text();
  const marca = 'window.__sgdOrigen = "copia";';
  return new Response(texto + salto + marca + salto, {
    headers: {
      'Content-Type': 'text/javascript; charset=utf-8'
    }
  });
}

async function responder(clave, esEstado, redPendiente) {
  const resultadoRed = redPendiente.then(function (respuesta) {
    return { tipo: 'red', respuesta: respuesta };
  }, function (error) {
    return { tipo: 'fallo', error: error };
  });
  const primero = await Promise.race([resultadoRed, demora()]);

  if (primero.tipo === 'tiempo') {
    const copia = await buscarCopia(clave, esEstado);
    if (copia) {
      return copia;
    }
    return redPendiente;
  }

  if (primero.tipo === 'red' && primero.respuesta.ok) {
    return primero.respuesta;
  }

  const copia = await buscarCopia(clave, esEstado);
  if (copia) {
    return copia;
  }
  if (primero.tipo === 'red') {
    return primero.respuesta;
  }
  throw primero.error;
}

async function buscarCopia(clave, esEstado) {
  const cache = await caches.open(CACHE);
  const copia = await cache.match(clave);
  return copia ? marcarCopia(copia, esEstado) : null;
}

self.addEventListener('fetch', function (evento) {
  if (evento.request.method !== 'GET') {
    return;
  }

  const clave = urlLimpia(evento.request.url);
  if (!ARCHIVOS.includes(clave)) {
    return;
  }

  const redPendiente = pedirRed(evento.request, clave);
  evento.waitUntil(redPendiente.then(function () {}, function () {}));
  evento.respondWith(responder(clave, clave === ESTADO, redPendiente));
});
