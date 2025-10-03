import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * ContainerMigrationTool.java
 * Java implementation of a Solution Accelerator for Container Migration Readiness.
 * This tool analyzes a simulated application manifest and generates deployment artifacts
 * (Dockerfile and Kubernetes Deployment YAML) if the application is deemed ready.
 */
public class ContainerMigrationTool {

    // Define the target output directory (will be simulated by printing to console)
    private static final String OUTPUT_DIR = "migration_output";

    // --- 1. CONFIGURATION AND ANALYSIS DATA (SIMULATED APPLICATION INPUT) ---
    private static final Map<String, Object> APPLICATION_MANIFEST = createManifest();

    /**
     * Helper to create the complex, nested application manifest data structure.
     */
    private static Map<String, Object> createManifest() {
        Map<String, Object> manifest = new HashMap<>();
        manifest.put("app_name", "inventory-api-v2");
        manifest.put("language", "Python");
        manifest.put("runtime_version", "3.10");
        manifest.put("dependencies", List.of("flask", "psycopg2"));
        manifest.put("required_ports", List.of(8080));

        Map<String, String> persistence = new HashMap<>();
        persistence.put("type", "database");
        persistence.put("details", "PostgreSQL RDS (External)");
        persistence.put("state_storage", "None (Stateless)");
        manifest.put("persistence", persistence);

        Map<String, Object> fsAccess = new HashMap<>();
        fsAccess.put("local_storage_path", "/var/app/temp_files");
        fsAccess.put("hardcoded_config_paths", List.of("/etc/app/config.ini", "/opt/data/certs"));
        fsAccess.put("writes_to_logs", true);
        manifest.put("file_system_access", fsAccess);

        return manifest;
    }

    /**
     * Simple class to return the result of the readiness analysis.
     */
    private static class ReadinessResult {
        final boolean isReady;
        final List<String> issues;

        ReadinessResult(boolean isReady, List<String> issues) {
            this.isReady = isReady;
            this.issues = issues;
        }
    }


    // --- 2. ANALYZER CORE LOGIC ---

    /**
     * Analyzes the application manifest against common containerization best practices.
     */
    private static ReadinessResult analyzeReadiness(Map<String, Object> manifest) {
        List<String> issues = new ArrayList<>();
        boolean isReady = true;
        String appName = (String) manifest.get("app_name");

        System.out.println(String.format("--- Analyzing Application: %s ---", appName));

        // Check for hardcoded paths (MAJOR BLOCKER)
        @SuppressWarnings("unchecked")
        List<String> hardcodedPaths = (List<String>) ((Map<String, Object>) manifest.get("file_system_access")).get("hardcoded_config_paths");
        if (!hardcodedPaths.isEmpty()) {
            issues.add(String.format("Major Issue: Hardcoded file paths found: %s. Must be externalized to environment variables (ConfigMaps/Secrets).", hardcodedPaths));
            isReady = false;
        }

        // Check for non-externalized state (BLOCKER)
        @SuppressWarnings("unchecked")
        String stateStorage = ((Map<String, String>) manifest.get("persistence")).get("state_storage");
        if (stateStorage.toLowerCase().contains("local")) {
            issues.add("Major Issue: Application is not Stateless. It uses local storage for state, which must be externalized (EFS, Volumes, or external DB).");
            isReady = false;
        }

        // Check for proper dependency management (WARNING)
        @SuppressWarnings("unchecked")
        List<String> dependencies = (List<String>) manifest.get("dependencies");
        if (dependencies.isEmpty()) {
            issues.add("Warning: Dependency list is empty. Ensure requirements.txt or equivalent file exists for reproducible build.");
        }

        // Check if necessary ports are defined (WARNING)
        @SuppressWarnings("unchecked")
        List<Integer> requiredPorts = (List<Integer>) manifest.get("required_ports");
        if (requiredPorts.isEmpty()) {
            issues.add("Warning: No required ports defined. Container may not be accessible.");
        }

        if (isReady) {
            System.out.println("\n[SUCCESS] Basic checks passed. Application is a good candidate for automated containerization.");
        } else {
            System.out.println("\n[FAILURE] Critical issues found. Manual remediation is required before container generation.");
        }

        return new ReadinessResult(isReady, issues);
    }


    // --- 3. CONFIGURATION GENERATOR CORE LOGIC ---

