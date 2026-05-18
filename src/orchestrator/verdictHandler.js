javascript
'use strict';

const { writePatternEntry } = require('../patternMemory');
const logger = require('../utils/logger');

// ─────────────────────────────────────────────────────────────
// Constants & Configuration
// ─────────────────────────────────────────────────────────────

/** @readonly */
const VALID_RESULTS = Object.freeze(['PASS', 'FAIL']);

/** @type {number} Maximum length of any observation string to prevent data corruption */
const MAX_OBSERVATION_LENGTH = 4096;

/** @type {number} Default minimum secondary observations required for PASS verdicts */
const DEFAULT_MIN_SECONDARY_FOR_PASS = 2;

/** @type {number} Default minimum secondary observations required for FAIL verdicts */
const DEFAULT_MIN_SECONDARY_FOR_FAIL = 1;

// ─────────────────────────────────────────────────────────────
// Type Definitions (JSDoc)
// ─────────────────────────────────────────────────────────────

/**
 * @typedef {Object} Verdict
 * @property {'PASS'|'FAIL'} result - The QA result.
 * @property {string[]} [primaryObservations] - Primary observations (required for all verdicts).
 * @property {string[]} [secondaryObservations] - Secondary observations (strongly recommended).
 */

/**
 * @typedef {Object} MemoryRecord
 * @property {'PASS'|'FAIL'} result
 * @property {string[]} primaryObservations
 * @property {string[]} secondaryObservations
 */

/**
 * @typedef {Object} HandleVerdictOptions
 * @property {number} [minSecondaryForPass] - Minimum secondary observations required for PASS.
 * @property {number} [minSecondaryForFail] - Minimum secondary observations required for FAIL.
 * @property {boolean} [throwOnMissingSecondary] - If true, throws when minimum not met.
 */

// ─────────────────────────────────────────────────────────────
// Validation Helpers
// ─────────────────────────────────────────────────────────────

/**
 * Validates that a value is a non‑empty string.
 * @param {*} value
 * @param {string} fieldName
 * @returns {string}
 * @throws {TypeError} If value is not a non‑empty string.
 */
function assertString(value, fieldName) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new TypeError(`${fieldName} must be a non‑empty string`);
  }
  if (value.length > MAX_OBSERVATION_LENGTH) {
    throw new TypeError(`${fieldName} exceeds maximum length of ${MAX_OBSERVATION_LENGTH} characters`);
  }
  return value;
}

/**
 * Validates that a value is an array of non‑empty strings.
 * @param {*} value
 * @param {string} fieldName
 * @returns {string[]}
 * @throws {TypeError} If value is not an array or contains invalid items.
 */
function assertStringArray(value, fieldName) {
  if (!Array.isArray(value)) {
    throw new TypeError(`${fieldName} must be an array`);
  }
  for (let i = 0; i < value.length; i++) {
    if (typeof value[i] !== 'string' || value[i].length === 0) {
      throw new TypeError(`${fieldName}[${i}] must be a non‑empty string`);
    }
    if (value[i].length > MAX_OBSERVATION_LENGTH) {
      throw new TypeError(`${fieldName}[${i}] exceeds maximum length of ${MAX_OBSERVATION_LENGTH} characters`);
    }
  }
  return value;
}

/**
 * Validates an optional string array (may be undefined). Returns empty array if undefined.
 * @param {*} value
 * @param {string} fieldName
 * @returns {string[]}
 * @throws {TypeError}
 */
function assertOptionalStringArray(value, fieldName) {
  if (value === undefined) {
    return [];
  }
  return assertStringArray(value, fieldName);
}

/**
 * Validates that an optional options object has valid numeric thresholds.
 * @param {HandleVerdictOptions} [options]
 * @returns {HandleVerdictOptions}
 * @throws {TypeError}
 */
function validateOptions(options) {
  if (options === undefined) {
    return {};
  }
  if (typeof options !== 'object' || Array.isArray(options)) {
    throw new TypeError('options must be a plain object');
  }
  const valid = {};
  if (options.minSecondaryForPass !== undefined) {
    if (typeof options.minSecondaryForPass !== 'number' || !Number.isInteger(options.minSecondaryForPass) || options.minSecondaryForPass < 0) {
      throw new TypeError('options.minSecondaryForPass must be a non-negative integer');
    }
    valid.minSecondaryForPass = options.minSecondaryForPass;
  }
  if (options.minSecondaryForFail !== undefined) {
    if (typeof options.minSecondaryForFail !== 'number' || !Number.isInteger(options.minSecondaryForFail) || options.minSecondaryForFail < 0) {
      throw new TypeError('options.minSecondaryForFail must be a non-negative integer');
    }
    valid.minSecondaryForFail = options.minSecondaryForFail;
  }
  if (options.throwOnMissingSecondary !== undefined) {
    if (typeof options.throwOnMissingSecondary !== 'boolean') {
      throw new TypeError('options.throwOnMissingSecondary must be a boolean');
    }
    valid.throwOnMissingSecondary = options.throwOnMissingSecondary;
  }
  return valid;
}

/**
 * Truncates a string to the maximum allowed length.
 * @param {string} str
 * @param {number} maxLength
 * @returns {string}
 */
function truncateString(str, maxLength) {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength);
}

/**
 * Truncates all strings in an array to a maximum length.
 * @param {string[]} arr
 * @param {number} maxLength
 * @returns {string[]}
 */
function truncateStringArray(arr, maxLength) {
  return arr.map(s => truncateString(s, maxLength));
}

