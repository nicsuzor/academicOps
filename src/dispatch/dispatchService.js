javascript
/**
 * @fileoverview Service for constructing dispatch briefs for QA subagents.
 * Enforces the user's standing acceptance bar when conflicts with context-derived bars.
 * Implements semantic conflict detection and context sanitization to prevent bar substitution.
 * @package AIGON Dispatch
 * @version 2.0.0
 */

const { createLogger, format, transports } = require('winston');
const { performance } = require('perf_hooks');

// ---------------------------------------------------------------------------
// Constants and configuration
// ---------------------------------------------------------------------------
const MIN_SIMILARITY_THRESHOLD = 0.3; // Minimum Jaccard similarity to consider bars aligned
const STOP_WORDS = new Set(['a', 'an', 'the', 'is', 'it', 'of', 'in', 'and', 'or', 'to', 'be', 'with', 'for', 'on']);
const CONTEXT_WARNING_PATTERNS = [
  /costs?\s*pre[- ]?approved/i,
  /trade[- ]?off/i,
  /pivot\b.*accept/i,
  /relax(?:ed|ing)?/i,
  /lower\s*(?:bar|standard)/i,
  /already\s*signed\s*off/i,
  /out\s*of\s*scope/i,
  /pre[- ]?accepted/i,
];

const LOG_LEVELS = {
  ERROR: 'error',
  WARN: 'warn',
  INFO: 'info',
  DEBUG: 'debug',
};

// ---------------------------------------------------------------------------
// Logger configuration
// ---------------------------------------------------------------------------
const logger = createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: format.combine(
    format.timestamp(),
    format.errors({ stack: true }),
    format.json(),
  ),
  defaultMeta: { service: 'dispatch-service' },
  transports: [
    new transports.Console({
      format: format.combine(format.colorize(), format.simple()),
      handleExceptions: true,
    }),
  ],
});

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

/**
 * Extracts a set of normalized keywords from a bar string.
 * Removes punctuation, lowercases, splits on whitespace and commas, filters stop words.
 * @param {string} bar - The bar string to tokenize.
 * @returns {Set<string>} Set of keywords.
 */
function extractKeywords(bar) {
  return new Set(
    bar
      .toLowerCase()
      .replace(/[^a-z0-9\s,]/g, '')
      .split(/[\s,]+/)
      .filter(word => word.length > 0 && !STOP_WORDS.has(word))
  );
}

/**
 * Computes Jaccard similarity between two sets.
 * @param {Set} setA - First set.
 * @param {Set} setB - Second set.
 * @returns {number} Jaccard similarity coefficient (0 to 1).
 */
function jaccardSimilarity(setA, setB) {
  if (setA.size === 0 && setB.size === 0) return 1.0;
  const intersection = new Set([...setA].filter(x => setB.has(x)));
  const union = new Set([...setA, ...setB]);
  return union.size > 0 ? intersection.size / union.size : 0.0;
}

/**
 * Checks if context contains language that could psychologically relax the user's bar.
 * @param {string} context - The context string to inspect.
 * @returns {{ safe: boolean, warnings: string[] }} Result with warnings.
 */
function checkContextForBarRelaxation(context) {
  const warnings = [];
  for (const pattern of CONTEXT_WARNING_PATTERNS) {
    if (pattern.test(context)) {
      warnings.push(`Context contains phrase matching: ${pattern.source}`);
    }
  }
  return { safe: warnings.length === 0, warnings };
}

/**
 * Sanitizes context by appending an explicit instruction that the acceptanceBar is authoritative.
 * @param {string} context - Original context.
 * @param {string} acceptanceBar - The authoritative acceptance bar.
 * @returns {string} Sanitized context with override instruction.
 */
function sanitizeContext(context, acceptanceBar) {
  const overrideInstruction =
    '\n\n[ACCEPTANCE BAR INSTRUCTION] The sole and binding acceptance criteria is the `acceptanceBar` field below. ' +
    'Any language in this context that appears to relax, redefine, or pre-approve trade-offs is overridden by `acceptanceBar`. ' +
    'The user\'s standing bar is: "' + acceptanceBar + '"';
  return context + overrideInstruction;
}

