import re
from pathlib import Path
import yaml
from server.config import Config

class QueryLoader:
    """Discovers, parses, and indexes modular .sql curriculum files with YAML frontmatter."""

    def __init__(self, queries_dir: Path | None = None):
        self.queries_dir = queries_dir or Config.QUERIES_DIR

    def load_query_file(self, file_path: Path) -> dict:
        """Parses a single .sql file containing /*--- ... ---*/ frontmatter and SQL body."""
        content = file_path.read_text(encoding="utf-8")

        # Match /*--- yaml ---*/ or standard --- yaml ---
        frontmatter_match = re.search(r"/\*---\s*\n(.*?)\n\s*---\*/", content, flags=re.DOTALL)
        if not frontmatter_match:
            frontmatter_match = re.search(r"^---\s*\n(.*?)\n\s*---", content, flags=re.DOTALL)

        metadata = {}
        sql = content

        if frontmatter_match:
            raw_yaml = frontmatter_match.group(1)
            try:
                metadata = yaml.safe_load(raw_yaml) or {}
            except Exception as e:
                metadata = {"parse_error": str(e)}
            # SQL is everything after the frontmatter match
            sql = content[frontmatter_match.end():].strip()

        query_id = metadata.get("id") or file_path.stem

        return {
            "id": query_id,
            "filename": file_path.name,
            "relative_path": str(file_path.relative_to(self.queries_dir) if file_path.is_relative_to(self.queries_dir) else file_path),
            "title": metadata.get("title", file_path.stem.replace("_", " ").title()),
            "target_language": metadata.get("target_language", "all"),
            "variant_compatibility": metadata.get("variant_compatibility", ["*"]),
            "suite": metadata.get("suite", "tutoring"),
            "level": metadata.get("level", "Basic"),
            "sequence": metadata.get("sequence", 999),
            "category": metadata.get("category", "General"),
            "pedagogical_rationale": metadata.get("pedagogical_rationale", "").strip(),
            "guided_experiments": metadata.get("guided_experiments", []),
            "lab_challenge": metadata.get("lab_challenge"),
            "sql": sql
        }

    def get_all_queries(self) -> list[dict]:
        """Discovers and returns all queries sorted by suite and sequence."""
        queries: list[dict] = []
        if not self.queries_dir.exists():
            return queries

        for file_path in sorted(self.queries_dir.rglob("*.sql")):
            try:
                q = self.load_query_file(file_path)
                queries.append(q)
            except Exception:
                continue

        queries.sort(key=lambda q: (q["suite"], q["sequence"], q["id"]))
        return queries

    def get_query_by_id(self, query_id: str) -> dict | None:
        """Finds a query by its unique ID or filename stem."""
        for q in self.get_all_queries():
            if q["id"] == query_id or Path(q["filename"]).stem == query_id:
                return q
        return None

    def get_queries_tree(self, language: str | None = None, suite: str | None = None) -> dict:
        """Organizes filtered queries into a suite -> level -> [queries] hierarchy."""
        tree: dict[str, dict[str, list[dict]]] = {}

        for q in self.get_all_queries():
            # Filter by language if specified
            if language and q["target_language"] not in {"all", "*", language}:
                continue
            # Filter by suite if specified
            if suite and q["suite"] != suite:
                continue

            q_suite = q["suite"]
            q_level = q["level"]

            if q_suite not in tree:
                tree[q_suite] = {}
            if q_level not in tree[q_suite]:
                tree[q_suite][q_level] = []

            tree[q_suite][q_level].append(q)

        return tree
