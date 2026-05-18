javascript
/**
 * Mongoose schema for verdict documents in the AIGON QA pipeline.
 *
 * This schema enforces a strict structure to prevent the "bar substitution" and
 * "PASS as termination" failures observed in incident IR-2025-03-17.
 *
 * Each verdict includes:
 *  - A `result`: PASS, FAIL, or INCONCLUSIVE.
 *  - `primaryObservations`: all user-visible shortfalls, even when the result is
 *    PASS. May be empty if no shortfalls exist.
 *  - `secondaryObservations`: subagent notes that did not rise to FAIL level.
 *    Always required (use empty array if none).
 *  - `userStandingBar`: the user's stated acceptance bar.
 *  - `dispatchBar`: the acceptance bar from the dispatch brief (stored for
 *    forensic tracing).
 *  - `conflictFlag`: automatically set when `dispatchBar` differs from
 *    `userStandingBar`.
 *
 * @module models/Verdict
 */

const mongoose = require('mongoose');
const { createLogger } = require('../lib/logger');

const logger = createLogger('VerdictSchema');

// ---------- Constants ----------

/**
 * Allowed verdict results.
 * @readonly
 * @enum {string}
 */
const VERDICT_RESULTS = Object.freeze({
  PASS: 'PASS',
  FAIL: 'FAIL',
  INCONCLUSIVE: 'INCONCLUSIVE',
});

// ---------- Schema Definition ----------

/**
 * @typedef {Object} VerdictDocument
 * @property {string} result - One of PASS, FAIL, INCONCLUSIVE.
 * @property {string[]} primaryObservations - Primary observations (user-facing
 *   shortfalls). May be empty but each element must be a non-empty string.
 * @property {string[]} secondaryObservations - Secondary observations (may be
 *   empty). Each element must be a string (empty strings allowed for
 *   flexibility, but should be avoided in practice).
 * @property {string} userStandingBar - User's stated acceptance bar.
 * @property {string} [dispatchBar] - Acceptance bar from the dispatch brief
 *   (stored for forensic tracing). Optional.
 * @property {boolean} conflictFlag - True when dispatchBar differs from
 *   userStandingBar (auto‑set in pre‑save).
 * @property {Date} createdAt - Auto‑managed.
 * @property {Date} updatedAt - Auto‑managed.
 */

const verdictSchema = new mongoose.Schema(
  {
    /**
     * Verdict result.
     * Must be one of PASS, FAIL, INCONCLUSIVE.
     * @type {string}
     * @required
     * @example "PASS"
     */
    result: {
      type: String,
      required: [true, 'result is required'],
      enum: {
        values: Object.values(VERDICT_RESULTS),
        message: '{VALUE} is not a valid verdict result. Allowed: PASS, FAIL, INCONCLUSIVE.',
      },
      // No redundant regex – enum is sufficient and more maintainable.
    },

    /**
     * Primary observations capturing all user‑visible shortfalls.
     * Even when result is PASS, any shortfalls found must be listed here.
     * May be empty if no shortfalls exist.
     * Each element, if present, must be a non‑empty string.
     * @type {string[]}
     * @required
     * @default []
     * @example ["Text rendering letter‑stacking", "No animated zoom transition"]
     */
    primaryObservations: {
      type: [String],
      required: [true, 'primaryObservations is required'],
      default: [],
      validate: {
        /**
         * Custom validator: allows empty arrays but rejects arrays containing
         * non‑string or empty‑string elements.
         * @param {*} arr
         * @returns {boolean}
         */
        validator(arr) {
          return (
            Array.isArray(arr) &&
            arr.every((s) => typeof s === 'string' && s.trim().length > 0)
          );
        },
        message:
          'primaryObservations must be an array of non‑empty strings (empty array is allowed)',
      },
    },

    /**
     * Secondary observations that did not rise to the level of FAIL
     * but should be recorded. Always required to prevent data loss.
     * Use empty array if none.
     * @type {string[]}
     * @required
     * @default []
     * @example ["Minor layout shift on mobile viewport"]
     */
    secondaryObservations: {
      type: [String],
      required: [true, 'secondaryObservations is required'],
      default: [],
      validate: {
        validator(arr) {
          return Array.isArray(arr) && arr.every((s) => typeof s === 'string');
        },
        message: 'secondaryObservations must be an array of strings',
      },
    },

    /**
     * The user's standing acceptance bar as defined in project requirements.
     * Used for forensic comparison against the dispatch brief.
     * @type {string}
     * @required
     * @maxLength 500
     * @example "excellent, beautiful, oriented within 3 seconds"
     */
    userStandingBar: {
      type: String,
      required: [true, 'userStandingBar is required'],
      trim: true,
      maxlength: [500, 'userStandingBar cannot exceed 500 characters'],
    },

    /**
     * The acceptance bar from the dispatch brief.
     * Stored permanently to enable forensic tracing of bar mismatches.
     * Optional – if omitted, conflictFlag remains false.
     * @type {string}
     * @optional
     * @example "fractal‑philosophy bar (every‑node‑addressable)"
     */
    dispatchBar: {
      type: String,
      default: null,
      trim: true,
      maxlength: [500, 'dispatchBar cannot exceed 500 characters'],
    },

    /**
     * Conflict flag indicating whether the dispatch acceptance bar differed
     * from the user's standing acceptance bar.
     * Auto‑set during pre‑save hook; do not set directly.
     * @type {boolean}
     * @default false
     */
    conflictFlag: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: true,
    toJSON: {
      getters: true,
      aliases: true,
      versionKey: false,
      transform(_doc, ret) {
        delete ret.__v;
        return ret;
      },
    },
    toObject: {
      getters: true,
      versionKey: false,
    },
  }
);

