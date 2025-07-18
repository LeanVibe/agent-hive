#!/usr/bin/env python3
"""
Agent Capabilities Registry

Manages and queries agent capabilities, specializations, and skills.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class AgentCapabilityRegistry:
    """Registry of agent capabilities and specializations"""

    def __init__(self, db_path: str = "agent_capabilities.db"):
        self.db_path = Path(db_path)
        self._init_database()
        self._populate_default_capabilities()

    def _init_database(self):
        """Initialize capabilities database"""
        conn = sqlite3.connect(self.db_path)

        # Agent capabilities table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_capabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                capability TEXT NOT NULL,
                proficiency_level INTEGER DEFAULT 5,
                description TEXT,
                last_updated TEXT,
                UNIQUE(agent_name, capability)
            )
        """)

        # Agent specializations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_specializations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                description TEXT,
                confidence_level INTEGER DEFAULT 8,
                last_updated TEXT,
                UNIQUE(agent_name, specialization)
            )
        """)

        # Agent availability table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'available',
                current_task TEXT,
                workload_level INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _populate_default_capabilities(self):
        """Populate default capabilities for known agents"""
        default_agents = {
            "pm-agent": {
                "capabilities": [
                    ("project_management", 9, "Project coordination and planning"),
                    ("task_breakdown", 8,
                     "Breaking down complex tasks into manageable chunks"),
                    ("conflict_resolution", 7,
                     "Resolving conflicts between team members and agents"),
                    ("quality_assurance", 6, "Ensuring quality standards are met"),
                    ("communication", 9, "Facilitating communication between agents"),
                    ("escalation_management", 8,
                     "Managing escalations to human oversight")
                ],
                "specializations": [
                    ("agile_methodology", "Expert in Agile/XP development practices", 9),
                    ("multi_agent_coordination",
                     "Coordinating multiple AI agents", 8),
                    ("pr_management", "Pull request review and merge coordination", 7),
                    ("sprint_planning", "Sprint planning and velocity tracking", 8)
                ]
            },
            "documentation-agent": {
                "capabilities": [
                    ("technical_writing", 9, "Creating technical documentation"),
                    ("api_documentation", 8, "Documenting APIs and interfaces"),
                    ("user_guides", 7, "Writing user guides and tutorials"),
                    ("code_comments", 8, "Adding comprehensive code comments"),
                    ("markdown_formatting", 9, "Expert in Markdown formatting"),
                    ("content_organization", 8, "Organizing and structuring content")
                ],
                "specializations": [
                    ("system_documentation", "Comprehensive system documentation", 9),
                    ("integration_guides", "Integration and setup documentation", 8),
                    ("monitoring_systems",
                     "Monitoring and observability documentation", 7),
                    ("validation_frameworks",
                     "Documentation validation and testing", 8)
                ]
            },
            "integration-agent": {
                "capabilities": [
                    ("system_integration", 9, "Integrating disparate systems"),
                    ("api_development", 8, "Developing and integrating APIs"),
                    ("middleware_development", 7, "Creating middleware components"),
                    ("authentication_systems", 8, "Implementing auth systems"),
                    ("microservices", 7, "Microservices architecture"),
                    ("data_pipeline", 6, "Building data processing pipelines")
                ],
                "specializations": [
                    ("auth_middleware", "Authentication and authorization middleware", 8),
                    ("service_discovery", "Service discovery and registration", 7),
                    ("api_gateway", "API gateway implementation", 6),
                    ("integration_testing", "Integration testing frameworks", 8)
                ]
            },
            "quality-agent": {
                "capabilities": [
                    ("testing", 9, "Comprehensive testing strategies"),
                    ("code_review", 8, "Code quality assessment"),
                    ("security_analysis", 7, "Security vulnerability assessment"),
                    ("performance_testing", 8, "Performance and load testing"),
                    ("automated_testing", 9, "Automated test suite development"),
                    ("quality_gates", 8, "Implementing quality gate systems")
                ],
                "specializations": [
                    ("security_frameworks", "Security testing and frameworks", 8),
                    ("quality_assurance", "Comprehensive QA processes", 9),
                    ("api_gateway_testing", "API gateway testing and validation", 7),
                    ("compliance_validation", "Compliance and standards validation", 8)
                ]
            },
            "intelligence-agent": {
                "capabilities": [
                    ("machine_learning", 8, "ML model development and integration"),
                    ("data_analysis", 7, "Data analysis and insights"),
                    ("ai_orchestration", 9, "AI agent orchestration"),
                    ("pattern_recognition", 8,
                     "Pattern recognition and classification"),
                    ("natural_language", 7, "Natural language processing"),
                    ("optimization", 8, "System optimization and efficiency")
                ],
                "specializations": [
                    ("agent_intelligence", "AI agent intelligence frameworks", 9),
                    ("decision_making", "Automated decision making systems", 8),
                    ("learning_systems", "Adaptive learning systems", 7),
                    ("intelligence_frameworks",
                     "Intelligence framework development", 8)
                ]
            },
            "orchestration-agent": {
                "capabilities": [
                    ("multi_agent_coordination", 9,
                     "Coordinating multiple agents"),
                    ("workflow_management", 8, "Managing complex workflows"),
                    ("resource_allocation", 7, "Allocating resources efficiently"),
                    ("load_balancing", 8, "Balancing workloads across agents"),
                    ("event_coordination", 8, "Coordinating system events"),
                    ("system_monitoring", 7, "Monitoring system health")
                ],
                "specializations": [
                    ("orchestration_systems", "Multi-agent orchestration", 9),
                    ("coordination_protocols", "Agent coordination protocols", 8),
                    ("workflow_optimization",
                     "Workflow optimization and management", 8),
                    ("system_orchestration", "System-level orchestration", 7)
                ]
            }
        }

        # Check if we already have data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM agent_capabilities")
        count = cursor.fetchone()[0]
        conn.close()

        if count > 0:
            return  # Already populated

        # Populate the database
        for agent_name, data in default_agents.items():
            for cap, level, desc in data["capabilities"]:
                self.add_capability(agent_name, cap, level, desc)

            for spec, desc, confidence in data["specializations"]:
                self.add_specialization(agent_name, spec, desc, confidence)

            self.update_availability(agent_name, "available", "", 0)

    def add_capability(self, agent_name: str, capability: str,
                       proficiency_level: int = 5, description: str = ""):
        """Add a capability for an agent"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO agent_capabilities
            (agent_name, capability, proficiency_level, description, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, capability, proficiency_level, description, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def add_specialization(self, agent_name: str, specialization: str,
                           description: str = "", confidence_level: int = 8):
        """Add a specialization for an agent"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO agent_specializations
            (agent_name, specialization, description, confidence_level, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, specialization, description, confidence_level, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def update_availability(self, agent_name: str, status: str = "available",
                            current_task: str = "", workload_level: int = 0):
        """Update agent availability status"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO agent_availability
            (agent_name, status, current_task, workload_level, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, status, current_task, workload_level, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def find_agents_by_capability(
            self,
            capability: str,
            min_level: int = 5) -> List[Dict]:
        """Find agents with a specific capability above minimum level"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT ac.agent_name, ac.proficiency_level, ac.description, aa.status, aa.workload_level
            FROM agent_capabilities ac
            LEFT JOIN agent_availability aa ON ac.agent_name = aa.agent_name
            WHERE ac.capability = ? AND ac.proficiency_level >= ?
            ORDER BY ac.proficiency_level DESC
        """, (capability, min_level))

        agents = []
        for row in cursor.fetchall():
            agents.append({
                'agent_name': row[0],
                'proficiency_level': row[1],
                'description': row[2],
                'status': row[3] or 'unknown',
                'workload_level': row[4] or 0
            })

        conn.close()
        return agents

    def find_agents_by_specialization(
            self,
            specialization: str,
            min_confidence: int = 6) -> List[Dict]:
        """Find agents with a specific specialization above minimum confidence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT asp.agent_name, asp.confidence_level, asp.description, aa.status, aa.workload_level
            FROM agent_specializations asp
            LEFT JOIN agent_availability aa ON asp.agent_name = aa.agent_name
            WHERE asp.specialization = ? AND asp.confidence_level >= ?
            ORDER BY asp.confidence_level DESC
        """, (specialization, min_confidence))

        agents = []
        for row in cursor.fetchall():
            agents.append({
                'agent_name': row[0],
                'confidence_level': row[1],
                'description': row[2],
                'status': row[3] or 'unknown',
                'workload_level': row[4] or 0
            })

        conn.close()
        return agents

    def get_agent_profile(self, agent_name: str) -> Dict:
        """Get complete profile for an agent"""
        conn = sqlite3.connect(self.db_path)

        # Get capabilities
        cursor = conn.execute("""
            SELECT capability, proficiency_level, description
            FROM agent_capabilities
            WHERE agent_name = ?
            ORDER BY proficiency_level DESC
        """, (agent_name,))

        capabilities = []
        for row in cursor.fetchall():
            capabilities.append({
                'capability': row[0],
                'proficiency_level': row[1],
                'description': row[2]
            })

        # Get specializations
        cursor = conn.execute("""
            SELECT specialization, confidence_level, description
            FROM agent_specializations
            WHERE agent_name = ?
            ORDER BY confidence_level DESC
        """, (agent_name,))

        specializations = []
        for row in cursor.fetchall():
            specializations.append({
                'specialization': row[0],
                'confidence_level': row[1],
                'description': row[2]
            })

        # Get availability
        cursor = conn.execute("""
            SELECT status, current_task, workload_level, last_updated
            FROM agent_availability
            WHERE agent_name = ?
        """, (agent_name,))

        availability = cursor.fetchone()
        availability_info = {
            'status': availability[0] if availability else 'unknown',
            'current_task': availability[1] if availability else '',
            'workload_level': availability[2] if availability else 0,
            'last_updated': availability[3] if availability else ''
        }

        conn.close()

        return {
            'agent_name': agent_name,
            'capabilities': capabilities,
            'specializations': specializations,
            'availability': availability_info
        }

    def get_all_agents(self) -> List[str]:
        """Get list of all known agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT DISTINCT agent_name FROM agent_capabilities
            UNION
            SELECT DISTINCT agent_name FROM agent_specializations
            ORDER BY agent_name
        """)

        agents = [row[0] for row in cursor.fetchall()]
        conn.close()
        return agents

    def recommend_agent_for_task(
            self,
            task_description: str,
            task_type: str = "") -> List[Dict]:
        """Recommend best agents for a given task"""
        # Simple keyword matching for now - could be enhanced with ML
        task_lower = task_description.lower()

        # Define task keywords to capability/specialization mapping
        task_mappings = {
            'documentation': ['technical_writing', 'api_documentation'],
            'testing': ['testing', 'quality_assurance', 'automated_testing'],
            'integration': ['system_integration', 'api_development'],
            'security': ['security_analysis', 'security_frameworks'],
            'monitoring': ['system_monitoring', 'monitoring_systems'],
            'api': ['api_development', 'api_documentation', 'api_gateway'],
            'auth': ['authentication_systems', 'auth_middleware'],
            'coordination': ['multi_agent_coordination', 'project_management'],
            'quality': ['quality_gates', 'code_review', 'quality_assurance'],
            'performance': ['performance_testing', 'optimization'],
            'conflict': ['conflict_resolution'],
            'pr': ['pr_management', 'code_review']
        }

        relevant_skills = set()
        for keyword, skills in task_mappings.items():
            if keyword in task_lower:
                relevant_skills.update(skills)

        if not relevant_skills:
            # Default to project management if no specific skills identified
            relevant_skills = {'project_management', 'communication'}

        # Find agents with relevant capabilities
        recommendations = []
        for skill in relevant_skills:
            agents = self.find_agents_by_capability(skill, min_level=6)
            for agent in agents:
                agent['matched_skill'] = skill
                agent['skill_type'] = 'capability'
                recommendations.append(agent)

            # Also check specializations
            agents = self.find_agents_by_specialization(
                skill, min_confidence=6)
            for agent in agents:
                agent['matched_skill'] = skill
                agent['skill_type'] = 'specialization'
                recommendations.append(agent)

        # Remove duplicates and sort by skill level
        seen_agents = set()
        unique_recommendations = []
        for rec in sorted(
                recommendations,
                key=lambda x: x.get(
                    'proficiency_level',
                    0) +
                x.get(
                    'confidence_level',
                    0),
                reverse=True):
            if rec['agent_name'] not in seen_agents:
                unique_recommendations.append(rec)
                seen_agents.add(rec['agent_name'])

        return unique_recommendations[:5]  # Top 5 recommendations

    def print_agent_profile(self, agent_name: str):
        """Print formatted agent profile"""
        profile = self.get_agent_profile(agent_name)

        print(f"🤖 AGENT PROFILE: {agent_name}")
        print("=" * 50)

        # Availability
        availability = profile['availability']
        status = availability['status']
        status_emoji = {
            'available': '✅',
            'busy': '🔶',
            'offline': '🔴',
            'unknown': '❓'
        }.get(status, '❓')

        print(f"📊 STATUS: {status_emoji} {status.upper()}")
        if availability['current_task']:
            print(f"🎯 CURRENT TASK: {availability['current_task']}")
        print(f"📈 WORKLOAD: {availability['workload_level']}/10")
        print()

        # Capabilities
        print("🛠️  CAPABILITIES:")
        for cap in profile['capabilities']:
            level = cap['proficiency_level']
            level_bar = "█" * level + "░" * (10 - level)
            print(f"  {cap['capability']}: {level_bar} ({level}/10)")
            if cap['description']:
                print(f"    └─ {cap['description']}")
        print()

        # Specializations
        print("🎯 SPECIALIZATIONS:")
        for spec in profile['specializations']:
            confidence = spec['confidence_level']
            confidence_bar = "█" * confidence + "░" * (10 - confidence)
            print(
                f"  {
                    spec['specialization']}: {confidence_bar} ({confidence}/10)")
            if spec['description']:
                print(f"    └─ {spec['description']}")


