# Project Catalog

## Buttermilk

Foundational Python framework for computational research in HASS ("MLOps for HASS scholars"). Provides agents, flows, and reproducible research pipelines.

- **Repository**: `nicsuzor/buttermilk`
- **Path**: `projects/buttermilk/`
- **Priority**: P1 - Critical infrastructure
- **Dependents**: automod, dbr, zotmcp, osbchatmcp

**Architecture**:
- Hydra config, Pydantic contracts, async I/O
- Data: GCS/BigQuery, tracked in Weights & Biases

## academicOps

Public framework for AI-assisted academic work. Modular instruction library, workflows, and tools for other researchers.

- **Repository**: `nicsuzor/academicOps`
- **Path**: `aOps/`
- **Status**: Being refactored from personal toolset to reusable platform

## Automod Demo (automod.cc)

High-impact public demo and accountability tool. Terminal-style web interface for AI-powered content moderation research.

- **Repository**: `nicsuzor/automod.cc`
- **Path**: `projects/automod.cc/`
- **Stack**: SvelteKit frontend + Buttermilk backend
- **Data**: BigQuery evaluation data, Looker Studio analysis
- **Focus**: "Proving and selling" not further development
- **Method**: JUDGE→SYNTH evaluation pattern with stochastic testing

## Digital Bills of Rights (DBR)

Thematic extraction from 30 Digital Bills of Rights using Buttermilk.

- **Repository**: `nicsuzor/dbr`
- **Path**: `projects/dbr/`

## ZotMCP (Zotero RAG Agent)

MCP server providing semantic search over Zotero research library.

- **Repository**: `nicsuzor/zotmcp`
- **Path**: `projects/zotmcp/`
- **Priority**: Medium
- **Features**: 7 tools for search, item retrieval, similarity finding
- **Architecture**: Buttermilk vectorization + ChromaDB + MCP

## OSB ChatMCP

MCP server for Meta Oversight Board case decisions with AI-generated IRAC summaries.

- **Repository**: `nicsuzor/osbchatmcp`
- **Path**: `projects/osbchatmcp/`
- **Features**: Semantic search and case retrieval
- **Architecture**: Same as ZotMCP (consistent pattern)

## Other Projects

- **mediamarkets**: SVOD platform availability research
- **wikijuris**: Open textbooks project
