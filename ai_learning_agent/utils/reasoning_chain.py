"""
Reasoning Chain Visualization

Provides utilities for capturing, storing, and visualizing AI reasoning chains.
Enables transparency into how the AI formulates answers and reaches conclusions.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# Set up logger
logger = logging.getLogger(__name__)

class ReasoningStepType(Enum):
    """Types of reasoning steps in the chain."""
    QUERY_ANALYSIS = "query_analysis"
    KNOWLEDGE_SEARCH = "knowledge_search" 
    RELEVANCE_RANKING = "relevance_ranking"
    INFORMATION_EXTRACTION = "information_extraction"
    FACT_VERIFICATION = "fact_verification"
    CONTEXT_INTEGRATION = "context_integration"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    ANSWER_FORMULATION = "answer_formulation"
    SELF_REFLECTION = "self_reflection"
    WEB_RESEARCH = "web_research"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"
    DECISION_MAKING = "decision_making"
    EXAM_PREPARATION = "exam_preparation"
    STUDY_PLANNING = "study_planning"

@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str  # Unique identifier for the step
    step_type: ReasoningStepType  # Type of reasoning step
    description: str  # Human-readable description
    inputs: Dict[str, Any] = field(default_factory=dict)  # Input data for this step
    outputs: Dict[str, Any] = field(default_factory=dict)  # Output data from this step
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.0  # Confidence level (0.0 to 1.0)
    duration_ms: Optional[int] = None  # Execution time in milliseconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enum to string for serialization
        data["step_type"] = data["step_type"].value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReasoningStep':
        """Create from dictionary."""
        step_data = data.copy()
        # Convert string back to enum
        step_data["step_type"] = ReasoningStepType(step_data["step_type"])
        return cls(**step_data)

@dataclass
class ReasoningChain:
    """A complete reasoning chain composed of multiple steps."""
    chain_id: str  # Unique identifier for this chain
    query: str  # The original user query
    steps: List[ReasoningStep] = field(default_factory=list)  # All steps in the chain
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def add_step(self, step: ReasoningStep) -> None:
        """Add a reasoning step to the chain."""
        self.steps.append(step)
    
    def complete(self) -> None:
        """Mark the reasoning chain as complete."""
        self.end_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chain_id": self.chain_id,
            "query": self.query,
            "steps": [step.to_dict() for step in self.steps],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReasoningChain':
        """Create from dictionary."""
        chain_data = data.copy()
        chain_data["steps"] = [ReasoningStep.from_dict(step) for step in chain_data["steps"]]
        return cls(**chain_data)


class ReasoningChainManager:
    """Manages reasoning chains, including storage and retrieval."""
    
    def __init__(self, max_chains: int = 100):
        self.chains: Dict[str, ReasoningChain] = {}
        self.max_chains = max_chains
    
    def create_chain(self, query: str, chain_id: Optional[str] = None) -> ReasoningChain:
        """Create a new reasoning chain."""
        if chain_id is None:
            chain_id = f"chain_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.chains)}"
        
        chain = ReasoningChain(chain_id=chain_id, query=query)
        self.chains[chain_id] = chain
        
        # Limit number of stored chains
        if len(self.chains) > self.max_chains:
            oldest_key = sorted(self.chains.keys(), 
                               key=lambda k: self.chains[k].start_time)[0]
            del self.chains[oldest_key]
        
        return chain
    
    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        """Get a reasoning chain by ID."""
        return self.chains.get(chain_id)
    
    def list_chains(self) -> List[Dict[str, Any]]:
        """List all reasoning chains."""
        return [
            {
                "chain_id": chain.chain_id,
                "query": chain.query,
                "start_time": chain.start_time,
                "end_time": chain.end_time,
                "step_count": len(chain.steps)
            }
            for chain in self.chains.values()
        ]
    
    def save_chains_to_file(self, filename: str) -> bool:
        """Save all chains to a file."""
        try:
            with open(filename, 'w') as f:
                json.dump({
                    "chains": [chain.to_dict() for chain in self.chains.values()]
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving chains: {e}")
            return False
    
    def load_chains_from_file(self, filename: str) -> bool:
        """Load chains from a file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.chains = {
                    chain["chain_id"]: ReasoningChain.from_dict(chain)
                    for chain in data["chains"]
                }
            return True
        except Exception as e:
            logger.error(f"Error loading chains: {e}")
            return False


