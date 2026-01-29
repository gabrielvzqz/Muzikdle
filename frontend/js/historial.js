// Configuración
const API_BASE = window.location.origin;
const API_URL = `${API_BASE}/api`;
// Elementos DOM
const botonesGrid = document.getElementById('botones-grid');
const cargandoElement = document.getElementById('cargando');
const sinAlbumesElement = document.getElementById('sin-albumes');

/*const albumInfo = document.getElementById('album-info');
const albumTitulo = document.getElementById('album-titulo');
const albumFecha = document.getElementById('album-fecha');
const albumDescripcion = document.getElementById('album-descripcion');
const btnJugar = document.getElementById('btn-jugar-historial');
*/

// Variables
let albumes = [];
//let albumSeleccionado = null;
// ⚠️ CAMBIA ESTA FECHA a cuando empezó TU álbum
const FECHA_INICIO = '2026-01-26';
// Función para filtrar álbumes que YA HAN PASADO (fecha <= hoy)

function filtrarAlbumesPasados(albumes) {
    const hoy = new Date();
    hoy.setMonth(hoy.getMonth()); // ← 4 meses en el futuro
    hoy.setHours(0, 0, 0, 0);
    return albumes.filter(album => {
        try {
            const fechaAlbum = new Date(album.fecha_programada);
            fechaAlbum.setHours(0, 0, 0, 0);

            // Solo incluir si la fecha es HOY o ANTERIOR
            return fechaAlbum <= hoy;

        } catch (error) {
            console.error('Error filtrando álbum:', album, error);
            return false; // Excluir si hay error
        }
    });
}
// Cargar historial
async function cargarHistorial() {
    try {
        cargandoElement.style.display = 'flex';
        sinAlbumesElement.style.display = 'none';

        const response = await fetch(`${API_URL}/historial-completo`);

        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.albumes && data.albumes.length > 0) {
            // 1. Ordenar por fecha (más antiguo primero)
            let albumesOrdenados = data.albumes.sort((a, b) => {
                return new Date(a.fecha_programada) - new Date(b.fecha_programada);
            });

            // 2. FILTRAR: Solo álbumes que YA HAN PASADO (fecha <= hoy)
            albumes = filtrarAlbumesPasados(albumesOrdenados);

            console.log(`📊 Total álbumes: ${data.albumes.length}`);
            console.log(`✅ Álbumes pasados: ${albumes.length}`);

            if (albumes.length > 0) {
                console.log(`📅 Fechas disponibles: ${albumes.map(a => a.fecha_programada).join(', ')}`);
                crearBotones();
            } else {
                console.log('ℹ️ No hay álbumes pasados todavía');
                mostrarMensajeSinAlbumes();
            }

        } else {
            console.warn('⚠️ No hay álbumes, usando datos de ejemplo');
            crearDatosEjemplo();
        }

    } catch (error) {
        console.error('❌ Error cargando historial:', error);
        crearDatosEjemplo();
    } finally {
        cargandoElement.style.display = 'none';
    }
}

// Función para mostrar mensaje cuando no hay álbumes pasados
function mostrarMensajeSinAlbumes() {
    sinAlbumesElement.innerHTML = `
        <p>🎉 ¡Bienvenido al Álbum del Día!</p>
        <p>Este es el primer día del juego.</p>
        <p>Los álbumes históricos aparecerán aquí a medida que avancen los días.</p>
        <a href="index.html" class="btn-volver" style="margin-top: 1rem; display: inline-block;">
            ← Jugar al álbum de hoy
        </a>
    `;
    sinAlbumesElement.style.display = 'block';
    botonesGrid.style.display = 'none';
}

// Calcular número del día desde fecha
function calcularNumeroDia(fechaString) {
    try {
        // Parsear fechas directamente como YYYY-MM-DD
        const [yearA, monthA, dayA] = fechaString.split('-').map(Number);
        const [yearI, monthI, dayI] = FECHA_INICIO.split('-').map(Number);

        // Crear fechas UTC
        const fechaAlbum = Date.UTC(yearA, monthA - 1, dayA);
        const inicio = Date.UTC(yearI, monthI - 1, dayI);

        const diferenciaDias = Math.floor((fechaAlbum - inicio) / (1000 * 3600 * 24));

        return Math.max(1, diferenciaDias + 1);
    } catch (error) {
        console.error('Error calculando número día:', error);
        return 1;
    }
}

// Crear botones numerados (AHORA VAN DIRECTAMENTE AL JUEGO)
function crearBotones() {
    if (albumes.length === 0) {
        sinAlbumesElement.style.display = 'block';
        botonesGrid.style.display = 'none';
        return;
    }

    botonesGrid.innerHTML = '';
    botonesGrid.style.display = 'grid';

    albumes.forEach((album, index) => {
        const numeroDia = calcularNumeroDia(album.fecha_programada);
        const esDiaActual = esDiaDeHoy(album.fecha_programada);

        const boton = document.createElement('button');
        boton.className = `btn-dia ${esDiaActual ? 'actual' : ''}`;
        boton.dataset.fecha = album.fecha_programada;
        boton.dataset.numero = numeroDia;

        boton.innerHTML = `
            <div class="numero-dia">${numeroDia}</div>
        `;

        boton.addEventListener('click', () => {
            console.log(`🎮 Seleccionado Álbum #${numeroDia} (${album.fecha_programada})`);
            jugarAlbum(album.fecha_programada, numeroDia);
        });

        botonesGrid.appendChild(boton);
    });

}

// Verificar si es el día de hoy
function esDiaDeHoy(fecha) {
    const hoy = new Date().toISOString().split('T')[0];
    const fechaAlbum = new Date(fecha).toISOString().split('T')[0];

    // Imprimir ambos valores
    console.log("🔍 Debug esDiaDeHoy:");
    console.log("hoy:", hoy);
    console.log("fechaAlbum:", fechaAlbum);
    console.log("¿Son iguales?", hoy === fechaAlbum);

    return hoy === fechaAlbum;
}

// Ir directamente al álbum seleccionado
function jugarAlbum(fecha, numeroDia) {
    console.log(`🚀 Redirigiendo a Álbum #${numeroDia} (${fecha})`);

    // Usar solo parámetros URL (más limpio)
    window.location.href = `index.html?album=${fecha}&dia=${numeroDia}`;
}

// Datos de ejemplo
function crearDatosEjemplo() {
    albumes = [];
    const hoy = new Date();
    const fechaInicioObj = new Date(FECHA_INICIO);

    // Calcular días desde inicio
    const diasDesdeInicio = Math.floor((hoy - fechaInicioObj) / (1000 * 3600 * 24));
    const totalDias = Math.max(275, diasDesdeInicio + 1);

    for (let i = 0; i < totalDias; i++) {
        const fecha = new Date(fechaInicioObj);
        fecha.setDate(fecha.getDate() + i);

        albumes.push({
            fecha_programada: fecha.toISOString().split('T')[0],
            total_imagenes: 6,
            completado: true
        });
    }

    console.log(`📊 ${albumes.length} álbumes de ejemplo creados`);
    crearBotones();
}

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    cargarHistorial();

    // Ya no necesitamos el evento del botón jugar
    // porque vamos directo con cada clic en los botones de día
});