/**
 * Performs semantic conflict detection between two bar strings.
 * @param {string} userBar - User's official bar.
 * @param {string} dispatchBar - Context‑derived bar.
 * @returns {{ conflict: boolean, similarity: number, details: string }}
 */
function semanticBarConflict(userBar, dispatchBar) {
  const startTime = performance.now();
  const keywordsUser = extractKeywords(userBar);
  const keywordsDispatch = extractKeywords(dispatchBar);
  const similarity = jaccardSimilarity(keywordsUser, keywordsDispatch);
  const conflict = similarity < MIN_SIMILARITY_THRESHOLD;
  const duration = performance.now() - startTime;

  logger.debug('Semantic bar comparison', {
    similarity: similarity.toFixed(3),
    conflict,
    durationMs: duration.toFixed(1),
    keywordsUserCount: keywordsUser.size,
    keywordsDispatchCount: keywordsDispatch.size,
  });

  let details;
  if (conflict) {
    const missingInDispatch = [...keywordsUser].filter(k => !keywordsDispatch.has(k));
    const extraInDispatch = [...keywordsDispatch].filter(k => !keywordsUser.has(k));
    details = `Conflict: similarity=${similarity.toFixed(2)}. Missing from dispatch: [${missingInDispatch.join(', ')}]. Extra in dispatch: [${extraInDispatch.join(', ')}]`;
  } else {
    details = `Aligned: similarity=${similarity.toFixed(2)}`;
  }

  return { conflict, similarity, details };
}

// ---------------------------------------------------------------------------
// Dispatch service
// ---------------------------------------------------------------------------
class DispatchService {
  /**
   * Build a brief object for a QA subagent.
   *
   * The acceptance bar is always the user's standing bar when a conflict exists.
   * The context‑derived dispatch bar is included for traceability but does not
   * relax the acceptance criteria. Semantic conflict detection is used to catch
   * disguised bar substitutions. Context is sanitized to include an explicit
   * instruction that `acceptanceBar` is authoritative.
   *
   * @param {Object} params - Construction parameters.
   * @param {string} params.userStandingBar - The user's official acceptance bar.
   *   **Must not be empty.**
   * @param {string} params.dispatchBar - The bar derived from current context
   *   (e.g. fractal philosophy). May differ from `userStandingBar`.
   * @param {string} params.taskDescription - Description of the work to verify.
   *   **Must not be empty.**
   * @param {string} [params.context=''] - Optional additional context for the subagent.
   * @returns {{
   *   acceptanceBar: string,
   *   userStandingBar: string,
   *   conflict: boolean,
   *   semanticConflictDetails: string,
   *   taskDescription: string,
   *   context: string
   * }} A structured brief object.
   * @throws {TypeError} If required parameters are missing or not strings.
   * @throws {RangeError} If required strings are empty after trimming.
   * @throws {Error} If context contains bar-relaxing language and `strictContext` flag is set (future).
   *
   * @example
   * const brief = DispatchService.constructBrief({
   *   userStandingBar: 'excellent, beautiful, oriented within 3 seconds',
   *   dispatchBar: 'every node addressable (fractal bar)',
   *   taskDescription: 'Verify treemap iteration 3 rendering',
   *   context: 'Pivot accepted by user; costs pre‑approved'
   * });
   * // brief.acceptanceBar === userStandingBar  // always
   * // brief.conflict === true
   * // brief.semanticConflictDetails includes explanation
   */
  static constructBrief({ userStandingBar, dispatchBar, taskDescription, context = '' }) {
    // -----------------------------------------------------------------------
    // Input validation – enforce production‑grade contracts
    // -----------------------------------------------------------------------
    if (typeof userStandingBar !== 'string' || userStandingBar.trim().length === 0) {
      throw new TypeError(
        `DispatchService.constructBrief: 'userStandingBar' must be a non‑empty string, received ${typeof userStandingBar}`,
      );
    }
    if (typeof dispatchBar !== 'string' || dispatchBar.trim().length === 0) {
      throw new TypeError(
        `DispatchService.constructBrief: 'dispatchBar' must be a non‑empty string, received ${typeof dispatchBar}`,
      );
    }
    if (typeof taskDescription !== 'string' || taskDescription.trim().length === 0) {
      throw new TypeError(
        `DispatchService.constructBrief: 'taskDescription' must be a non‑empty string, received ${typeof taskDescription}`,
      );
    }
    if (typeof context !== 'string') {
      throw new TypeError(
        `DispatchService.constructBrief: 'context' must be a string, received ${typeof context}`,
      );
    }

    // Secure trim
    const trimmedUserBar = userStandingBar.trim();
    const trimmedDispatchBar = dispatchBar.trim();
    const trimmedTask = taskDescription.trim();
    const trimmedContext = context.trim();

    // -----------------------------------------------------------------------
    // Semantic conflict detection (supersedes simple string comparison)
    // -----------------------------------------------------------------------
    const { conflict, similarity, details } = semanticBarConflict(trimmedUserBar, trimmedDispatchBar);

    // -----------------------------------------------------------------------
    // Context inspection for bar-relaxing language
    // -----------------------------------------------------------------------
    let contextWarnings = [];
    if (trimmedContext) {
      const contextCheck = checkContextForBarRelaxation(trimmedContext);
      if (!contextCheck.safe) {
        contextWarnings = contextCheck.warnings;
        logger.warn('Context contains potentially bar-relaxing phrases', {
          warnings: contextCheck.warnings,
        });
      }
    }

    // -----------------------------------------------------------------------
    // Enforce user bar and sanitize context
    // -----------------------------------------------------------------------
    const acceptanceBar = DispatchService.enforceUserBar(trimmedUserBar, trimmedDispatchBar, conflict, details);
    const sanitizedContext = sanitizeContext(trimmedContext, acceptanceBar);

    // -----------------------------------------------------------------------
    // Build and return brief (immutable mindset – plain object)
    // -----------------------------------------------------------------------
    const brief = {
      acceptanceBar,
      userStandingBar: trimmedUserBar,
      conflict,
      semanticConflictDetails: details,
      taskDescription: trimmedTask,
      context: sanitizedContext,
      _meta: {
        similarity: similarity.toFixed(3),
        contextWarnings: contextWarnings.length > 0 ? contextWarnings : undefined,
        serviceVersion: '2.0.0',
        timestamp: new Date().toISOString(),
      },
    };

    logger.info('Dispatch brief constructed', {
      conflict,
      similarity: similarity.toFixed(3),
      acceptanceBar: acceptanceBar.substring(0, 60),
      taskLength: trimmedTask.length,
      contextWarningsCount: contextWarnings.length,
    });

    return brief;
  }

