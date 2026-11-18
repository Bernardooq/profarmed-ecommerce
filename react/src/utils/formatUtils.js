/**
 * Utilidades de formateo para la aplicación.
 * 
 * IMPORTANTE: Estas funciones son solo para visualización.
 * Los datos enviados al backend deben mantenerse como números o strings numéricos sin comas.
 */

/**
 * Formatea un número como moneda (MXN) con separador de miles.
 * Ejemplo: 1837.93 -> $1,837.93
 * 
 * @param {number|string} amount - El monto a formatear
 * @returns {string} - El monto formateado
 */
export const formatCurrency = (amount) => {
  if (amount === undefined || amount === null || isNaN(parseFloat(amount))) {
    return '$0.00';
  }
  
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
};

/**
 * Formatea un número con separador de miles sin el símbolo de moneda.
 * Ejemplo: 1837.93 -> 1,837.93
 */
export const formatNumber = (number) => {
  if (number === undefined || number === null || isNaN(parseFloat(number))) {
    return '0.00';
  }

  return new Intl.NumberFormat('es-MX', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(number);
};
/**
 * Obtiene la fecha en formato 'YYYY-MM-DD' en la zona horaria de México (America/Mexico_City).
 * Ideal para rangos de búsqueda y filtros de reportes.
 */
export const getMexicoDateString = (date = new Date()) => {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Mexico_City',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date);
};

/**
 * Formatea una fecha y hora completa en horario de México (America/Mexico_City).
 * Ejemplo: "20/09/2026, 12:15 p.m."
 */
export const formatMexicoDateTime = (dateString, options = {}) => {
  if (!dateString) return 'N/A';
  const d = new Date(dateString);
  return d.toLocaleString('es-MX', {
    timeZone: 'America/Mexico_City',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    ...options
  });
};

/**
 * Formatea solo la fecha (día/mes/año) en horario de México (America/Mexico_City).
 * Ejemplo: "20/09/2026"
 */
export const formatMexicoDate = (dateString, options = {}) => {
  if (!dateString) return 'N/A';
  const d = new Date(dateString);
  return d.toLocaleDateString('es-MX', {
    timeZone: 'America/Mexico_City',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...options
  });
};

/**
 * Convierte cualquier fecha a string compatible con input type="datetime-local" (YYYY-MM-DDTHH:mm)
 * garantizando que refleje la hora de México sin desfasarse al editar.
 */
export const toDateTimeLocalString = (dateInput) => {
  if (!dateInput) return '';
  const d = new Date(dateInput);
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Mexico_City',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  });
  const parts = formatter.formatToParts(d);
  const getPart = (t) => parts.find(p => p.type === t)?.value || '00';
  return `${getPart('year')}-${getPart('month')}-${getPart('day')}T${getPart('hour')}:${getPart('minute')}`;
};

/**
 * Convierte un string de input datetime-local (hora local de México) a ISO UTC string.
 * Se asegura de interpretar la hora en UTC-6 (horario estándar de México).
 */
export const mexicoLocalToUtcIso = (dateTimeLocalStr) => {
  if (!dateTimeLocalStr) return null;
  const fullStr = dateTimeLocalStr.length === 16 ? `${dateTimeLocalStr}:00-06:00` : (dateTimeLocalStr.includes('-06:00') ? dateTimeLocalStr : `${dateTimeLocalStr}-06:00`);
  return new Date(fullStr).toISOString();
};
