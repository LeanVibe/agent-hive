"""
Multi-language client library generators for Service Discovery API.

Generates client libraries in various programming languages for easy
integration with the Service Discovery system.
"""

import logging
from typing import Dict, Any, List
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class ClientLibraryGenerator(ABC):
    """Base class for client library generators."""

    @abstractmethod
    def generate_client(self, api_endpoint: str, service_name: str) -> str:
        """
        Generate client library code.

        Args:
            api_endpoint: Service Discovery API endpoint
            service_name: Target service name for the client

        Returns:
            Generated client code
        """
        pass


class PythonClientGenerator(ClientLibraryGenerator):
    """Python client library generator."""

    def generate_client(self, api_endpoint: str, service_name: str) -> str:
        """Generate Python client library."""

        template = '''"""
Auto-generated Python client for {service_name} service.
Generated for Service Discovery API at {api_endpoint}
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """Service instance information."""
    service_id: str
    service_name: str
    host: str
    port: int
    metadata: Dict[str, Any]
    health_check_url: Optional[str] = None
    tags: List[str] = None
    version: str = "1.0.0"


class {service_name_class}Client:
    """
    Auto-generated client for {service_name} service discovery.
    """

    def __init__(self, discovery_api_endpoint: str = "{api_endpoint}"):
        """
        Initialize client.

        Args:
            discovery_api_endpoint: Service Discovery API endpoint
        """
        self.discovery_api_endpoint = discovery_api_endpoint.rstrip('/')
        self.service_name = "{service_name}"

    async def discover_instances(self, healthy_only: bool = True) -> List[ServiceInstance]:
        """
        Discover available service instances.

        Args:
            healthy_only: Only return healthy instances

        Returns:
            List of service instances
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{{self.discovery_api_endpoint}}/services/discover/{{self.service_name}}"
                params = {{"healthy_only": healthy_only}}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        instances = []

                        for service_data in data.get("services", []):
                            instances.append(ServiceInstance(
                                service_id=service_data["service_id"],
                                service_name=service_data["service_name"],
                                host=service_data["host"],
                                port=service_data["port"],
                                metadata=service_data["metadata"],
                                health_check_url=service_data.get("health_check_url"),
                                tags=service_data.get("tags", []),
                                version=service_data.get("version", "1.0.0")
                            ))

                        logger.info(f"Discovered {{len(instances)}} instances of {{self.service_name}}")
                        return instances
                    else:
                        logger.error(f"Failed to discover services: HTTP {{response.status}}")
                        return []

        except Exception as e:
            logger.error(f"Error discovering {{self.service_name}} instances: {{e}}")
            return []

    async def get_healthy_instance(self) -> Optional[ServiceInstance]:
        """
        Get a healthy service instance.

        Returns:
            Healthy service instance or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{{self.discovery_api_endpoint}}/services/healthy/{{self.service_name}}"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return ServiceInstance(
                            service_id=data["service_id"],
                            service_name=data["service_name"],
                            host=data["host"],
                            port=data["port"],
                            metadata=data["metadata"],
                            health_check_url=data.get("health_check_url"),
                            tags=data.get("tags", []),
                            version=data.get("version", "1.0.0")
                        )
                    elif response.status == 404:
                        logger.warning(f"No healthy instances found for {{self.service_name}}")
                        return None
                    else:
                        logger.error(f"Failed to get healthy instance: HTTP {{response.status}}")
                        return None

        except Exception as e:
            logger.error(f"Error getting healthy {{self.service_name}} instance: {{e}}")
            return None

    async def register_instance(self, instance: ServiceInstance) -> bool:
        """
        Register a service instance.

        Args:
            instance: Service instance to register

        Returns:
            True if registration successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{{self.discovery_api_endpoint}}/services/register"

                data = {{
                    "service_id": instance.service_id,
                    "service_name": instance.service_name,
                    "host": instance.host,
                    "port": instance.port,
                    "metadata": instance.metadata,
                    "health_check_url": instance.health_check_url,
                    "tags": instance.tags or [],
                    "version": instance.version
                }}

                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Successfully registered {{instance.service_id}}")
                        return True
                    else:
                        logger.error(f"Failed to register service: HTTP {{response.status}}")
                        return False

        except Exception as e:
            logger.error(f"Error registering {{instance.service_id}}: {{e}}")
            return False

    async def deregister_instance(self, service_id: str) -> bool:
        """
        Deregister a service instance.

        Args:
            service_id: Service ID to deregister

        Returns:
            True if deregistration successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{{self.discovery_api_endpoint}}/services/{{service_id}}"

                async with session.delete(url) as response:
                    if response.status == 200:
                        logger.info(f"Successfully deregistered {{service_id}}")
                        return True
                    elif response.status == 404:
                        logger.warning(f"Service {{service_id}} not found for deregistration")
                        return False
                    else:
                        logger.error(f"Failed to deregister service: HTTP {{response.status}}")
                        return False

        except Exception as e:
            logger.error(f"Error deregistering {{service_id}}: {{e}}")
            return False

    async def send_heartbeat(self, service_id: str) -> bool:
        """
        Send heartbeat for a service instance.

        Args:
            service_id: Service ID to send heartbeat for

        Returns:
            True if heartbeat successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{{self.discovery_api_endpoint}}/services/{{service_id}}/heartbeat"

                async with session.post(url) as response:
                    if response.status == 200:
                        logger.debug(f"Heartbeat sent for {{service_id}}")
                        return True
                    elif response.status == 404:
                        logger.warning(f"Service {{service_id}} not found for heartbeat")
                        return False
                    else:
                        logger.error(f"Failed to send heartbeat: HTTP {{response.status}}")
                        return False

        except Exception as e:
            logger.error(f"Error sending heartbeat for {{service_id}}: {{e}}")
            return False


# Example usage:
async def main():
    client = {service_name_class}Client()

    # Discover healthy instances
    instances = await client.discover_instances()
    print(f"Found {{len(instances)}} healthy instances")

    # Get a specific healthy instance
    instance = await client.get_healthy_instance()
    if instance:
        print(f"Healthy instance: {{instance.host}}:{{instance.port}}")


if __name__ == "__main__":
    asyncio.run(main())
'''

        service_name_class = ''.join(word.capitalize() for word in service_name.replace('-', '_').split('_'))

        return template.format(
            service_name=service_name,
            service_name_class=service_name_class,
            api_endpoint=api_endpoint
        )