class ReasoningChainVisualizer:
    """Creates human-readable visualizations of reasoning chains."""
    
    @staticmethod
    def generate_text_visualization(chain: ReasoningChain) -> str:
        """Generate a text-based visualization of the reasoning chain."""
        lines = [
            f"🧠 REASONING CHAIN: '{chain.query}'",
            f"⏱️ {chain.start_time} to {chain.end_time or 'In progress'}",
            "-" * 70
        ]
        
        for i, step in enumerate(chain.steps, 1):
            lines.append(f"STEP {i}: {step.step_type.value.upper()}")
            lines.append(f"  🔎 {step.description}")
            
            # Show confidence if available
            if step.confidence > 0:
                confidence_bar = "▓" * int(step.confidence * 10)
                lines.append(f"  📊 Confidence: {confidence_bar} ({step.confidence:.2f})")
            
            # Show inputs/outputs if they exist and aren't too large
            if step.inputs:
                input_str = json.dumps(step.inputs)
                if len(input_str) < 100:  # Only show brief inputs
                    lines.append(f"  ⮕ Input: {input_str}")
            
            if step.outputs:
                output_preview = ReasoningChainVisualizer._format_output(step.outputs)
                lines.append(f"  ⮕ Result: {output_preview}")
            
            # Show execution time if available
            if step.duration_ms:
                lines.append(f"  ⏱️ Time: {step.duration_ms}ms")
            
            lines.append("")  # Empty line between steps
        
        lines.append("-" * 70)
        lines.append(f"Total steps: {len(chain.steps)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_markdown_visualization(chain: ReasoningChain) -> str:
        """Generate a markdown visualization of the reasoning chain."""
        lines = [
            f"# Reasoning Chain: '{chain.query}'",
            f"**Started:** {chain.start_time}  ",
            f"**Completed:** {chain.end_time or 'In progress'}",
            "",
            "## Reasoning Steps"
        ]
        
        for i, step in enumerate(chain.steps, 1):
            lines.append(f"### Step {i}: {step.step_type.value.title()}")
            lines.append(f"{step.description}")
            lines.append("")
            
            # Show confidence if available
            if step.confidence > 0:
                lines.append(f"**Confidence:** {step.confidence:.2f}")
                lines.append("")
            
            # Add timing information if available
            if step.duration_ms:
                lines.append(f"**Processing Time:** {step.duration_ms}ms")
                lines.append("")
            
            # Add inputs in collapsible section if they exist
            if step.inputs:
                lines.append("<details>")
                lines.append("<summary>Inputs</summary>")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(step.inputs, indent=2))
                lines.append("```")
                lines.append("</details>")
                lines.append("")
            
            # Add outputs in collapsible section if they exist
            if step.outputs:
                lines.append("<details>")
                lines.append("<summary>Outputs</summary>")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(step.outputs, indent=2))
                lines.append("```")
                lines.append("</details>")
                lines.append("")
            
            lines.append("---")
        
        lines.append(f"**Total Steps:** {len(chain.steps)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_html_visualization(chain: ReasoningChain) -> str:
        """Generate an HTML visualization of the reasoning chain."""
        html = [
            "<div class='reasoning-chain'>",
            f"<h3>Reasoning Chain: '{chain.query}'</h3>",
            f"<div class='chain-metadata'>Started: {chain.start_time}</div>",
            "<div class='reasoning-steps'>"
        ]
        
        for i, step in enumerate(chain.steps, 1):
            html.append(f"<div class='reasoning-step'>")
            html.append(f"<div class='step-header'>Step {i}: {step.step_type.value}</div>")
            html.append(f"<div class='step-description'>{step.description}</div>")
            
            # Add confidence bar if available
            if step.confidence > 0:
                html.append("<div class='confidence-wrapper'>")
                html.append(f"<div class='confidence-bar' style='width:{int(step.confidence*100)}%'></div>")
                html.append(f"<div class='confidence-text'>{step.confidence:.2f}</div>")
                html.append("</div>")
            
            # Add collapsible inputs/outputs
            if step.inputs or step.outputs:
                html.append("<div class='step-details'>")
                if step.inputs:
                    html.append("<details>")
                    html.append("<summary>Inputs</summary>")
                    html.append(f"<pre>{json.dumps(step.inputs, indent=2)}</pre>")
                    html.append("</details>")
                
                if step.outputs:
                    html.append("<details>")
                    html.append("<summary>Outputs</summary>")
                    html.append(f"<pre>{json.dumps(step.outputs, indent=2)}</pre>")
                    html.append("</details>")
                html.append("</div>")
            
            html.append("</div>")  # Close reasoning-step
        
        html.append("</div>")  # Close reasoning-steps
        html.append("</div>")  # Close reasoning-chain
        
        return "\n".join(html)
        
    @staticmethod
    def generate_interactive_html(chain: ReasoningChain) -> str:
        """Generate a fully interactive HTML visualization with JavaScript for chain exploration."""
        # CSS styles for the visualization
        css = """
        <style>
        .reasoning-container {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 20px auto;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            background: #fff;
        }
        .reasoning-header {
            border-bottom: 2px solid #eee;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .reasoning-steps {
            position: relative;
        }
        .reasoning-step {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        .reasoning-step:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }
        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .step-type {
            font-weight: bold;
            color: #4285f4;
        }
        .step-metrics {
            font-size: 0.85em;
            color: #666;
        }
        .step-description {
            margin-bottom: 10px;
            font-style: italic;
        }
        .confidence-bar-container {
            height: 10px;
            background: #eee;
            border-radius: 5px;
            margin: 10px 0;
        }
        .confidence-bar {
            height: 100%;
            background: linear-gradient(90deg, #4285f4, #34a853);
            border-radius: 5px;
        }
        .step-details {
            margin-top: 15px;
        }
        .detail-toggle {
            background: #f5f5f5;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
            font-size: 0.9em;
        }
        .detail-toggle:hover {
            background: #e0e0e0;
        }
        .detail-content {
            display: none;
            background: #f9f9f9;
            border-radius: 4px;
            padding: 10px;
            margin-top: 10px;
            overflow: auto;
            max-height: 300px;
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
        }
        .timeline {
            position: absolute;
            left: -20px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #4285f4;
        }
        .timeline-point {
            position: absolute;
            left: -26px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4285f4;
        }
        .metadata-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        .metadata-table th, .metadata-table td {
            padding: 8px;
            border: 1px solid #ddd;
            text-align: left;
        }
        .metadata-table th {
            background: #f5f5f5;
        }
        </style>
        """
        
        # JavaScript for interactivity
        js = """
        <script>
        function toggleDetail(id) {
            const content = document.getElementById(id);
            if (content.style.display === 'block') {
                content.style.display = 'none';
            } else {
                content.style.display = 'block';
            }
        }
        
        function highlightStep(stepId) {
            // Remove highlight from all steps
            document.querySelectorAll('.reasoning-step').forEach(step => {
                step.style.background = '#fff';
            });
            
            // Add highlight to this step
            const step = document.getElementById('step-' + stepId);
            if (step) {
                step.style.background = '#f0f7ff';
                step.scrollIntoView({behavior: 'smooth', block: 'center'});
            }
        }
        </script>
        """
        
        # Main container
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            f"<title>Reasoning Chain: {chain.query}</title>",
            css,
            "</head>",
            "<body>",
            "<div class='reasoning-container'>",
            "<div class='reasoning-header'>",
            f"<h2>Reasoning Chain: '{chain.query}'</h2>",
            "<table class='metadata-table'>",
            "<tr><th>Started</th><td>" + chain.start_time + "</td></tr>",
            "<tr><th>Completed</th><td>" + (chain.end_time or "In progress") + "</td></tr>",
            f"<tr><th>Steps</th><td>{len(chain.steps)}</td></tr>",
            "</table>",
            "</div>",
            "<div class='reasoning-steps'>",
            "<div class='timeline'></div>"
        ]
        
        # Generate HTML for each step
        for i, step in enumerate(chain.steps, 1):
            position = i / len(chain.steps) * 100
            
            html.append(f"<div id='step-{i}' class='reasoning-step'>")
            html.append(f"<div class='timeline-point' style='top: {position}%'></div>")
            
            html.append("<div class='step-header'>")
            html.append(f"<div class='step-type'>Step {i}: {step.step_type.value.title()}</div>")
            
            # Add metrics
            metrics = []
            if step.duration_ms:
                metrics.append(f"{step.duration_ms}ms")
            if step.confidence > 0:
                metrics.append(f"Confidence: {step.confidence:.2f}")
                
            if metrics:
                html.append(f"<div class='step-metrics'>{' | '.join(metrics)}</div>")
            html.append("</div>")  # Close step-header
            
            # Description
            html.append(f"<div class='step-description'>{step.description}</div>")
            
            # Confidence bar if available
            if step.confidence > 0:
                html.append("<div class='confidence-bar-container'>")
                html.append(f"<div class='confidence-bar' style='width:{int(step.confidence*100)}%'></div>")
                html.append("</div>")
            
            # Add inputs/outputs
            html.append("<div class='step-details'>")
            
            if step.inputs:
                input_id = f"input-{i}"
                html.append(f"<button class='detail-toggle' onclick=\"toggleDetail('{input_id}')\">Inputs</button>")
            
            if step.outputs:
                output_id = f"output-{i}"
                html.append(f"<button class='detail-toggle' onclick=\"toggleDetail('{output_id}')\">Outputs</button>")
            
            if step.inputs:
                html.append(f"<div id='{input_id}' class='detail-content'>")
                html.append("<pre>" + json.dumps(step.inputs, indent=2) + "</pre>")
                html.append("</div>")
            
            if step.outputs:
                html.append(f"<div id='{output_id}' class='detail-content'>")
                html.append("<pre>" + json.dumps(step.outputs, indent=2) + "</pre>")
                html.append("</div>")
                
            html.append("</div>")  # Close step-details
            html.append("</div>")  # Close reasoning-step
        
        # Close containers
        html.append("</div>")  # Close reasoning-steps
        html.append("</div>")  # Close reasoning-container
        
        # Add JavaScript
        html.append(js)
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    @staticmethod
    def _format_output(output: Dict[str, Any]) -> str:
        """Format output for text visualization."""
        if not output:
            return "No output"
        
        if "error" in output:
            return f"Error: {output['error']}"
        
        if "summary" in output:
            return output["summary"]
        
        # Default formatting for complex outputs
        output_str = json.dumps(output)
        if len(output_str) > 100:
            return f"{output_str[:97]}..."
        return output_str


