"""Prompt templates for Engineering Intelligence Agent reasoning steps."""

INCIDENT_UNDERSTANDING_PROMPT = """You are an expert Reliability & Telemetry Engineer investigating an incident.
Target Service: {service}
Incident Description: {incident}

Analyze the incident and outline key metrics, logs, and code areas to investigate."""

HYPOTHESIS_FORMULATION_PROMPT = """Based on collected engineering evidence from GitHub and Operations Runtime:

Evidence Summary:
{evidence_summary}

Formulate candidate hypotheses for the root cause of the incident."""

REPORT_GENERATION_PROMPT = """Generate a formal Root Cause Analysis (RCA) report based on validated evidence:

Target Service: {service}
Incident: {incident}
Root Cause: {root_cause}
Confidence Score: {confidence}

Evidence Items:
{evidence_list}
"""
