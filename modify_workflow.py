import sys


def main():
    try:
        with open(".github/workflows/build-extension.yml") as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: File not found")
        sys.exit(1)

    # Define the old block to replace
    # Note: Indentation must match exactly
    old_block = """  # Step 1: Download PKB binaries from nicsuzor/mem releases
  build-pkb:
    uses: ./.github/workflows/build-pkb-binary.yml
    secrets: inherit"""

    # Define the new block
    # Note: Double check indentation
    new_block = """  # Step 1: Download PKB binaries from nicsuzor/mem releases
  download-pkb-binaries:
    strategy:
      fail-fast: false
      matrix:
        include:
          - artifact_label: x86_64-linux
            output_name: pkb-linux-x86_64
          - artifact_label: aarch64-darwin
            output_name: pkb-macos-aarch64

    runs-on: ubuntu-latest
    steps:
      - name: Determine version
        id: version
        env:
          GH_TOKEN: ${{ secrets.AOPS_DIST_PAT }}
        run: |
          TAG=$(gh api repos/nicsuzor/mem/releases/latest --jq '.tag_name')
          echo "tag=$TAG" >> $GITHUB_OUTPUT
          echo "Using latest release: $TAG"

      - name: Download release archive
        env:
          GH_TOKEN: ${{ secrets.AOPS_DIST_PAT }}
        run: |
          TAG="${{ steps.version.outputs.tag }}"
          ARCHIVE="mem-${TAG}-${{ matrix.artifact_label }}.tar.gz"
          echo "Downloading $ARCHIVE from nicsuzor/mem release $TAG"

          gh release download "$TAG" \\
            --repo nicsuzor/mem \\
            --pattern "$ARCHIVE"

          # Extract binaries (pkb and aops)
          mkdir -p output
          tar xzf "$ARCHIVE" -C output
          chmod +x output/pkb output/aops
          echo "Extracted binaries:"
          ls -la output/

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.output_name }}
          path: |
            output/pkb
            output/aops
          if-no-files-found: error"""

    if old_block not in content:
        print("Error: Could not find the block to replace. Content preview around line 15:")
        lines = content.splitlines()
        for i in range(10, 25):
            if i < len(lines):
                print(f"{i}: {lines[i]}")
        sys.exit(1)

    new_content = content.replace(old_block, new_block)

    # Also replace dependency
    if "needs: build-pkb" not in new_content:
        print("Warning: 'needs: build-pkb' not found to replace.")
    new_content = new_content.replace("needs: build-pkb", "needs: download-pkb-binaries")

    with open(".github/workflows/build-extension.yml", "w") as f:
        f.write(new_content)

    print("Successfully modified .github/workflows/build-extension.yml")


if __name__ == "__main__":
    main()
