"""
Knowledge Graph Module

Builds and manages knowledge graphs from extracted concepts and relationships.
"""

import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Node:
    """Represents a node in the knowledge graph."""
    id: str
    label: str
    node_type: str
    properties: Dict[str, Any]
    weight: float = 1.0


@dataclass
class Edge:
    """Represents an edge in the knowledge graph."""
    source: str
    target: str
    relationship: str
    weight: float
    properties: Dict[str, Any]


@dataclass
class Path:
    """Represents a path between nodes."""
    nodes: List[str]
    edges: List[str]
    total_weight: float
    length: int


class KnowledgeGraph:
    """
    Knowledge graph for representing and querying learned information.
    
    Features:
    - Node and edge management
    - Path finding
    - Concept clustering
    - Graph analysis
    - Query capabilities
    """
    
    def __init__(self, config):
        """Initialize the knowledge graph."""
        self.config = config
        self.logger = logging.getLogger("knowledge_graph")
        
        # Graph storage
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        
        # Graph statistics
        self.node_count = 0
        self.edge_count = 0
        
        self.logger.info("Knowledge graph initialized")
    
    async def build_graph(self, concepts: List[str], relationships: List[Any]) -> Dict[str, Any]:
        """
        Build a knowledge graph from concepts and relationships.
        
        Args:
            concepts: List of extracted concepts
            relationships: List of concept relationships
            
        Returns:
            Graph structure dictionary
        """
        self.logger.info(f"Building knowledge graph with {len(concepts)} concepts and {len(relationships)} relationships")
        
        # Add concept nodes
        for concept in concepts:
            await self.add_node(concept, concept, "concept")
        
        # Add relationship edges
        for rel in relationships:
            await self.add_edge(
                rel.source,
                rel.target,
                rel.relationship_type,
                rel.strength,
                {"context": rel.context}
            )
        
        # Analyze graph structure
        graph_analysis = await self.analyze_graph()
        
        return {
            "nodes": list(self.nodes.values()),
            "edges": list(self.edges.values()),
            "analysis": graph_analysis,
            "adjacency_list": dict(self.adjacency_list)
        }
    
    async def add_node(self, node_id: str, label: str, node_type: str, 
                      properties: Optional[Dict[str, Any]] = None) -> Node:
        """Add a node to the graph."""
        if properties is None:
            properties = {}
        
        node = Node(
            id=node_id,
            label=label,
            node_type=node_type,
            properties=properties
        )
        
        self.nodes[node_id] = node
        self.node_count += 1
        
        self.logger.debug(f"Added node: {node_id}")
        return node
    
    async def add_edge(self, source: str, target: str, relationship: str, 
                      weight: float = 1.0, properties: Optional[Dict[str, Any]] = None) -> Edge:
        """Add an edge to the graph."""
        if properties is None:
            properties = {}
        
        # Ensure source and target nodes exist
        if source not in self.nodes:
            await self.add_node(source, source, "concept")
        
        if target not in self.nodes:
            await self.add_node(target, target, "concept")
        
        edge_id = f"{source}->{target}"
        edge = Edge(
            source=source,
            target=target,
            relationship=relationship,
            weight=weight,
            properties=properties
        )
        
        self.edges[edge_id] = edge
        self.adjacency_list[source].append(target)
        self.edge_count += 1
        
        self.logger.debug(f"Added edge: {source} -> {target} ({relationship})")
        return edge
    
    async def find_shortest_path(self, start: str, end: str) -> Optional[Path]:
        """Find the shortest path between two nodes using BFS."""
        if start not in self.nodes or end not in self.nodes:
            return None
        
        if start == end:
            return Path(nodes=[start], edges=[], total_weight=0, length=0)
        
        # BFS for shortest path
        queue = [(start, [start], [], 0)]
        visited = set()
        
        while queue:
            current, path_nodes, path_edges, total_weight = queue.pop(0)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            for neighbor in self.adjacency_list[current]:
                if neighbor == end:
                    # Found the target
                    edge_id = f"{current}->{neighbor}"
                    edge_weight = self.edges.get(edge_id, Edge("", "", "", 1.0, {})).weight
                    
                    return Path(
                        nodes=path_nodes + [neighbor],
                        edges=path_edges + [edge_id],
                        total_weight=total_weight + edge_weight,
                        length=len(path_nodes)
                    )
                
                if neighbor not in visited:
                    edge_id = f"{current}->{neighbor}"
                    edge_weight = self.edges.get(edge_id, Edge("", "", "", 1.0, {})).weight
                    
                    queue.append((
                        neighbor,
                        path_nodes + [neighbor],
                        path_edges + [edge_id],
                        total_weight + edge_weight
                    ))
        
        return None
    
    async def get_neighbors(self, node_id: str, max_distance: int = 1) -> List[str]:
        """Get neighbors of a node within specified distance."""
        if node_id not in self.nodes:
            return []
        
        neighbors = set()
        current_level = {node_id}
        
        for distance in range(max_distance):
            next_level = set()
            
            for node in current_level:
                for neighbor in self.adjacency_list[node]:
                    if neighbor not in neighbors and neighbor != node_id:
                        neighbors.add(neighbor)
                        next_level.add(neighbor)
            
            current_level = next_level
            if not current_level:
                break
        
        return list(neighbors)
    
    async def find_central_concepts(self, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find the most central concepts in the graph."""
        centrality_scores = {}
        
        for node_id in self.nodes:
            # Calculate degree centrality (simplified)
            in_degree = sum(1 for edge in self.edges.values() if edge.target == node_id)
            out_degree = len(self.adjacency_list[node_id])
            
            centrality_scores[node_id] = (in_degree + out_degree) / max(1, self.node_count - 1)
        
        # Sort by centrality score
        sorted_concepts = sorted(centrality_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_concepts[:top_k]
    
    async def get_concept_clusters(self, max_clusters: int = 5) -> List[List[str]]:
        """Group related concepts into clusters."""
        clusters = []
        visited = set()
        
        for node_id in self.nodes:
            if node_id in visited:
                continue
            
            # BFS to find connected components
            cluster = []
            queue = [node_id]
            
            while queue and len(clusters) < max_clusters:
                current = queue.pop(0)
                
                if current in visited:
                    continue
                
                visited.add(current)
                cluster.append(current)
                
                # Add neighbors to queue
                for neighbor in self.adjacency_list[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)
                
                # Also check incoming edges
                for edge in self.edges.values():
                    if edge.target == current and edge.source not in visited:
                        queue.append(edge.source)
            
            if cluster:
                clusters.append(cluster)
        
        return clusters
    
    async def query_related_concepts(self, concept: str, max_results: int = 10) -> List[Tuple[str, str, float]]:
        """Query for concepts related to the given concept."""
        if concept not in self.nodes:
            return []
        
        related = []
        
        # Direct neighbors
        for neighbor in self.adjacency_list[concept]:
            edge_id = f"{concept}->{neighbor}"
            if edge_id in self.edges:
                edge = self.edges[edge_id]
                related.append((neighbor, edge.relationship, edge.weight))
        
        # Incoming edges
        for edge in self.edges.values():
            if edge.target == concept:
                related.append((edge.source, edge.relationship, edge.weight))
        
        # Sort by relationship strength
        related.sort(key=lambda x: x[2], reverse=True)
        
        return related[:max_results]
    
    async def analyze_graph(self) -> Dict[str, Any]:
        """Analyze the graph structure and return statistics."""
        if not self.nodes:
            return {"error": "Empty graph"}
        
        # Basic statistics
        stats = {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "density": self.edge_count / max(1, self.node_count * (self.node_count - 1)),
            "average_degree": sum(len(neighbors) for neighbors in self.adjacency_list.values()) / max(1, self.node_count)
        }
        
        # Find central concepts
        central_concepts = await self.find_central_concepts()
        stats["central_concepts"] = central_concepts
        
        # Find clusters
        clusters = await self.get_concept_clusters()
        stats["clusters"] = len(clusters)
        stats["largest_cluster_size"] = max(len(cluster) for cluster in clusters) if clusters else 0
        
        # Relationship types
        relationship_types = {}
        for edge in self.edges.values():
            rel_type = edge.relationship
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
        
        stats["relationship_types"] = relationship_types
        
        return stats
    
    async def export_graph(self, format_type: str = "dict") -> Dict[str, Any]:
        """Export the graph in various formats."""
        if format_type == "dict":
            return {
                "nodes": [
                    {
                        "id": node.id,
                        "label": node.label,
                        "type": node.node_type,
                        "properties": node.properties,
                        "weight": node.weight
                    }
                    for node in self.nodes.values()
                ],
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "relationship": edge.relationship,
                        "weight": edge.weight,
                        "properties": edge.properties
                    }
                    for edge in self.edges.values()
                ]
            }
        
        # Add more export formats as needed
        return {}
    
    def clear(self):
        """Clear the entire graph."""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency_list.clear()
        self.node_count = 0
        self.edge_count = 0
        
        self.logger.info("Knowledge graph cleared")
    
    def get_graph_summary(self) -> str:
        """Get a human-readable summary of the graph."""
        if not self.nodes:
            return "Empty knowledge graph"
        
        summary_parts = [
            f"Knowledge Graph Summary:",
            f"- {self.node_count} concepts",
            f"- {self.edge_count} relationships",
        ]
        
        if self.nodes:
            # Get top concepts by connections
            concept_connections = {}
            for node_id in self.nodes:
                connections = len(self.adjacency_list[node_id])
                # Count incoming edges
                incoming = sum(1 for edge in self.edges.values() if edge.target == node_id)
                concept_connections[node_id] = connections + incoming
            
            top_concepts = sorted(concept_connections.items(), key=lambda x: x[1], reverse=True)[:3]
            
            if top_concepts:
                summary_parts.append("- Top connected concepts:")
                for concept, connections in top_concepts:
                    summary_parts.append(f"  • {concept} ({connections} connections)")
        
        return "\n".join(summary_parts)