// ---------- Indexes ----------

verdictSchema.index({ result: 1, createdAt: -1 });
verdictSchema.index({ conflictFlag: 1 });
verdictSchema.index({ dispatchBar: 1 }); // support forensic queries

// ---------- Pre‑save Hook ----------

verdictSchema.pre('save', function (next) {
  try {
    // Compute conflictFlag from stored dispatchBar vs userStandingBar
    if (this.dispatchBar && this.userStandingBar) {
      this.conflictFlag = this.dispatchBar !== this.userStandingBar;
    } else {
      this.conflictFlag = false;
    }

    // Log conflict detection
    if (this.conflictFlag) {
      logger.warn('Verdict conflict detected', {
        id: this._id || '(new)',
        userBar: this.userStandingBar,
        dispatchBar: this.dispatchBar,
      });
    }

    logger.info('Saving verdict', {
      result: this.result,
      primaryCount: this.primaryObservations ? this.primaryObservations.length : 0,
      secondaryCount: this.secondaryObservations ? this.secondaryObservations.length : 0,
      conflict: this.conflictFlag,
    });

    next();
  } catch (err) {
    // Catch unexpected errors to prevent unhandled rejections
    logger.error('Pre‑save hook error', { error: err.message, stack: err.stack });
    next(err);
  }
});

// ---------- Post‑save Hook ----------

verdictSchema.post('save', function (doc) {
  try {
    logger.info('Verdict saved successfully', {
      id: doc._id,
      result: doc.result,
      conflictFlag: doc.conflictFlag,
    });
  } catch (err) {
    // Post‑save errors must not crash the save operation – log only
    logger.error('Post‑save hook error', { error: err.message, stack: err.stack });
  }
});

// ---------- Static Methods ----------

/**
 * Creates and saves a new Verdict document.
 * Use this factory method instead of `new Verdict().save()` to ensure all
 * required fields are validated and the dispatchBar is properly recorded.
 *
 * @static
 * @param {Object} data - Verdict data.
 * @param {string} data.result - Verdict result (PASS, FAIL, INCONCLUSIVE).
 * @param {string[]} data.primaryObservations - Primary observations.
 * @param {string[]} [data.secondaryObservations=[]] - Secondary observations.
 * @param {string} data.userStandingBar - User's acceptance bar.
 * @param {string} [data.dispatchBar] - Dispatch brief acceptance bar (optional).
 * @param {Object} [options] - Additional options (reserved for future use).
 * @returns {Promise<import('mongoose').Document>} The saved verdict document.
 * @throws {Error} If required fields are missing or validation fails.
 */
verdictSchema.statics.createVerdict = async function createVerdict(data, options = {}) {
  const { result, primaryObservations, secondaryObservations = [], userStandingBar, dispatchBar } = data;

  // Explicit input validation before constructing the document
  if (!result || !primaryObservations || !userStandingBar) {
    throw new Error('Missing required fields: result, primaryObservations, userStandingBar');
  }

  if (!Object.values(VERDICT_RESULTS).includes(result)) {
    throw new Error(`Invalid result: "${result}". Must be one of ${Object.values(VERDICT_RESULTS).join(', ')}`);
  }

  if (!Array.isArray(primaryObservations)) {
    throw new Error('primaryObservations must be an array');
  }

  if (!Array.isArray(secondaryObservations)) {
    throw new Error('secondaryObservations must be an array');
  }

  const verdict = new this({
    result,
    primaryObservations,
    secondaryObservations,
    userStandingBar,
    dispatchBar: dispatchBar || null,
    // conflictFlag is auto-set in pre-save, so we omit it here
  });

  try {
    return await verdict.save();
  } catch (err) {
    logger.error('Failed to create verdict', {
      error: err.message,
      data: { result, primaryObservations, secondaryObservations, userStandingBar },
    });
    throw err; // re-throw for caller to handle
  }
};

// ---------- Model Export ----------

/** Verdict model with enhanced validation and forensic tracking. */
const Verdict = mongoose.model('Verdict', verdictSchema);

module.exports = Verdict;
module.exports.VERDICT_RESULTS = VERDICT_RESULTS;