def main():
    """Main CLI interface"""
    import sys

    registry = AgentCapabilityRegistry()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python agent_capabilities.py --list")
        print("  python agent_capabilities.py --agent <agent-name>")
        print(
            "  python agent_capabilities.py --find-capability <capability> [--min-level 5]")
        print(
            "  python agent_capabilities.py --find-specialization <specialization> [--min-confidence 6]")
        print("  python agent_capabilities.py --recommend '<task description>'")
        print(
            "  python agent_capabilities.py --update-status <agent-name> <status> [task] [workload]")
        return

    command = sys.argv[1]

    if command == "--list":
        agents = registry.get_all_agents()
        print(f"🤖 KNOWN AGENTS ({len(agents)}):")
        print("=" * 30)
        for agent in agents:
            profile = registry.get_agent_profile(agent)
            status = profile['availability']['status']
            workload = profile['availability']['workload_level']

            status_emoji = {
                'available': '✅',
                'busy': '🔶',
                'offline': '🔴',
                'unknown': '❓'
            }.get(status, '❓')

            print(
                f"  {status_emoji} {agent} - {status} (workload: {workload}/10)")

    elif command == "--agent" and len(sys.argv) > 2:
        agent_name = sys.argv[2]
        registry.print_agent_profile(agent_name)

    elif command == "--find-capability" and len(sys.argv) > 2:
        capability = sys.argv[2]
        min_level = 5
        if "--min-level" in sys.argv:
            min_level = int(sys.argv[sys.argv.index("--min-level") + 1])

        agents = registry.find_agents_by_capability(capability, min_level)
        print(f"🔍 AGENTS WITH CAPABILITY: {capability} (≥{min_level})")
        print("=" * 60)

        for agent in agents:
            print(
                f"  {agent['agent_name']}: {agent['proficiency_level']}/10 ({agent['status']})")
            if agent['description']:
                print(f"    └─ {agent['description']}")

    elif command == "--recommend" and len(sys.argv) > 2:
        task_description = sys.argv[2]
        recommendations = registry.recommend_agent_for_task(task_description)

        print(f"💡 RECOMMENDATIONS FOR: '{task_description}'")
        print("=" * 60)

        for i, rec in enumerate(recommendations, 1):
            skill_level = rec.get('proficiency_level',
                                  rec.get('confidence_level', 0))
            print(
                f"  {i}. {rec['agent_name']} - {rec['matched_skill']} ({skill_level}/10)")
            print(
                f"     Status: {
                    rec['status']} | Workload: {
                    rec['workload_level']}/10")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
