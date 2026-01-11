"""
Principle constants for referencing axioms and heuristics by name.

Usage:
    from lib.principles import Axiom, Heuristic

    # In code comments or docstrings:
    f"Per {Axiom.FAIL_FAST_CODE}"  # -> "Per fail-fast-code"

    # In hook docstrings (Enforces pattern):
    '''
    Hook description.

    Enforces: {Axiom.CURRENT_STATE_MACHINE} (Current State Machine)
    '''

Priority bands (1-100):
- 1-20: Core principles (inviolable axioms, fundamental heuristics)
- 21-40: Behavioral rules (agent conduct)
- 41-60: Domain-specific (Python, framework, features)
- 61-80: Derived/supporting rules
- 81-100: Experimental/provisional
"""


class Axiom:
    """Axiom name constants. Use instead of numeric references like 'A#7'."""

    # Core (1-12)
    NO_OTHER_TRUTHS = "no-other-truths"
    CATEGORICAL_IMPERATIVE = "categorical-imperative"
    DONT_MAKE_SHIT_UP = "dont-make-shit-up"
    ALWAYS_CITE_SOURCES = "always-cite-sources"
    DO_ONE_THING = "do-one-thing"
    DATA_BOUNDARIES = "data-boundaries"
    PROJECT_INDEPENDENCE = "project-independence"
    FAIL_FAST_CODE = "fail-fast-code"
    FAIL_FAST_AGENTS = "fail-fast-agents"
    SELF_DOCUMENTING = "self-documenting"
    SINGLE_PURPOSE_FILES = "single-purpose-files"
    DRY_MODULAR_EXPLICIT = "dry-modular-explicit"

    # Behavioral (21-31)
    USE_STANDARD_TOOLS = "use-standard-tools"
    ALWAYS_DOGFOODING = "always-dogfooding"
    SKILLS_ARE_READ_ONLY = "skills-are-read-only"
    TRUST_VERSION_CONTROL = "trust-version-control"
    NO_WORKAROUNDS = "no-workarounds"
    VERIFY_FIRST = "verify-first"
    NO_EXCUSES = "no-excuses"
    WRITE_FOR_LONG_TERM = "write-for-long-term"
    MAINTAIN_RELATIONAL_INTEGRITY = "maintain-relational-integrity"
    NOTHING_IS_SOMEONE_ELSES_RESPONSIBILITY = "nothing-is-someone-elses-responsibility"
    ACCEPTANCE_CRITERIA_OWN_SUCCESS = "acceptance-criteria-own-success"

    # Domain-specific (41-47)
    PLAN_FIRST_DEVELOPMENT = "plan-first-development"
    RESEARCH_DATA_IMMUTABLE = "research-data-immutable"
    JUST_IN_TIME_CONTEXT = "just-in-time-context"
    MINIMAL_INSTRUCTIONS = "minimal-instructions"
    FEEDBACK_LOOPS_FOR_UNCERTAINTY = "feedback-loops-for-uncertainty"
    CURRENT_STATE_MACHINE = "current-state-machine"
    ONE_SPEC_PER_FEATURE = "one-spec-per-feature"


class Heuristic:
    """Heuristic name constants. Use instead of numeric references like 'H#3'."""

    # Core (10-20)
    SKILL_INVOCATION_FRAMING = "skill-invocation-framing"
    SKILL_FIRST_ACTION = "skill-first-action"
    VERIFICATION_BEFORE_ASSERTION = "verification-before-assertion"
    EXPLICIT_INSTRUCTIONS_OVERRIDE = "explicit-instructions-override"
    ERROR_MESSAGES_PRIMARY_EVIDENCE = "error-messages-primary-evidence"
    CONTEXT_UNCERTAINTY_FAVORS_SKILLS = "context-uncertainty-favors-skills"
    LINK_DONT_REPEAT = "link-dont-repeat"
    AVOID_NAMESPACE_COLLISIONS = "avoid-namespace-collisions"
    SKILLS_NO_DYNAMIC_CONTENT = "skills-no-dynamic-content"
    LIGHT_INSTRUCTIONS_VIA_REFERENCE = "light-instructions-via-reference"

    # Behavioral (25-37)
    NO_PROMISES_WITHOUT_INSTRUCTIONS = "no-promises-without-instructions"
    SEMANTIC_SEARCH_OVER_KEYWORD = "semantic-search-over-keyword"
    CONTEXT_OVER_ALGORITHMS = "context-over-algorithms"
    EDIT_SOURCE_RUN_SETUP = "edit-source-run-setup"
    MANDATORY_SECOND_OPINION = "mandatory-second-opinion"
    STREAMLIT_HOT_RELOADS = "streamlit-hot-reloads"
    USE_ASKUSERQUESTION = "use-askuserquestion"
    CHECK_SKILL_CONVENTIONS = "check-skill-conventions"
    DISTINGUISH_SCRIPT_VS_LLM = "distinguish-script-vs-llm"
    QUESTIONS_REQUIRE_ANSWERS = "questions-require-answers"
    CRITICAL_THINKING_OVER_COMPLIANCE = "critical-thinking-over-compliance"

    # Domain-specific (41-63)
    CORE_FIRST_EXPANSION = "core-first-expansion"
    INDICES_BEFORE_EXPLORATION = "indices-before-exploration"
    SYNTHESIZE_AFTER_RESOLUTION = "synthesize-after-resolution"
    SHIP_SCRIPTS_DONT_INLINE = "ship-scripts-dont-inline"
    USER_CENTRIC_ACCEPTANCE = "user-centric-acceptance"
    SEMANTIC_VS_EPISODIC_STORAGE = "semantic-vs-episodic-storage"
    DEBUG_DONT_REDESIGN = "debug-dont-redesign"
    MANDATORY_ACCEPTANCE_TESTING = "mandatory-acceptance-testing"
    TODOWRITE_VS_PERSISTENT_TASKS = "todowrite-vs-persistent-tasks"
    CHECK_DOCS_BEFORE_GUESSING = "check-docs-before-guessing"
    DESIGN_FIRST_NOT_CONSTRAINT_FIRST = "design-first-not-constraint-first"
    NO_LLM_CALLS_IN_HOOKS = "no-llm-calls-in-hooks"
    DELETE_DONT_DEPRECATE = "delete-dont-deprecate"
    REAL_DATA_FIXTURES = "real-data-fixtures"
    SEMANTIC_LINK_DENSITY = "semantic-link-density"
    SPEC_FIRST_FILE_MODIFICATION = "spec-first-file-modification"
    FILE_CATEGORY_CLASSIFICATION = "file-category-classification"
    LLM_SEMANTIC_EVALUATION = "llm-semantic-evaluation"
    FULL_EVIDENCE_FOR_VALIDATION = "full-evidence-for-validation"
    REAL_FIXTURES_OVER_CONTRIVED = "real-fixtures-over-contrived"
    EXECUTION_OVER_INSPECTION = "execution-over-inspection"
    SIDE_EFFECTS_OVER_RESPONSE = "side-effects-over-response"
    TEST_FAILURE_REQUIRES_USER_DECISION = "test-failure-requires-user-decision"
    NO_HORIZONTAL_DIVIDERS = "no-horizontal-dividers"
