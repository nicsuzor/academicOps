use anyhow::Result;
use chrono::Utc;
use clap::Parser;
use gray_matter::engine::YAML;
use gray_matter::Matter;
use ignore::WalkBuilder;
use md5;
use rayon::prelude::*;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Root directory to scan
    #[arg(default_value = ".")]
    root: String,

    /// Output file path (extension auto-added based on format)
    #[arg(short, long, default_value = "graph")]
    output: String,

    /// Output format: json, graphml, dot, mcp-index, all (default: all)
    #[arg(short, long, default_value = "all")]
    format: String,

    /// Filter by frontmatter type (e.g., task,project,goal)
    #[arg(short = 't', long, value_delimiter = ',')]
    filter_type: Option<Vec<String>>,

    /// Tasks directory for MCP index (relative path within root, e.g., "tasks")
    #[arg(long)]
    tasks_dir: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Node {
    id: String,
    path: String,
    label: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    tags: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    node_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    status: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    priority: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    parent: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    depends_on: Option<Vec<String>>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Edge {
    source: String,
    target: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct Graph {
    nodes: Vec<Node>,
    edges: Vec<Edge>,
}

// MCP Task Index structures (matches task_index.py schema)
#[derive(Serialize, Deserialize, Debug, Clone)]
struct McpIndexEntry {
    id: String,
    title: String,
    #[serde(rename = "type")]
    task_type: String,
    status: String,
    priority: i32,
    order: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    parent: Option<String>,
    children: Vec<String>,      // Computed: inverse of parent
    depends_on: Vec<String>,
    blocks: Vec<String>,        // Computed: inverse of depends_on
    depth: i32,
    leaf: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    project: Option<String>,
    path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    due: Option<String>,
    #[serde(default)]
    tags: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug)]
struct McpIndex {
    version: i32,
    generated: String,
    tasks: HashMap<String, McpIndexEntry>,
    by_project: HashMap<String, Vec<String>>,
    roots: Vec<String>,
    ready: Vec<String>,
    blocked: Vec<String>,
}

#[derive(Clone)]
struct FileData {
    path: PathBuf,
    content: String,
    id: String,
    label: String,
    tags: Vec<String>,
    raw_links: Vec<String>,
    permalinks: Vec<String>, // For ID resolution (filename, permalink key, etc)
    // Frontmatter fields for task visualization
    node_type: Option<String>,
    status: Option<String>,
    priority: Option<i32>,
    order: i32,
    parent: Option<String>,
    depends_on: Vec<String>,
    children: Vec<String>,
    blocks: Vec<String>,
    project: Option<String>,
    due: Option<String>,
    depth: i32,
    leaf: bool,
    // Task ID (from frontmatter id field, distinct from hash id)
    task_id: Option<String>,
}

fn compute_id(path: &Path) -> String {
    let path_str = path.to_string_lossy();
    let path_without_ext = path.with_extension("");
    let key = path_without_ext.to_string_lossy();
    format!("{:x}", md5::compute(key.as_bytes()))
}

fn extract_tags(frontmatter: &Option<serde_json::Value>, content: &str) -> Vec<String> {
    let mut tags = HashSet::new();

    // 1. Frontmatter tags
    if let Some(fm) = frontmatter {
        if let Some(tag_val) = fm.get("tags") {
            if let Some(arr) = tag_val.as_array() {
                for t in arr {
                    if let Some(s) = t.as_str() {
                        tags.insert(s.to_string());
                    }
                }
            } else if let Some(s) = tag_val.as_str() {
                // Handle comma separated
                for part in s.split(',') {
                    tags.insert(part.trim().to_string());
                }
            }
        }
    }

    // 2. Hashtags in content
    // Regex: (space or start)(#tag)
    // Note: Rust regex doesn't support lookbehind/lookahead fully, so we match the group
    let re = Regex::new(r"(?:^|\s)#([a-zA-Z0-9_\-]+)").unwrap();
    for cap in re.captures_iter(content) {
        if let Some(m) = cap.get(1) {
            tags.insert(m.as_str().to_string());
        }
    }

    tags.into_iter().collect()
}

fn parse_file(path: PathBuf) -> Option<FileData> {
    let content = fs::read_to_string(&path).ok()?;
    let matter = Matter::<YAML>::new();
    let result = matter.parse(&content);
    
    // Frontmatter data
    let fm_data = result.data.as_ref().map(|d| d.deserialize::<serde_json::Value>().ok()).flatten();

    // 1. Label/Title
    let mut label = path.file_stem()?.to_string_lossy().to_string();
    if let Some(ref fm) = fm_data {
        if let Some(title) = fm.get("title").and_then(|v| v.as_str()) {
            label = title.to_string();
        }
    }
    // Fallback to H1 if no FM title? (Simplification: skipping H1 parse for speed/robustness unless needed)

    // 2. Tags
    let tags = extract_tags(&fm_data, &result.content);

    // 3. Permalinks / Resolution Keys
    let mut permalinks = Vec::new();
    // Filename key
    if let Some(stem) = path.file_stem() {
        let stem_str = stem.to_string_lossy().to_string();
        permalinks.push(stem_str.to_lowercase());
    }
    // Permalink from FM
    if let Some(ref fm) = fm_data {
        if let Some(pl) = fm.get("permalink").and_then(|v| v.as_str()) {
            permalinks.push(pl.trim().to_lowercase());
        }
    }
    // Task ID prefixes (e.g. "aops-123")
    let stem_str = path.file_stem()?.to_string_lossy();
    let task_re = Regex::new(r"^([a-z]{1,4}-[a-z0-9]+)-").unwrap();
    if let Some(cap) = task_re.captures(&stem_str) {
        if let Some(m) = cap.get(1) {
            permalinks.push(m.as_str().to_lowercase());
        }
    }

    // 4. Raw Links
    // Extract [[wiki links]] and [md links](...)
    let mut raw_links = Vec::new();
    
    // Wiki links: [[target]] or [[target|alias]]
    let wiki_re = Regex::new(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]").unwrap();
    for cap in wiki_re.captures_iter(&result.content) {
        if let Some(m) = cap.get(1) {
            raw_links.push(m.as_str().trim().to_string());
        }
    }

    // Standard MD links: [label](target)
    // Ignore external http/https
    let md_re = Regex::new(r"\[([^\]]+)\]\(([^)]+)\)").unwrap();
    for cap in md_re.captures_iter(&result.content) {
        if let Some(m) = cap.get(2) {
            let link = m.as_str().trim();
            if !link.starts_with("http") && !link.starts_with("#") {
                raw_links.push(link.to_string());
            }
        }
    }

    // Extract task-related frontmatter fields
    let node_type = fm_data.as_ref().and_then(|fm| fm.get("type").and_then(|v| v.as_str()).map(String::from));
    let status = fm_data.as_ref().and_then(|fm| fm.get("status").and_then(|v| v.as_str()).map(String::from));
    let priority = fm_data.as_ref().and_then(|fm| fm.get("priority").and_then(|v| v.as_i64()).map(|v| v as i32));
    let order = fm_data.as_ref().and_then(|fm| fm.get("order").and_then(|v| v.as_i64()).map(|v| v as i32)).unwrap_or(0);
    let parent = fm_data.as_ref().and_then(|fm| fm.get("parent").and_then(|v| v.as_str()).map(String::from));
    let depends_on = fm_data.as_ref()
        .and_then(|fm| fm.get("depends_on"))
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default();
    let children = fm_data.as_ref()
        .and_then(|fm| fm.get("children"))
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default();
    let blocks = fm_data.as_ref()
        .and_then(|fm| fm.get("blocks"))
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default();
    let project = fm_data.as_ref().and_then(|fm| fm.get("project").and_then(|v| v.as_str()).map(String::from));
    let due = fm_data.as_ref().and_then(|fm| fm.get("due").and_then(|v| v.as_str()).map(String::from));
    let depth = fm_data.as_ref().and_then(|fm| fm.get("depth").and_then(|v| v.as_i64()).map(|v| v as i32)).unwrap_or(0);
    let leaf = fm_data.as_ref().and_then(|fm| fm.get("leaf").and_then(|v| v.as_bool())).unwrap_or(true);
    let task_id = fm_data.as_ref().and_then(|fm| fm.get("id").and_then(|v| v.as_str()).map(String::from));

    Some(FileData {
        id: compute_id(&path),
        path,
        content: String::new(), // Don't keep heavy content in memory
        label,
        tags,
        raw_links,
        permalinks,
        node_type,
        status,
        priority,
        order,
        parent,
        depends_on,
        children,
        blocks,
        project,
        due,
        depth,
        leaf,
        task_id,
    })
}

fn resolve_link(link: &str, current_file: &FileData, id_map: &HashMap<String, String>) -> Option<String> {
    // 1. Try Lookup in map (Wiki-style)
    // Try exact, then lowercase
    if let Some(path) = id_map.get(link) {
        return Some(path.clone());
    }
    if let Some(path) = id_map.get(&link.to_lowercase()) {
        return Some(path.clone());
    }

    // 2. Try Relative Path
    let current_dir = current_file.path.parent()?;
    let joined = current_dir.join(link);
    // We ideally should check if this path exists in our scanned files.
    // For fast indexing, we can check if the canonicalized path (or just raw resolved path) matches any known file path
    // But we need absolute paths for the map logic used in extension.
    // Let's assume absolute paths in the map.
    
    // To properly check existence without hitting FS again, we'd need a Set of all valid paths.
    // Let's optimize: id_map stores ShortKey -> AbsPath.
    // We can also assume we might need full path resolution.
    
    // Simplification: If relative path resolution works, the extension uses `resolveLinkPath`.
    // Here we must emulate that.
    // If the link is "./foo.md", we join it. 
    // Since we are writing a standalone tool, we can just canonicalize.
    if joined.exists() {
        return Some(joined.canonicalize().ok()?.to_string_lossy().to_string());
    }

    None
}

fn output_graphml(graph: &Graph, path: &str) -> Result<()> {
    let mut xml = String::from(r#"<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
  <key id="d0" for="node" attr.name="label" attr.type="string"/>
  <key id="d1" for="node" attr.name="path" attr.type="string"/>
  <key id="d2" for="node" attr.name="tags" attr.type="string"/>
  <graph id="G" edgedefault="directed">
"#);

    for node in &graph.nodes {
        let label_escaped = node.label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
        let path_escaped = node.path.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
        let tags_str = node.tags.as_ref().map(|t| t.join(",")).unwrap_or_default();

        xml.push_str(&format!(
            "    <node id=\"{}\">\n      <data key=\"d0\">{}</data>\n      <data key=\"d1\">{}</data>\n      <data key=\"d2\">{}</data>\n    </node>\n",
            node.id, label_escaped, path_escaped, tags_str
        ));
    }

    for (i, edge) in graph.edges.iter().enumerate() {
        xml.push_str(&format!(
            "    <edge id=\"e{}\" source=\"{}\" target=\"{}\"/>\n",
            i, edge.source, edge.target
        ));
    }

    xml.push_str("  </graph>\n</graphml>\n");
    fs::write(path, xml)?;
    Ok(())
}

fn output_dot(graph: &Graph, path: &str) -> Result<()> {
    let mut dot = String::from("digraph G {\n    rankdir=TB;\n    node [shape=box, style=filled, fillcolor=\"#e9ecef\"];\n\n");

    for node in &graph.nodes {
        let label_escaped = node.label.replace("\"", "\\\"");
        dot.push_str(&format!("    \"{}\" [label=\"{}\"];\n", node.id, label_escaped));
    }

    dot.push('\n');

    for edge in &graph.edges {
        dot.push_str(&format!("    \"{}\" -> \"{}\";\n", edge.source, edge.target));
    }

    dot.push_str("}\n");
    fs::write(path, dot)?;
    Ok(())
}

/// Build MCP task index from parsed task files.
///
/// This produces the exact schema expected by tasks_server.py:
/// - version: 2
/// - generated: ISO timestamp
/// - tasks: {task_id: {id, title, type, status, priority, order, parent, children, depends_on, blocks, depth, leaf, project, path, due, tags}}
/// - by_project: {project: [task_ids]}
/// - roots: [task_ids with no parent]
/// - ready: [leaf tasks with no unmet deps and status active/inbox]
/// - blocked: [tasks with unmet deps or status blocked]
fn build_mcp_index(files: &[FileData], data_root: &Path) -> McpIndex {
    // Build lookup by task_id (from frontmatter id field)
    let mut task_id_to_file: HashMap<String, &FileData> = HashMap::new();
    for f in files {
        if let Some(ref tid) = f.task_id {
            task_id_to_file.insert(tid.clone(), f);
        }
    }

    // Build initial entries with direct fields
    let mut entries: HashMap<String, McpIndexEntry> = HashMap::new();
    for f in files {
        if let Some(ref tid) = f.task_id {
            let rel_path = f.path.strip_prefix(data_root)
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| f.path.to_string_lossy().to_string());

            entries.insert(tid.clone(), McpIndexEntry {
                id: tid.clone(),
                title: f.label.clone(),
                task_type: f.node_type.clone().unwrap_or_else(|| "task".to_string()),
                status: f.status.clone().unwrap_or_else(|| "inbox".to_string()),
                priority: f.priority.unwrap_or(2),
                order: f.order,
                parent: f.parent.clone(),
                children: Vec::new(),    // Computed below
                depends_on: f.depends_on.clone(),
                blocks: Vec::new(),      // Computed below
                depth: f.depth,
                leaf: f.leaf,
                project: f.project.clone(),
                path: rel_path,
                due: f.due.clone(),
                tags: f.tags.clone(),
            });
        }
    }

    // Compute children (inverse of parent) - collect updates first to avoid borrow issues
    let task_ids: Vec<String> = entries.keys().cloned().collect();
    let mut child_updates: Vec<(String, String)> = Vec::new(); // (parent_id, child_id)
    for tid in &task_ids {
        if let Some(entry) = entries.get(tid) {
            if let Some(parent_id) = entry.parent.clone() {
                if entries.contains_key(&parent_id) {
                    child_updates.push((parent_id, tid.clone()));
                }
            }
        }
    }
    for (parent_id, child_id) in child_updates {
        if let Some(parent_entry) = entries.get_mut(&parent_id) {
            parent_entry.children.push(child_id);
        }
    }

    // Compute blocks (inverse of depends_on) - collect updates first
    let mut block_updates: Vec<(String, String)> = Vec::new(); // (dep_id, blocker_id)
    for tid in &task_ids {
        if let Some(entry) = entries.get(tid) {
            for dep_id in &entry.depends_on {
                if entries.contains_key(dep_id) {
                    block_updates.push((dep_id.clone(), tid.clone()));
                }
            }
        }
    }
    for (dep_id, blocker_id) in block_updates {
        if let Some(dep_entry) = entries.get_mut(&dep_id) {
            dep_entry.blocks.push(blocker_id);
        }
    }

    // Update leaf status based on computed children
    for tid in &task_ids {
        if let Some(entry) = entries.get_mut(tid) {
            entry.leaf = entry.children.is_empty();
        }
    }

    // Build by_project groupings
    let mut by_project: HashMap<String, Vec<String>> = HashMap::new();
    for (tid, entry) in &entries {
        let project = entry.project.clone().unwrap_or_else(|| "inbox".to_string());
        by_project.entry(project).or_default().push(tid.clone());
    }

    // Identify roots (no parent OR parent doesn't exist in index)
    // Orphan tasks (with non-existent parents) are treated as roots
    let roots: Vec<String> = entries.iter()
        .filter(|(_, e)| {
            match &e.parent {
                None => true,
                Some(parent_id) => !entries.contains_key(parent_id),
            }
        })
        .map(|(tid, _)| tid.clone())
        .collect();

    // Compute ready and blocked
    let completed_statuses: HashSet<&str> = ["done", "cancelled"].into_iter().collect();
    let completed_ids: HashSet<String> = entries.iter()
        .filter(|(_, e)| completed_statuses.contains(e.status.as_str()))
        .map(|(tid, _)| tid.clone())
        .collect();

    let mut ready: Vec<String> = Vec::new();
    let mut blocked: Vec<String> = Vec::new();

    for (tid, entry) in &entries {
        // Skip completed tasks
        if completed_statuses.contains(entry.status.as_str()) {
            continue;
        }

        // Check if blocked
        let unmet_deps: Vec<&String> = entry.depends_on.iter()
            .filter(|d| !completed_ids.contains(*d))
            .collect();

        if !unmet_deps.is_empty() || entry.status == "blocked" {
            blocked.push(tid.clone());
        } else if entry.leaf && (entry.status == "active" || entry.status == "inbox") {
            ready.push(tid.clone());
        }
    }

    // Sort ready by priority, order, title
    ready.sort_by(|a, b| {
        let ea = entries.get(a).unwrap();
        let eb = entries.get(b).unwrap();
        (ea.priority, ea.order, &ea.title).cmp(&(eb.priority, eb.order, &eb.title))
    });

    McpIndex {
        version: 2,
        generated: Utc::now().to_rfc3339(),
        tasks: entries,
        by_project,
        roots,
        ready,
        blocked,
    }
}

fn output_mcp_index(files: &[FileData], path: &str, data_root: &Path) -> Result<()> {
    let index = build_mcp_index(files, data_root);
    let json = serde_json::to_string_pretty(&index)?;
    fs::write(path, json)?;
    Ok(())
}

fn main() -> Result<()> {
    let args = Args::parse();
    let root = Path::new(&args.root).canonicalize()?;
    
    println!("Scanning directory: {:?}", root);

    // 1. Find all markdown files (respects .gitignore)
    let walker = WalkBuilder::new(&root)
        .hidden(false)      // Include hidden files
        .git_ignore(true)   // Respect .gitignore
        .git_global(true)   // Respect global gitignore
        .git_exclude(true)  // Respect .git/info/exclude
        .build();

    let entries: Vec<PathBuf> = walker
        .filter_map(|e| e.ok())
        .filter(|e| {
            let p = e.path();
            p.is_file() && p.extension().map_or(false, |ext| ext == "md")
        })
        .map(|e| e.path().to_owned())
        .collect();

    println!("Found {} markdown files. Parsing...", entries.len());

    // 2. Parse files in parallel
    let mut files: Vec<FileData> = entries
        .par_iter()
        .filter_map(|path| parse_file(path.clone()))
        .collect();

    // 3. Filter by type if specified
    if let Some(ref filter_types) = args.filter_type {
        let filter_set: HashSet<String> = filter_types.iter().map(|s| s.to_lowercase()).collect();
        let before_count = files.len();
        files.retain(|f| {
            f.node_type.as_ref().map(|t| filter_set.contains(&t.to_lowercase())).unwrap_or(false)
        });
        println!("Filtered to {} files with type in {:?}", files.len(), filter_types);
    }

    // 3. Build Lookup Maps
    // Map: Key (filename/permalink) -> Absolute Path
    let mut id_map: HashMap<String, String> = HashMap::new();
    // Map: Absolute Path -> ID (for edge construction)
    let mut path_to_id: HashMap<String, String> = HashMap::new();

    for f in &files {
        let abs_path = f.path.canonicalize()?.to_string_lossy().to_string();
        path_to_id.insert(abs_path.clone(), f.id.clone());

        for key in &f.permalinks {
            id_map.insert(key.clone(), abs_path.clone());
        }
        // Also ensure absolute path is a key? Optional but helpful
    }

    // 4. Build Edges in Parallel
    // Helper: resolve a frontmatter reference (task ID or filename) to target ID
    let resolve_fm_ref = |ref_str: &str| -> Option<String> {
        // Try direct lookup by lowercase key
        if let Some(path) = id_map.get(&ref_str.to_lowercase()) {
            return path_to_id.get(path).cloned();
        }
        None
    };

    let edges: Vec<Edge> = files
        .par_iter()
        .flat_map(|f| {
            let mut local_edges = Vec::new();

            // Edges from wikilinks and markdown links
            for link in &f.raw_links {
                if let Some(target_path) = resolve_link(link, f, &id_map) {
                    if let Some(target_id) = path_to_id.get(&target_path) {
                         if f.id != *target_id {
                             local_edges.push(Edge {
                                 source: f.id.clone(),
                                 target: target_id.clone(),
                             });
                         }
                    }
                }
            }

            // Edges from frontmatter: parent (this -> parent)
            if let Some(ref parent_ref) = f.parent {
                if let Some(target_id) = resolve_fm_ref(parent_ref) {
                    if f.id != target_id {
                        local_edges.push(Edge {
                            source: f.id.clone(),
                            target: target_id,
                        });
                    }
                }
            }

            // Edges from frontmatter: depends_on (this -> dependency)
            for dep_ref in &f.depends_on {
                if let Some(target_id) = resolve_fm_ref(dep_ref) {
                    if f.id != target_id {
                        local_edges.push(Edge {
                            source: f.id.clone(),
                            target: target_id,
                        });
                    }
                }
            }

            // Edges from frontmatter: children (this -> child)
            for child_ref in &f.children {
                if let Some(target_id) = resolve_fm_ref(child_ref) {
                    if f.id != target_id {
                        local_edges.push(Edge {
                            source: f.id.clone(),
                            target: target_id,
                        });
                    }
                }
            }

            // Edges from frontmatter: blocks (this -> blocked task)
            for blocks_ref in &f.blocks {
                if let Some(target_id) = resolve_fm_ref(blocks_ref) {
                    if f.id != target_id {
                        local_edges.push(Edge {
                            source: f.id.clone(),
                            target: target_id,
                        });
                    }
                }
            }

            // Edges from frontmatter: project (this -> project)
            if let Some(ref project_ref) = f.project {
                if let Some(target_id) = resolve_fm_ref(project_ref) {
                    if f.id != target_id {
                        local_edges.push(Edge {
                            source: f.id.clone(),
                            target: target_id,
                        });
                    }
                }
            }

            local_edges
        })
        .collect();

    // 5. Output based on format
    let output_base = args.output.trim_end_matches(".json")
        .trim_end_matches(".graphml")
        .trim_end_matches(".dot");

    // Handle mcp-index format specially (doesn't use graph structure, needs files before consumption)
    if args.format.to_lowercase() == "mcp-index" {
        let path = format!("{}.json", output_base);
        output_mcp_index(&files, &path, &root)?;
        println!("  Saved MCP task index: {}", path);
        let index = build_mcp_index(&files, &root);
        println!(
            "MCP index generated: {} tasks, {} ready, {} blocked",
            index.tasks.len(),
            index.ready.len(),
            index.blocked.len(),
        );
        return Ok(());
    }

    // 6. Construct Graph Nodes (consumes files)
    let nodes: Vec<Node> = files
        .into_iter()
        .map(|f| {
            Node {
                id: f.id,
                path: f.path.canonicalize().unwrap_or(f.path).to_string_lossy().to_string(),
                label: f.label,
                tags: if f.tags.is_empty() { None } else { Some(f.tags) },
                node_type: f.node_type,
                status: f.status,
                priority: f.priority,
                parent: f.parent,
                depends_on: if f.depends_on.is_empty() { None } else { Some(f.depends_on) },
            }
        })
        .collect();

    let graph = Graph { nodes, edges };

    let formats: Vec<&str> = match args.format.to_lowercase().as_str() {
        "json" => vec!["json"],
        "graphml" => vec!["graphml"],
        "dot" => vec!["dot"],
        _ => vec!["json", "graphml", "dot"], // "all" or default
    };

    for fmt in &formats {
        match *fmt {
            "graphml" => {
                let path = format!("{}.graphml", output_base);
                output_graphml(&graph, &path)?;
                println!("  Saved {}", path);
            }
            "dot" => {
                let path = format!("{}.dot", output_base);
                output_dot(&graph, &path)?;
                println!("  Saved {}", path);
            }
            _ => {
                let path = format!("{}.json", output_base);
                let json = serde_json::to_string_pretty(&graph)?;
                fs::write(&path, json)?;
                println!("  Saved {}", path);
            }
        }
    }

    println!(
        "Graph generated: {} nodes, {} edges ({} format{})",
        graph.nodes.len(),
        graph.edges.len(),
        formats.len(),
        if formats.len() > 1 { "s" } else { "" }
    );

    Ok(())
}
