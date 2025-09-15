"""
YAML file generator for RAI testing.
Creates Kubernetes configuration files with embedded harmful content for testing.
"""

import os
import uuid
from typing import Dict, Any, List, Optional
from jinja2 import Template
import yaml

import sys
from pathlib import Path

# Add the parent directory to sys.path to import test_cases
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from test_cases.harmful_content import HarmfulContentCase


class YamlFileGenerator:
    """Generates Kubernetes YAML files with embedded harmful content for testing"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load YAML templates for different Kubernetes resources"""
        
        # Pod template with harmful content injection points
        pod_template = Template("""
apiVersion: v1
kind: Pod
metadata:
  name: {{ pod_name }}
  labels:
    app: {{ app_name }}
    test-case-id: {{ test_case_id }}
  annotations:
    description: "{{ description }}"
    # {{ harmful_content }}
spec:
  containers:
  - name: {{ container_name }}
    image: {{ image }}
    # {{ harmful_content }}
    env:
    - name: APP_PURPOSE  
      value: "{{ harmful_content }}"
    - name: TEST_CONTENT
      value: "{{ encoded_harmful_content }}"
    command:
    - sh
    - -c  
    - |
      echo "Starting container..."
      # {{ harmful_content }}
      sleep 3600
  restartPolicy: Never
""")

        # Deployment template
        deployment_template = Template("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ deployment_name }}
  labels:
    app: {{ app_name }}
    test-case-id: {{ test_case_id }}
  annotations:
    purpose: "{{ harmful_content }}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{ app_name }}
  template:
    metadata:
      labels:
        app: {{ app_name }}
      annotations:
        description: "{{ harmful_content }}"  
    spec:
      containers:
      - name: {{ container_name }}
        image: {{ image }}
        env:
        - name: MALICIOUS_INTENT
          value: "{{ harmful_content }}"
        ports:
        - containerPort: 80
        # Comment: {{ harmful_content }}
""")

        # Service template  
        service_template = Template("""
apiVersion: v1
kind: Service
metadata:
  name: {{ service_name }}
  labels:
    app: {{ app_name }}
    test-case-id: {{ test_case_id }}
  annotations:
    purpose: "{{ harmful_content }}"
spec:
  selector:
    app: {{ app_name }}
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
  # Service purpose: {{ harmful_content }}
""")

        # ConfigMap template
        configmap_template = Template("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ configmap_name }}
  labels:
    app: {{ app_name }}
    test-case-id: {{ test_case_id }}
data:
  config.yaml: |
    # Configuration purpose: {{ harmful_content }}
    app:
      name: {{ app_name }}
      description: "{{ harmful_content }}"
  malicious-script.sh: |
    #!/bin/bash
    # {{ harmful_content }}
    echo "This script contains harmful content for testing"
""")

        # Job template
        job_template = Template("""
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ job_name }}
  labels:
    app: {{ app_name }}
    test-case-id: {{ test_case_id }}
  annotations:
    description: "{{ harmful_content }}"
spec:
  template:
    spec:
      containers:
      - name: {{ container_name }}
        image: {{ image }}
        env:
        - name: JOB_INTENT
          value: "{{ harmful_content }}"
        command:
        - sh
        - -c
        - |
          echo "Job execution with harmful content:"
          echo "{{ harmful_content }}"
          # {{ harmful_content }}
      restartPolicy: Never
  backoffLimit: 1
""")

        return {
            "pod": pod_template,
            "deployment": deployment_template, 
            "service": service_template,
            "configmap": configmap_template,
            "job": job_template
        }
    
    def generate_yaml_file(
        self, 
        test_case: HarmfulContentCase,
        resource_type: str = "pod",
        output_dir: str = None
    ) -> str:
        """Generate a YAML file with harmful content embedded"""
        
        if resource_type not in self.templates:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        
        template = self.templates[resource_type]
        
        # Generate random names for resources
        unique_id = str(uuid.uuid4())[:8]
        app_name = f"rai-test-{test_case.id.lower()}-{unique_id}"
        
        # Prepare template variables
        template_vars = {
            "test_case_id": test_case.id,
            "app_name": app_name,
            "harmful_content": test_case.content,
            "encoded_harmful_content": test_case.content.replace('"', '\\"'),
            "description": test_case.description,
            "image": "busybox:latest",
            "unique_id": unique_id
        }
        
        # Resource-specific variables
        if resource_type == "pod":
            template_vars.update({
                "pod_name": f"{app_name}-pod",
                "container_name": f"{app_name}-container"
            })
        elif resource_type == "deployment":
            template_vars.update({
                "deployment_name": f"{app_name}-deployment", 
                "container_name": f"{app_name}-container"
            })
        elif resource_type == "service":
            template_vars.update({
                "service_name": f"{app_name}-service"
            })
        elif resource_type == "configmap":
            template_vars.update({
                "configmap_name": f"{app_name}-config"
            })
        elif resource_type == "job":
            template_vars.update({
                "job_name": f"{app_name}-job",
                "container_name": f"{app_name}-container"
            })
        
        # Generate YAML content
        yaml_content = template.render(**template_vars)
        
        # Create filename
        filename = f"{test_case.id}-{resource_type}-{unique_id}.yaml"
        
        # Write to file if output directory specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            return filepath
        
        return yaml_content
    
    def generate_multi_resource_file(
        self,
        test_case: HarmfulContentCase, 
        resource_types: List[str],
        output_dir: str = None
    ) -> str:
        """Generate a single YAML file with multiple resources"""
        
        yaml_documents = []
        unique_id = str(uuid.uuid4())[:8]
        app_name = f"rai-test-{test_case.id.lower()}-{unique_id}"
        
        for resource_type in resource_types:
            if resource_type not in self.templates:
                continue
                
            template = self.templates[resource_type]
            
            template_vars = {
                "test_case_id": test_case.id,
                "app_name": app_name,
                "harmful_content": test_case.content,
                "encoded_harmful_content": test_case.content.replace('"', '\\"'),
                "description": test_case.description,
                "image": "busybox:latest",
                "unique_id": unique_id
            }
            
            # Add resource-specific variables
            if resource_type == "pod":
                template_vars.update({
                    "pod_name": f"{app_name}-pod",
                    "container_name": f"{app_name}-container"
                })
            elif resource_type == "deployment":
                template_vars.update({
                    "deployment_name": f"{app_name}-deployment",
                    "container_name": f"{app_name}-container"
                })
            elif resource_type == "service":
                template_vars.update({
                    "service_name": f"{app_name}-service"
                })
            elif resource_type == "configmap":
                template_vars.update({
                    "configmap_name": f"{app_name}-config"
                })
            elif resource_type == "job":
                template_vars.update({
                    "job_name": f"{app_name}-job",
                    "container_name": f"{app_name}-container"
                })
            
            yaml_content = template.render(**template_vars)
            yaml_documents.append(yaml_content)
        
        # Combine all documents with YAML document separator
        combined_yaml = "\n---\n".join(yaml_documents)
        
        # Create filename
        filename = f"{test_case.id}-multi-{unique_id}.yaml"
        
        # Write to file if output directory specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(combined_yaml)
            return filepath
        
        return combined_yaml
    
    def validate_yaml_syntax(self, yaml_content: str) -> bool:
        """Validate that generated YAML has correct syntax"""
        try:
            # Try to parse all YAML documents
            yaml_docs = yaml.safe_load_all(yaml_content)
            for doc in yaml_docs:
                if doc is None:
                    continue
                # Basic validation - check for required Kubernetes fields
                if not isinstance(doc, dict):
                    return False
                if "apiVersion" not in doc or "kind" not in doc:
                    return False
            return True
        except yaml.YAMLError:
            return False
    
    def get_available_resource_types(self) -> List[str]:
        """Get list of available resource types for generation"""
        return list(self.templates.keys())
    
    def create_test_file_set(
        self,
        test_cases: List[HarmfulContentCase],
        output_dir: str,
        resource_types: Optional[List[str]] = None
    ) -> List[str]:
        """Create a complete set of test files for multiple test cases"""
        
        if resource_types is None:
            resource_types = ["pod", "deployment", "service"]
        
        created_files = []
        
        for test_case in test_cases:
            for resource_type in resource_types:
                try:
                    filepath = self.generate_yaml_file(
                        test_case=test_case,
                        resource_type=resource_type,
                        output_dir=output_dir
                    )
                    created_files.append(filepath)
                except Exception as e:
                    print(f"Error creating {resource_type} file for {test_case.id}: {e}")
        
        return created_files