# Helper functions for timing reasoning steps
def start_timing():
    """Start timing a reasoning step."""
    return datetime.now()

def end_timing(start_time):
    """End timing and return duration in milliseconds."""
    delta = datetime.now() - start_time
    return int(delta.total_seconds() * 1000)


# Helper decorator to add reasoning steps automatically
def reasoning_step(step_type: ReasoningStepType, description_template: str):
    """
    Decorator to automatically add a reasoning step to the current chain.
    
    Args:
        step_type: Type of reasoning step
        description_template: Template for step description (can use {param_name})
        
    Usage:
        @reasoning_step(ReasoningStepType.QUERY_ANALYSIS, "Analyzing query: {query}")
        def analyze_query(self, query, chain_id):
            # Function implementation
            return result
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Get chain_id parameter
            chain_id = kwargs.get('chain_id')
            if chain_id is None and args:
                # Try to find chain_id in positional arguments
                for arg in args:
                    if isinstance(arg, str) and arg.startswith('chain_'):
                        chain_id = arg
                        break
            
            if not chain_id or not hasattr(self, 'reasoning_manager'):
                # If no chain_id or no reasoning_manager, just call the function
                return func(self, *args, **kwargs)
            
            # Get the chain
            chain = self.reasoning_manager.get_chain(chain_id)
            if not chain:
                # If chain doesn't exist, just call the function
                return func(self, *args, **kwargs)
            
            # Format description using available parameters
            description = description_template
            for key, value in kwargs.items():
                if key in description_template:
                    if isinstance(value, str):
                        description = description.replace(f"{{{key}}}", value)
            
            # Create step ID
            step_id = f"{chain_id}_step_{len(chain.steps) + 1}"
            
            # Create inputs dict from function args
            func_args = func.__code__.co_varnames[:func.__code__.co_argcount]
            inputs = {}
            for i, arg_name in enumerate(func_args):
                if i > 0 and i < len(args) + 1:  # Skip 'self'
                    # Only add serializable types
                    if isinstance(args[i-1], (str, int, float, bool, list, dict)):
                        inputs[arg_name] = args[i-1]
            
            # Add kwargs to inputs
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool, list, dict)):
                    inputs[key] = value
            
            # Create step
            step = ReasoningStep(
                step_id=step_id,
                step_type=step_type,
                description=description,
                inputs=inputs
            )
            
            # Add step to chain
            chain.add_step(step)
            
            # Time execution
            start_time = start_timing()
            
            try:
                # Call the function
                result = func(self, *args, **kwargs)
                
                # Update step with duration and output
                step.duration_ms = end_timing(start_time)
                
                # Only add serializable outputs
                if isinstance(result, (str, int, float, bool)):
                    step.outputs = {"result": result}
                elif isinstance(result, (list, dict)):
                    step.outputs = {"result": result}
                elif hasattr(result, "__dict__"):
                    try:
                        step.outputs = {"result": vars(result)}
                    except:
                        step.outputs = {"result_type": str(type(result))}
                else:
                    step.outputs = {"result_type": str(type(result))}
                
                return result
            except Exception as e:
                # Update step with error information
                step.duration_ms = end_timing(start_time)
                step.outputs = {"error": str(e)}
                raise
            
        return wrapper
    return decorator