class JavaScriptClientGenerator(ClientLibraryGenerator):
    """JavaScript/Node.js client library generator."""

    def generate_client(self, api_endpoint: str, service_name: str) -> str:
        """Generate JavaScript client library."""

        template = '''/**
 * Auto-generated JavaScript client for {service_name} service.
 * Generated for Service Discovery API at {api_endpoint}
 */

const axios = require('axios');

class ServiceInstance {{
    constructor(data) {{
        this.serviceId = data.service_id;
        this.serviceName = data.service_name;
        this.host = data.host;
        this.port = data.port;
        this.metadata = data.metadata || {{}};
        this.healthCheckUrl = data.health_check_url;
        this.tags = data.tags || [];
        this.version = data.version || '1.0.0';
    }}
}}

class {service_name_class}Client {{
    /**
     * Initialize client.
     * @param {{string}} discoveryApiEndpoint - Service Discovery API endpoint
     */
    constructor(discoveryApiEndpoint = '{api_endpoint}') {{
        this.discoveryApiEndpoint = discoveryApiEndpoint.replace(/\\/$/, '');
        this.serviceName = '{service_name}';
        this.httpClient = axios.create({{
            timeout: 10000,
            headers: {{
                'Content-Type': 'application/json'
            }}
        }});
    }}

    /**
     * Discover available service instances.
     * @param {{boolean}} healthyOnly - Only return healthy instances
     * @returns {{Promise<ServiceInstance[]>}} List of service instances
     */
    async discoverInstances(healthyOnly = true) {{
        try {{
            const response = await this.httpClient.get(
                `${{this.discoveryApiEndpoint}}/services/discover/${{this.serviceName}}`,
                {{ params: {{ healthy_only: healthyOnly }} }}
            );

            if (response.status === 200) {{
                const instances = response.data.services.map(data => new ServiceInstance(data));
                console.log(`Discovered ${{instances.length}} instances of ${{this.serviceName}}`);
                return instances;
            }} else {{
                console.error(`Failed to discover services: HTTP ${{response.status}}`);
                return [];
            }}
        }} catch (error) {{
            console.error(`Error discovering ${{this.serviceName}} instances:`, error.message);
            return [];
        }}
    }}

    /**
     * Get a healthy service instance.
     * @returns {{Promise<ServiceInstance|null>}} Healthy service instance or null
     */
    async getHealthyInstance() {{
        try {{
            const response = await this.httpClient.get(
                `${{this.discoveryApiEndpoint}}/services/healthy/${{this.serviceName}}`
            );

            if (response.status === 200) {{
                return new ServiceInstance(response.data);
            }} else if (response.status === 404) {{
                console.warn(`No healthy instances found for ${{this.serviceName}}`);
                return null;
            }} else {{
                console.error(`Failed to get healthy instance: HTTP ${{response.status}}`);
                return null;
            }}
        }} catch (error) {{
            if (error.response?.status === 404) {{
                console.warn(`No healthy instances found for ${{this.serviceName}}`);
                return null;
            }}
            console.error(`Error getting healthy ${{this.serviceName}} instance:`, error.message);
            return null;
        }}
    }}

    /**
     * Register a service instance.
     * @param {{ServiceInstance}} instance - Service instance to register
     * @returns {{Promise<boolean>}} True if registration successful
     */
    async registerInstance(instance) {{
        try {{
            const data = {{
                service_id: instance.serviceId,
                service_name: instance.serviceName,
                host: instance.host,
                port: instance.port,
                metadata: instance.metadata,
                health_check_url: instance.healthCheckUrl,
                tags: instance.tags,
                version: instance.version
            }};

            const response = await this.httpClient.post(
                `${{this.discoveryApiEndpoint}}/services/register`,
                data
            );

            if (response.status === 200) {{
                console.log(`Successfully registered ${{instance.serviceId}}`);
                return true;
            }} else {{
                console.error(`Failed to register service: HTTP ${{response.status}}`);
                return false;
            }}
        }} catch (error) {{
            console.error(`Error registering ${{instance.serviceId}}:`, error.message);
            return false;
        }}
    }}

    /**
     * Deregister a service instance.
     * @param {{string}} serviceId - Service ID to deregister
     * @returns {{Promise<boolean>}} True if deregistration successful
     */
    async deregisterInstance(serviceId) {{
        try {{
            const response = await this.httpClient.delete(
                `${{this.discoveryApiEndpoint}}/services/${{serviceId}}`
            );

            if (response.status === 200) {{
                console.log(`Successfully deregistered ${{serviceId}}`);
                return true;
            }} else if (response.status === 404) {{
                console.warn(`Service ${{serviceId}} not found for deregistration`);
                return false;
            }} else {{
                console.error(`Failed to deregister service: HTTP ${{response.status}}`);
                return false;
            }}
        }} catch (error) {{
            if (error.response?.status === 404) {{
                console.warn(`Service ${{serviceId}} not found for deregistration`);
                return false;
            }}
            console.error(`Error deregistering ${{serviceId}}:`, error.message);
            return false;
        }}
    }}

    /**
     * Send heartbeat for a service instance.
     * @param {{string}} serviceId - Service ID to send heartbeat for
     * @returns {{Promise<boolean>}} True if heartbeat successful
     */
    async sendHeartbeat(serviceId) {{
        try {{
            const response = await this.httpClient.post(
                `${{this.discoveryApiEndpoint}}/services/${{serviceId}}/heartbeat`
            );

            if (response.status === 200) {{
                console.debug(`Heartbeat sent for ${{serviceId}}`);
                return true;
            }} else if (response.status === 404) {{
                console.warn(`Service ${{serviceId}} not found for heartbeat`);
                return false;
            }} else {{
                console.error(`Failed to send heartbeat: HTTP ${{response.status}}`);
                return false;
            }}
        }} catch (error) {{
            if (error.response?.status === 404) {{
                console.warn(`Service ${{serviceId}} not found for heartbeat`);
                return false;
            }}
            console.error(`Error sending heartbeat for ${{serviceId}}:`, error.message);
            return false;
        }}
    }}
}}

module.exports = {{ {service_name_class}Client, ServiceInstance }};

// Example usage:
// const {{ {service_name_class}Client }} = require('./path/to/this/file');
//
// async function main() {{
//     const client = new {service_name_class}Client();
//
//     // Discover healthy instances
//     const instances = await client.discoverInstances();
//     console.log(`Found ${{instances.length}} healthy instances`);
//
//     // Get a specific healthy instance
//     const instance = await client.getHealthyInstance();
//     if (instance) {{
//         console.log(`Healthy instance: ${{instance.host}}:${{instance.port}}`);
//     }}
// }}
'''

        service_name_class = ''.join(word.capitalize() for word in service_name.replace('-', '_').split('_'))

        return template.format(
            service_name=service_name,
            service_name_class=service_name_class,
            api_endpoint=api_endpoint
        )