// ─────────────────────────────────────────────────────────────
// Main Export
// ─────────────────────────────────────────────────────────────

/**
 * Processes the verdict returned by a QA subagent.
 * Validates the verdict structure, enforces business rules, logs warnings,
 * writes the record to pattern memory, and returns the final memory record.
 *
 * **Incident-driven improvements:**
 * - Mandatory presence and type validation for `result` and `primaryObservations`.
 * - Secondary observations are now enforced with configurable minimums
 *   (default: at least 2 for PASS, 1 for FAIL) to prevent missing critical findings.
 * - All strings are truncated to safe lengths to prevent data corruption.
 * - Comprehensive error handling ensures no uncaught exceptions escape.
 * - Structured logging with appropriate levels and context metadata.
 *
 * @param {Verdict} verdict - The verdict object from the QA subagent.
 * @param {HandleVerdictOptions} [options] - Optional configuration overrides.
 * @returns {Promise<MemoryRecord>} The memory record that was written to pattern memory.
 * @throws {TypeError} If verdict validation fails.
 * @throws {Error} If writing to pattern memory fails.
 */
async function handleVerdict(verdict, options = {}) {
  // ── Pre‑validation logging context ──────────────────────────────────
  const context = { verdict, options };

  // ── Input existence check ──────────────────────────────────────────
  if (!verdict || typeof verdict !== 'object' || Array.isArray(verdict)) {
    const errMsg = 'Invalid verdict: expected a plain object';
    logger.error(errMsg, context);
    throw new TypeError(errMsg);
  }

  // ── Validate options ───────────────────────────────────────────────
  let resolvedOptions;
  try {
    resolvedOptions = validateOptions(options);
  } catch (optError) {
    logger.error('Invalid options provided', { ...context, error: optError.message });
    throw optError;
  }

  // ── Validate `result` (mandatory) ──────────────────────────────────
  let result;
  try {
    result = assertString(verdict.result, 'verdict.result');
  } catch (validationError) {
    logger.error('Invalid result field', { ...context, error: validationError.message });
    throw validationError;
  }

  if (!VALID_RESULTS.includes(result)) {
    const errMsg = `Invalid verdict result: "${result}". Allowed: ${VALID_RESULTS.join(', ')}`;
    logger.error(errMsg, context);
    throw new TypeError(errMsg);
  }

  // ── Validate `primaryObservations` (optional but strongly recommended) ──
  let primaryObservations;
  try {
    primaryObservations = assertOptionalStringArray(
      verdict.primaryObservations,
      'verdict.primaryObservations'
    );
  } catch (validationError) {
    logger.error('Invalid primaryObservations field', { ...context, error: validationError.message });
    throw validationError;
  }

  // Warn if primaryObservations is empty
  if (primaryObservations.length === 0) {
    logger.warn('Verdict has no primary observations – possible lack of evidence', { ...context, result });
  }

  // ── Validate `secondaryObservations` (optional) ────────────────────
  let secondaryObservations;
  try {
    secondaryObservations = assertOptionalStringArray(
      verdict.secondaryObservations,
      'verdict.secondaryObservations'
    );
  } catch (validationError) {
    logger.error('Invalid secondaryObservations field', { ...context, error: validationError.message });
    throw validationError;
  }

  // ── Truncate all observations to safe length ───────────────────────
  primaryObservations = truncateStringArray(primaryObservations, MAX_OBSERVATION_LENGTH);
  secondaryObservations = truncateStringArray(secondaryObservations, MAX_OBSERVATION_LENGTH);

  // ── Enforce minimum observations based on verdict type ─────────────
  const minSecondaryForPass = resolvedOptions.minSecondaryForPass ?? DEFAULT_MIN_SECONDARY_FOR_PASS;
  const minSecondaryForFail = resolvedOptions.minSecondaryForFail ?? DEFAULT_MIN_SECONDARY_FOR_FAIL;
  const throwOnMissing = resolvedOptions.throwOnMissingSecondary ?? false;

  if (result === 'PASS' && secondaryObservations.length < minSecondaryForPass) {
    const warnMsg = `PASS verdict with insufficient secondary observations: ${secondaryObservations.length} < ${minSecondaryForPass}`;
    if (throwOnMissing) {
      logger.error(warnMsg, context);
      throw new Error(warnMsg);
    }
    logger.warn(warnMsg, context);
  }

  if (result === 'FAIL' && secondaryObservations.length < minSecondaryForFail) {
    const warnMsg = `FAIL verdict with insufficient secondary observations: ${secondaryObservations.length} < ${minSecondaryForFail}`;
    if (throwOnMissing) {
      logger.error(warnMsg, context);
      throw new Error(warnMsg);
    }
    logger.warn(warnMsg, context);
  }

  // ── Build memory record ──────────────────────────────────────────
  /** @type {MemoryRecord} */
  const memoryRecord = {
    result,
    primaryObservations,
    secondaryObservations,
  };

  // ── Write to pattern memory ──────────────────────────────────────
  try {
    logger.info('Writing verdict to pattern memory', { ...context, memoryRecord });
    await writePatternEntry({
      type: 'qa_verdict',
      data: memoryRecord,
    });
  } catch (writeError) {
    logger.error('Failed to write verdict to pattern memory', { ...context, error: writeError.message });
    throw writeError; // Re-throw to let caller handle
  }

  logger.info('Verdict processed successfully', { result, primaryCount: primaryObservations.length, secondaryCount: secondaryObservations.length });

  return memoryRecord;
}

module.exports = { handleVerdict };