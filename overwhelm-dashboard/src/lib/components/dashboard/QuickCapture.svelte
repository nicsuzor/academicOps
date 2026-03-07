<script lang="ts">
    let captureText = "";
    let isSubmitting = false;

    async function handleCapture() {
        if (!captureText.trim()) return;
        isSubmitting = true;

        // This is a stub for what would be an actual mutation (either hitting the local API or a server action)
        // Streamlit uses requests.post to GitHub directly
        try {
            await new Promise((r) => setTimeout(r, 600)); // Simulate network request
            captureText = ""; // Clear input on success
            alert("Quick Note Captured!"); // Placeholder alert
        } finally {
            isSubmitting = false;
        }
    }
</script>

<div class="capture-panel">
    <h3 class="capture-header">
        <span class="icon">⚡</span> QUICK CAPTURE
    </h3>

    <form on:submit|preventDefault={handleCapture}>
        <textarea
            bind:value={captureText}
            placeholder="Type a thought, task, or realization... (Alt+C)"
            disabled={isSubmitting}
        ></textarea>

        <div class="actions">
            <button
                class="quick-capture-btn"
                type="submit"
                disabled={isSubmitting || !captureText.trim()}
            >
                {#if isSubmitting}
                    Capturing...
                {:else}
                    Capture Note
                {/if}
            </button>
        </div>
    </form>
</div>

<style>
    .capture-panel {
        background: transparent;
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 20px;
        box-shadow: var(--shadow-md);
        background: var(--bg-panel);
        backdrop-filter: blur(12px);
    }

    .capture-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        color: var(--accent-warning);
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    textarea {
        width: 100%;
        height: 100px;
        background: var(--bg-input);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 16px;
        color: var(--text-primary);
        font-family: inherit;
        font-size: 14px;
        resize: vertical;
        box-sizing: border-box;
        margin-bottom: 16px;
        transition: all var(--transition-fast);
        outline: none;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    textarea:focus {
        border-color: var(--accent-primary);
        background: var(--bg-input-focus);
        box-shadow:
            inset 0 2px 4px rgba(0, 0, 0, 0.1),
            0 0 0 3px rgba(129, 140, 248, 0.2);
    }

    textarea::placeholder {
        color: var(--text-muted);
    }

    .quick-capture-btn {
        width: 100%;
        background: linear-gradient(
            135deg,
            var(--accent-primary),
            var(--accent-secondary)
        );
        color: #ffffff;
        border: none;
        border-radius: var(--radius-sm);
        padding: 12px;
        font-weight: 700;
        cursor: pointer;
        font-size: 14px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        transition: all var(--transition-fast);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }

    .quick-capture-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.5);
    }

    .quick-capture-btn:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(99, 102, 241, 0.4);
    }
    button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