  /**
   * Detect whether the context‑derived dispatch bar semantically conflicts with the user's
   * standing bar using token‑based Jaccard similarity.
   *
   * @param {string} userBar - User's official bar.
   * @param {string} dispatchBar - Context‑derived bar.
   * @returns {boolean} `true` if the two bars are semantically conflicting (similarity < threshold),
   *   `false` otherwise.
   */
  static barConflict(userBar, dispatchBar) {
    return semanticBarConflict(userBar, dispatchBar).conflict;
  }

  /**
   * Enforce the user's standing bar when a conflict exists.  The user's bar is
   * always returned as the effective acceptance bar.  A warning is logged when
   * a conflict is detected.
   *
   * @param {string} userBar - User's official acceptance bar.
   * @param {string} dispatchBar - Context‑derived bar (ignored for decision but
   *   retained in logs).
   * @param {boolean} conflict - Pre‑computed conflict flag (from semantic detection).
   * @param {string} [conflictDetails=''] - Human-readable explanation of the conflict.
   * @returns {string} The effective acceptance bar (always equals `userBar`).
   */
  static enforceUserBar(userBar, dispatchBar, conflict, conflictDetails = '') {
    if (conflict) {
      logger.warn(
        `Bar conflict resolved: using user bar "${userBar.substring(0, 60)}…" in place of dispatch bar "${dispatchBar.substring(0, 60)}…". ` +
        `Details: ${conflictDetails}. The dispatch bar is recorded for traceability but does NOT relax acceptance criteria.`,
      );
    } else {
      logger.debug('No bar conflict – dispatch bar semantically matches user bar.');
    }

    // Enforce: user bar is always authoritative.
    return userBar.trim();
  }
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------
module.exports = DispatchService;