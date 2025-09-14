"""
Text Formatting Utilities

This module provides utilities for cleaning and formatting text responses
to make them more readable and visually appealing in the web interface.
"""

import re
from typing import Dict, Any

def clean_and_format_study_plan(text: str) -> str:
    """
    Clean and format study plan text for better presentation.
    
    Args:
        text: Raw study plan text
        
    Returns:
        Cleaned and formatted study plan text
    """
    # Remove excessive equals signs and ASCII art
    text = re.sub(r'=+', '', text)
    
    # Clean up multiple line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove redundant headers
    text = re.sub(r'📚\s*TENTATIVE\s*STUDY\s*PLAN.*?\n', '', text, flags=re.IGNORECASE)
    
    # Ensure proper markdown formatting for headers
    text = re.sub(r'^([A-Z][^:\n]*):$', r'## \1', text, flags=re.MULTILINE)
    
    # Format priority indicators
    text = re.sub(r'HIGH PRIORITY', r'**🔴 HIGH PRIORITY**', text, flags=re.IGNORECASE)
    text = re.sub(r'MEDIUM PRIORITY', r'**🟡 MEDIUM PRIORITY**', text, flags=re.IGNORECASE)
    text = re.sub(r'LOW PRIORITY', r'**🟢 LOW PRIORITY**', text, flags=re.IGNORECASE)
    
    # Format dates and times
    text = re.sub(r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b', r'**\1**', text)
    text = re.sub(r'\b(\d{1,2}:\d{2}\s*[AP]M)\b', r'*\1*', text)
    
    # Format course names (assuming they start with capital letters and may contain numbers)
    text = re.sub(r'\b([A-Z]{2,3}\s*\d+[A-Za-z]*)\b', r'**\1**', text)
    
    return text.strip()

def clean_reasoning_chain(text: str) -> str:
    """
    Clean and format reasoning chain text for better presentation.
    
    Args:
        text: Raw reasoning chain text
        
    Returns:
        Cleaned reasoning chain text
    """
    # Clean up excessive separators
    text = re.sub(r'=+', '', text)
    
    # Format step headers
    text = re.sub(r'STEP\s*(\d+):\s*([A-Z_]+)', r'**STEP \1: \2**', text)
    
    # Format timing information
    text = re.sub(r'Duration:\s*([0-9.]+s)', r'*Duration: \1*', text)
    
    # Format emoji arrows and icons consistently
    text = text.replace('⮕', '→').replace('🔎', '🔍')
    
    return text.strip()

def clean_and_format_general_response(text: str) -> str:
    """
    Clean and format general response text for better presentation.
    
    Args:
        text: Raw response text
        
    Returns:
        Cleaned and formatted response text
    """
    # Remove excessive separators and ASCII art
    text = re.sub(r'=+', '', text)
    text = re.sub(r'-{3,}', '', text)
    
    # Clean up multiple line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove common prefixes that don't add value
    text = re.sub(r'^(Here\'s|Here is|Let me|I\'ll|I will)\s+', '', text, flags=re.IGNORECASE)
    
    # Format bullet points consistently
    text = re.sub(r'^[\s]*[•·▪▫]\s*', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*[→➤➜]\s*', '- ', text, flags=re.MULTILINE)
    
    # Ensure proper spacing around headers
    text = re.sub(r'^(#{1,6})\s*(.+)$', r'\1 \2', text, flags=re.MULTILINE)
    
    # Format dates and times more consistently
    text = re.sub(r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b', r'**\1**', text)
    text = re.sub(r'\b(\d{1,2}:\d{2}\s*[APap][Mm])\b', r'*\1*', text)
    text = re.sub(r'\b(\d{1,2}\/\d{1,2}\/\d{2,4})\b', r'*\1*', text)
    
    # Format course codes and numbers
    text = re.sub(r'\b([A-Z]{2,4}[\s-]?\d{2,4}[A-Za-z]*)\b', r'**\1**', text)
    
    # Format priority levels
    text = re.sub(r'\b(high priority|urgent|critical)\b', r'**🔴 \1**', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(medium priority|important)\b', r'**🟡 \1**', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(low priority|optional)\b', r'**🟢 \1**', text, flags=re.IGNORECASE)
    
    # Add spacing around quotes and important statements
    text = re.sub(r'^"([^"]+)"$', r'> \1', text, flags=re.MULTILINE)
    
    # Format step-by-step instructions
    text = re.sub(r'^(\d+)\.\s+', r'**\1.** ', text, flags=re.MULTILINE)
    
    # Clean up excessive whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    
    return text.strip()

def format_response_for_web(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format response data for optimal web presentation.
    
    Args:
        response_data: Dictionary containing response information
        
    Returns:
        Formatted response data
    """
    if isinstance(response_data, str):
        return {"reply": clean_and_format_general_response(response_data)}
    
    if not isinstance(response_data, dict):
        return response_data
    
    # Clean main reply/answer
    if 'reply' in response_data:
        # Check if it's a study plan based on content
        if any(keyword in response_data['reply'].lower() for keyword in ['study plan', 'schedule', 'priority tasks', 'weekly']):
            response_data['reply'] = clean_and_format_study_plan(response_data['reply'])
        else:
            response_data['reply'] = clean_and_format_general_response(response_data['reply'])
    
    if 'answer' in response_data:
        if any(keyword in response_data['answer'].lower() for keyword in ['study plan', 'schedule', 'priority tasks', 'weekly']):
            response_data['answer'] = clean_and_format_study_plan(response_data['answer'])
        else:
            response_data['answer'] = clean_and_format_general_response(response_data['answer'])
    
    if 'study_plan' in response_data:
        response_data['study_plan'] = clean_and_format_study_plan(response_data['study_plan'])
    
    # Clean reasoning chain
    if 'reasoning' in response_data:
        response_data['reasoning'] = clean_reasoning_chain(response_data['reasoning'])
    
    return response_data

def extract_title_from_study_plan(text: str) -> str:
    """
    Extract a clean title from a study plan.
    
    Args:
        text: Study plan text
        
    Returns:
        Extracted title or default title
    """
    # Look for markdown headers
    header_match = re.search(r'^#+\s*(.+)$', text, re.MULTILINE)
    if header_match:
        return header_match.group(1).strip()
    
    # Look for lines that look like titles
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line and len(line.split()) <= 8 and ':' not in line:
            return line
    
    return "Study Plan"