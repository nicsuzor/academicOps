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
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 380px;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(0, 240, 255, 0.2);
        border-bottom: 3px solid var(--neon-cyan);
        border-radius: var(--radius-md);
        padding: 20px;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        z-index: 90;
    }

    .capture-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        color: var(--neon-cyan);
        font-size: 14px;
        font-family: var(--font-display);
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.3);
    }

    textarea {
        width: 100%;
        height: 100px;
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: var(--radius-sm);
        padding: 16px;
        color: var(--color-text);
        font-family: inherit;
        font-size: 14px;
        resize: vertical;
        box-sizing: border-box;
        margin-bottom: 16px;
        transition: all var(--transition-fast);
        outline: none;
    }

    textarea:focus {
        border-color: var(--neon-cyan);
        box-shadow:
            inset 0 2px 4px rgba(0, 0, 0, 0.3),
            0 0 10px rgba(0, 240, 255, 0.2);
    }

    textarea::placeholder {
        color: rgba(255, 255, 255, 0.3);
    }

    .quick-capture-btn {
        width: 100%;
        background: transparent;
        color: var(--neon-cyan);
        border: 1px solid var(--neon-cyan);
        border-radius: var(--radius-sm);
        padding: 12px;
        font-weight: 700;
        font-family: var(--font-display);
        cursor: pointer;
        font-size: 13px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        transition: all var(--transition-fast);
    }

    .quick-capture-btn:hover:not(:disabled) {
        background: var(--neon-cyan);
        color: var(--color-void);
        box-shadow: 0 0 15px var(--neon-cyan);
    }

    .quick-capture-btn:active:not(:disabled) {
        transform: scale(0.98);
    }

    button:disabled {
        opacity: 0.3;
        cursor: not-allowed;
        border-color: var(--text-muted);
        color: var(--text-muted);
    }
</style>