class ClientLibraryFactory:
    """Factory for creating client library generators."""

    _generators = {
        'python': PythonClientGenerator,
        'javascript': JavaScriptClientGenerator,
        'js': JavaScriptClientGenerator,
        'node': JavaScriptClientGenerator,
    }

    @classmethod
    def get_generator(cls, language: str) -> ClientLibraryGenerator:
        """
        Get client library generator for specified language.

        Args:
            language: Programming language (python, javascript, js, node)

        Returns:
            Client library generator instance

        Raises:
            ValueError: If language is not supported
        """
        language = language.lower()
        if language not in cls._generators:
            supported = ', '.join(cls._generators.keys())
            raise ValueError(f"Unsupported language: {language}. Supported: {supported}")

        return cls._generators[language]()

    @classmethod
    def generate_client_library(cls, language: str, api_endpoint: str, service_name: str) -> str:
        """
        Generate client library for specified language.

        Args:
            language: Programming language
            api_endpoint: Service Discovery API endpoint
            service_name: Target service name

        Returns:
            Generated client library code
        """
        generator = cls.get_generator(language)
        return generator.generate_client(api_endpoint, service_name)

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Get list of supported programming languages."""
        return list(cls._generators.keys())


# Convenience functions
def generate_python_client(api_endpoint: str, service_name: str) -> str:
    """Generate Python client library."""
    return ClientLibraryFactory.generate_client_library('python', api_endpoint, service_name)


def generate_javascript_client(api_endpoint: str, service_name: str) -> str:
    """Generate JavaScript client library."""
    return ClientLibraryFactory.generate_client_library('javascript', api_endpoint, service_name)


def save_client_library(language: str, api_endpoint: str, service_name: str, output_path: str) -> bool:
    """
    Generate and save client library to file.

    Args:
        language: Programming language
        api_endpoint: Service Discovery API endpoint
        service_name: Target service name
        output_path: File path to save the client library

    Returns:
        True if successful, False otherwise
    """
    try:
        client_code = ClientLibraryFactory.generate_client_library(language, api_endpoint, service_name)

        with open(output_path, 'w') as f:
            f.write(client_code)

        logger.info(f"Generated {language} client library for {service_name} at {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate {language} client library: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    api_endpoint = "http://localhost:8000"
    service_name = "user-service"

    # Generate Python client
    python_client = generate_python_client(api_endpoint, service_name)
    print("=== Python Client ===")
    print(python_client[:500] + "...")

    # Generate JavaScript client
    js_client = generate_javascript_client(api_endpoint, service_name)
    print("\n=== JavaScript Client ===")
    print(js_client[:500] + "...")

    # Show supported languages
    print(f"\nSupported languages: {ClientLibraryFactory.get_supported_languages()}")