    /**
     * Generates a basic Dockerfile template based on the application language.
     */
    private static Map.Entry<String, String> generateDockerfile(Map<String, Object> manifest) {
        String lang = ((String) manifest.get("language")).toLowerCase();
        String version = (String) manifest.get("runtime_version");
        
        @SuppressWarnings("unchecked")
        List<Integer> ports = (List<Integer>) manifest.get("required_ports");
        int port = ports.isEmpty() ? 80 : ports.get(0);
        
        String dockerfileContent;

        if ("python".equals(lang)) {
            dockerfileContent = String.format("""
# Dockerfile generated by Container-Migration-Solution-Accelerator
# Using standard Python slim image for smaller footprint
FROM python:%s-slim

# Set environment variables for non-hardcoded configuration
ENV APP_PORT=%d
ENV APP_ENV=production

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy requirement files and install dependencies first (leverage Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the application port
EXPOSE $APP_PORT

# Command to run the application
CMD ["python", "app.py"]
""", version, port);
        } else if ("node".equals(lang)) {
            dockerfileContent = String.format("""
# Dockerfile generated by Container-Migration-Solution-Accelerator
FROM node:%s-slim
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE %d
CMD ["npm", "start"]
""", version, port);
        } else {
            dockerfileContent = String.format("# Dockerfile: Unknown language '%s'. Manual creation required.", lang);
        }

        return Map.entry("Dockerfile", dockerfileContent);
    }

    /**
     * Generates a basic Kubernetes Deployment YAML.
     */
    private static Map.Entry<String, String> generateK8sDeployment(Map<String, Object> manifest) {
        String appName = (String) manifest.get("app_name");
        
        @SuppressWarnings("unchecked")
        List<Integer> ports = (List<Integer>) manifest.get("required_ports");
        int port = ports.isEmpty() ? 80 : ports.get(0);

        String k8sYamlContent = String.format("""
# Kubernetes Deployment generated by Container-Migration-Solution-Accelerator
apiVersion: apps/v1
kind: Deployment
metadata:
  name: %s-deployment
  labels:
    app: %s
spec:
  replicas: 2 # Start with 2 replicas for high availability
  selector:
    matchLabels:
      app: %s
  template:
    metadata:
      labels:
        app: %s
    spec:
      containers:
      - name: %s-container
        image: your-repo/%s:latest # NOTE: Update with your container registry path
        ports:
        - containerPort: %d
        env: # Example: Externalized configuration via environment variables
        - name: DATABASE_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
        resources: # Best practice: Define resource limits
          limits:
            cpu: "500m"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: %s-service
spec:
  selector:
    app: %s
  ports:
  - protocol: TCP
    port: 80 # Service port
    targetPort: %d # Container port
  type: LoadBalancer # Expose the service externally
""", appName, appName, appName, appName, appName, appName, port, appName, appName, port);
        
        return Map.entry(appName + "-deployment.yaml", k8sYamlContent);
    }

    /**
     * Simulates writing content to a file. In this environment, it prints to the console.
     */
    private static void saveFile(String directory, String filename, String content) {
        System.out.println("\n-------------------------------------------------");
        System.out.println(String.format("File: %s/%s", directory, filename));
        System.out.println("-------------------------------------------------");
        System.out.println(content);
        System.out.println("-------------------------------------------------");

        // In a real application, you would use this logic:
        /*
        try {
            File dir = new File(directory);
            if (!dir.exists()) {
                dir.mkdirs();
            }
            try (FileWriter writer = new FileWriter(new File(dir, filename))) {
                writer.write(content);
                System.out.println(String.format("Successfully generated and saved: %s/%s", directory, filename));
            }
        } catch (IOException e) {
            System.err.println(String.format("Error saving file %s: %s", filename, e.getMessage()));
        }
        */
    }


    // --- 4. MAIN EXECUTION ---

    public static void main(String[] args) {
        
        // 1. ANALYZE APPLICATION
        ReadinessResult result = analyzeReadiness(APPLICATION_MANIFEST);
        
        if (!result.issues.isEmpty()) {
            System.out.println("\n--- Remediation Required ---");
            for (int i = 0; i < result.issues.size(); i++) {
                System.out.println(String.format("[%d] %s", i + 1, result.issues.get(i)));
            }
        }
        
        if (result.isReady) {
            // 2. GENERATE ARTIFACTS
            
            System.out.println("\n--- Generating Container Artifacts ---");
            
            // Generator functions return a Map.Entry of (filename, content)
            List<Map.Entry<String, String>> artifactsToGenerate = List.of(
                generateDockerfile(APPLICATION_MANIFEST),
                generateK8sDeployment(APPLICATION_MANIFEST)
            );
            
            for (Map.Entry<String, String> artifact : artifactsToGenerate) {
                saveFile(OUTPUT_DIR, artifact.getKey(), artifact.getValue());
            }

            // 3. SUMMARY
            System.out.println("\n==================================================================");
            System.out.println(String.format("Migration Accelerator Complete for %s", APPLICATION_MANIFEST.get("app_name")));
            System.out.println(String.format("Review the generated files above (simulated to be in '%s' directory).", OUTPUT_DIR));
            System.out.println("Remember to replace the placeholder image path in the deployment YAML.");
            System.out.println("==================================================================");
        } else {
            System.out.println("\nGeneration halted. Fix the critical issues above and re-run.");
        }
    }
}
