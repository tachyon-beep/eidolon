"""
Specialist Agent Framework - Phase 7

A pluggable system for domain-specific specialist agents that can be invoked
for specialized tasks requiring expert knowledge.

Unlike decomposers (which break down work) and linting agents (which fix code),
specialist agents provide EXPERT DOMAIN KNOWLEDGE for specific areas:

- Security Engineer: Security audits, vulnerability scanning, threat modeling
- Test Engineer: Test generation, coverage analysis, test strategies
- PyTorch Engineer: ML model design, training, optimization
- UX Specialist: UI/UX design, accessibility, user flows
- Data Specialist: Data pipelines, ETL, validation, schema design
- Integration Specialist: API integrations, webhooks, third-party services
- Diagnostic Specialist: Debugging, profiling, performance analysis
- Deployment Specialist: Docker, Kubernetes, Terraform, CI/CD
- Frontend Specialist: React/Vue/HTML/CSS/JS, responsive design
- Database Specialist: Schema design, query optimization, migrations
- API Specialist: REST/GraphQL design, API documentation, versioning

Each specialist can:
1. Analyze code/requirements in their domain
2. Provide expert recommendations
3. Generate domain-specific artifacts
4. Validate against best practices
5. Fix domain-specific issues

Integration points:
- Post-generation (review generated code)
- Pre-generation (provide expert guidance)
- On-demand (called by other agents)
"""

from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

from llm_providers import LLMProvider
from logging_config import get_logger

logger = get_logger(__name__)


class SpecialistDomain(Enum):
    """Domains that specialists can cover"""
    SECURITY = "security"
    TESTING = "testing"
    MACHINE_LEARNING = "machine_learning"
    UX_DESIGN = "ux_design"
    DATA_ENGINEERING = "data_engineering"
    INTEGRATION = "integration"
    DIAGNOSTICS = "diagnostics"
    DEPLOYMENT = "deployment"
    FRONTEND = "frontend"
    DATABASE = "database"
    API_DESIGN = "api_design"
    PERFORMANCE = "performance"


@dataclass
class SpecialistRecommendation:
    """A recommendation from a specialist"""
    domain: SpecialistDomain
    severity: str  # "critical", "high", "medium", "low", "info"
    title: str
    description: str
    code_location: Optional[str] = None
    suggested_fix: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class SpecialistReport:
    """Report from a specialist agent"""
    specialist_type: str
    domain: SpecialistDomain
    success: bool

    # Analysis results
    recommendations: List[SpecialistRecommendation] = field(default_factory=list)
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0

    # Artifacts generated
    artifacts: Dict[str, Any] = field(default_factory=dict)

    # Summary
    summary: str = ""
    overall_score: Optional[float] = None  # 0-100


class SpecialistAgent(ABC):
    """
    Base class for all specialist agents

    Each specialist provides expert analysis in their domain
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        domain: SpecialistDomain
    ):
        self.llm_provider = llm_provider
        self.domain = domain

    @abstractmethod
    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """
        Analyze code/requirements in specialist domain

        Args:
            code: Code to analyze (or requirements/specs)
            context: Additional context

        Returns:
            SpecialistReport with findings and recommendations
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this specialist provides"""
        pass


class SecurityEngineer(SpecialistAgent):
    """
    Security specialist for vulnerability analysis and security best practices

    Checks for:
    - SQL injection vulnerabilities
    - XSS vulnerabilities
    - Authentication/authorization issues
    - Secrets in code
    - Insecure dependencies
    - OWASP Top 10 vulnerabilities
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.SECURITY)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze code for security vulnerabilities"""

        logger.info("security_analysis_started", code_length=len(code))

        report = SpecialistReport(
            specialist_type="SecurityEngineer",
            domain=SpecialistDomain.SECURITY,
            success=False
        )

        # Build security analysis prompt
        system_prompt = """You are a Senior Security Engineer with expertise in application security, penetration testing, and OWASP best practices.

Your mission is to conduct a thorough security audit of the provided code, identifying vulnerabilities and providing actionable remediation guidance.

FOCUS AREAS (OWASP Top 10 2021):
1. **Broken Access Control**
   - Missing authorization checks
   - Insecure direct object references (IDOR)
   - Privilege escalation vulnerabilities

2. **Cryptographic Failures**
   - Hardcoded secrets/API keys
   - Weak hashing algorithms (MD5, SHA1)
   - Missing encryption for sensitive data
   - Insecure random number generation

3. **Injection Vulnerabilities**
   - SQL injection (parameterized queries missing)
   - Command injection (os.system, subprocess with user input)
   - LDAP/NoSQL/ORM injection
   - Server-side template injection

4. **Insecure Design**
   - Missing rate limiting
   - Insufficient input validation
   - Missing security headers
   - Weak password policies

5. **Security Misconfiguration**
   - Debug mode enabled in production
   - Default credentials
   - Unnecessary services enabled
   - Missing security patches

6. **Vulnerable Components**
   - Outdated dependencies
   - Known CVEs in libraries
   - Unmaintained packages

7. **Authentication Failures**
   - Weak password storage (plaintext, weak hashing)
   - Missing MFA
   - Weak session management
   - Missing account lockout

8. **Data Integrity Failures**
   - Missing integrity checks
   - Insecure deserialization
   - Missing digital signatures

9. **Logging & Monitoring**
   - Insufficient logging
   - Logging sensitive data
   - Missing security event detection

10. **Server-Side Request Forgery (SSRF)**
    - Unvalidated URL parameters
    - Missing URL allowlist

SEVERITY LEVELS:
- **critical**: Immediate exploitability, high impact (e.g., SQL injection, hardcoded credentials)
- **high**: Exploitable with effort, significant impact (e.g., weak crypto, missing auth)
- **medium**: Requires specific conditions, moderate impact (e.g., info disclosure)
- **low**: Minor issues, low impact (e.g., verbose error messages)
- **info**: Best practices, improvements (e.g., security headers)

OUTPUT REQUIREMENTS:
- Be specific about location (function name, line context)
- Provide concrete exploit scenarios when relevant
- Reference CWE/CVE numbers if applicable
- Include code examples in suggested fixes
- Prioritize by exploitability and impact"""

        user_prompt = f"""Analyze this code for security vulnerabilities:

```python
{code}
```

Return JSON with:
{{
  "summary": "overall security assessment",
  "overall_score": 85,  // 0-100, higher is better
  "recommendations": [
    {{
      "severity": "critical/high/medium/low/info",
      "title": "brief title",
      "description": "detailed description",
      "code_location": "line or function name",
      "suggested_fix": "how to fix it",
      "references": ["URL1", "URL2"]
    }}
  ]
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2048,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.SECURITY,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        code_location=rec.get("code_location"),
                        suggested_fix=rec.get("suggested_fix"),
                        references=rec.get("references", [])
                    )
                    report.recommendations.append(recommendation)

                    # Count by severity
                    if recommendation.severity == "critical":
                        report.critical_issues += 1
                    elif recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("security_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "security_analysis_complete",
            success=report.success,
            critical=report.critical_issues,
            high=report.high_issues,
            score=report.overall_score
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Vulnerability scanning",
            "OWASP Top 10 analysis",
            "Authentication/Authorization review",
            "Secrets detection",
            "Security best practices",
            "Threat modeling"
        ]


class TestEngineer(SpecialistAgent):
    """
    Testing specialist for test generation and test strategy

    Provides:
    - Unit test generation
    - Integration test suggestions
    - Test coverage analysis
    - Test strategy recommendations
    - Edge case identification
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.TESTING)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze code and generate test recommendations"""

        logger.info("test_analysis_started", code_length=len(code))

        report = SpecialistReport(
            specialist_type="TestEngineer",
            domain=SpecialistDomain.TESTING,
            success=False
        )

        system_prompt = """You are a Senior Test Engineer with expertise in test-driven development (TDD), behavior-driven development (BDD), and quality assurance.

Your mission is to analyze code and design comprehensive testing strategies that ensure reliability, correctness, and maintainability.

TESTING PYRAMID (prioritize in this order):
1. **Unit Tests** (70% of tests)
   - Test individual functions/methods in isolation
   - Fast, deterministic, no external dependencies
   - AAA pattern: Arrange, Act, Assert
   - Mock external dependencies

2. **Integration Tests** (20% of tests)
   - Test interactions between components
   - Database, API, file system integration
   - Test data flow and component contracts

3. **End-to-End Tests** (10% of tests)
   - Test complete user workflows
   - Real environment (or close simulation)
   - Critical happy paths only

ANALYSIS CHECKLIST:
✓ **Test Coverage**
  - Identify untested code paths
  - Calculate cyclomatic complexity
  - Find missing edge cases
  - Check error handling coverage

✓ **Edge Cases & Boundary Conditions**
  - Empty inputs ([], "", None, 0)
  - Null/undefined values
  - Very large inputs (scalability)
  - Negative numbers
  - Type mismatches
  - Concurrent access scenarios

✓ **Error Scenarios**
  - Exception handling
  - Invalid inputs
  - Network failures
  - Database errors
  - Timeout scenarios

✓ **Test Quality**
  - Tests are deterministic (no flakiness)
  - Tests are isolated (no shared state)
  - Tests are fast (<100ms for unit tests)
  - Good test naming (describe behavior)
  - Minimal test data setup

✓ **Mocking Strategy**
  - External APIs (use mocks/stubs)
  - Databases (use in-memory or fixtures)
  - File system (use temp directories)
  - Time-dependent code (mock datetime)
  - Random values (seed random generators)

TESTING FRAMEWORKS (Python):
- pytest: Modern, fixture-based testing
- unittest: Built-in, xUnit style
- hypothesis: Property-based testing
- pytest-cov: Coverage measurement
- pytest-mock: Mocking support
- factory_boy: Test data generation

OUTPUT REQUIREMENTS:
- Provide concrete pytest test examples
- Use descriptive test names (test_should_xxx_when_yyy)
- Include fixtures for test data
- Suggest parametrized tests for similar cases
- Estimate test coverage improvement
- Identify critical paths that MUST be tested"""

        user_prompt = f"""Analyze this code and suggest comprehensive testing strategy:

```python
{code}
```

Return JSON with:
{{
  "summary": "testing strategy overview",
  "overall_score": 75,  // 0-100, current testability
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "test type or concern",
      "description": "what to test and why",
      "suggested_fix": "test code or strategy"
    }}
  ],
  "artifacts": {{
    "unit_tests": "suggested unit test code",
    "edge_cases": ["case 1", "case 2"]
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.TESTING,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                report.success = True

        except Exception as e:
            logger.error("test_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "test_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Unit test generation",
            "Integration test strategy",
            "Edge case identification",
            "Test coverage analysis",
            "Mock/stub recommendations",
            "Test maintainability review"
        ]


class DeploymentSpecialist(SpecialistAgent):
    """
    Deployment specialist for Docker, Kubernetes, Terraform, CI/CD

    Provides:
    - Dockerfile generation
    - Kubernetes manifests
    - Terraform configurations
    - CI/CD pipeline suggestions
    - Deployment best practices
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.DEPLOYMENT)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze deployment requirements and generate configs"""

        logger.info("deployment_analysis_started")

        report = SpecialistReport(
            specialist_type="DeploymentSpecialist",
            domain=SpecialistDomain.DEPLOYMENT,
            success=False
        )

        system_prompt = """You are a Senior DevOps/Platform Engineer with expertise in Docker, Kubernetes, Terraform, CI/CD, and cloud-native architectures.

Your mission is to design robust, scalable, and secure deployment strategies for applications.

CONTAINERIZATION (Docker):
✓ **Dockerfile Best Practices**
  - Use specific base image tags (not :latest)
  - Multi-stage builds for smaller images
  - Minimal base images (alpine, distroless)
  - Non-root user execution
  - .dockerignore to exclude unnecessary files
  - COPY before RUN to leverage layer caching
  - Health checks (HEALTHCHECK instruction)
  - Proper signal handling (ENTRYPOINT vs CMD)

✓ **Container Optimization**
  - Image size < 500MB (< 100MB ideal)
  - Minimize layers (combine RUN commands)
  - Remove package manager caches
  - Use BuildKit for better caching
  - Security scanning (Trivy, Snyk)

ORCHESTRATION (Kubernetes):
✓ **Deployment Manifests**
  - Deployment + Service + Ingress
  - Resource limits and requests (CPU/memory)
  - Liveness and readiness probes
  - Rolling update strategy
  - Pod disruption budgets
  - ConfigMaps for configuration
  - Secrets for sensitive data
  - Horizontal Pod Autoscaling (HPA)

✓ **Production Readiness**
  - Multiple replicas (min 2 for HA)
  - Anti-affinity rules for resilience
  - Network policies for security
  - RBAC for access control
  - Service mesh (Istio/Linkerd) if needed

INFRASTRUCTURE AS CODE (Terraform):
✓ **Terraform Best Practices**
  - Modular structure (modules/)
  - Remote state storage (S3 + DynamoDB)
  - State locking
  - Workspace separation (dev/staging/prod)
  - Variable validation
  - Output values for reuse
  - Provider version pinning

✓ **Cloud Resources**
  - VPC networking setup
  - Load balancers
  - Auto-scaling groups
  - RDS/managed databases
  - S3 buckets with versioning
  - CloudWatch/monitoring

CI/CD PIPELINE:
✓ **Pipeline Stages**
  1. Code checkout
  2. Dependency installation
  3. Linting and static analysis
  4. Unit tests
  5. Build (Docker image)
  6. Integration tests
  7. Security scanning
  8. Push to registry
  9. Deploy to staging
  10. Deploy to production (manual approval)

✓ **Best Practices**
  - Immutable deployments
  - Blue-green or canary deployments
  - Automated rollback on failure
  - Environment parity
  - Secrets management (Vault, AWS Secrets Manager)
  - Build caching for speed

OUTPUT REQUIREMENTS:
- Provide complete Dockerfile (production-ready)
- Include Kubernetes manifests (Deployment, Service, Ingress)
- Suggest Terraform modules if infrastructure needed
- Design CI/CD pipeline (GitHub Actions, GitLab CI, or Jenkins)
- Estimate resource requirements (CPU, memory)
- Include monitoring and observability setup"""

        user_prompt = f"""Analyze this code and suggest deployment strategy:

```python
{code}
```

Context: {context.get('project_type', 'Python application') if context else 'Python application'}

Return JSON with:
{{
  "summary": "deployment strategy overview",
  "overall_score": 80,  // 0-100, deployment readiness
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "deployment concern or suggestion",
      "description": "detailed explanation",
      "suggested_fix": "configuration or code to implement"
    }}
  ],
  "artifacts": {{
    "dockerfile": "suggested Dockerfile content",
    "docker_compose": "docker-compose.yml if needed",
    "k8s_deployment": "Kubernetes deployment YAML if applicable"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.DEPLOYMENT,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("deployment_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "deployment_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Dockerfile generation",
            "Kubernetes manifests",
            "Terraform configurations",
            "CI/CD pipelines",
            "Deployment best practices",
            "Container optimization"
        ]


class FrontendSpecialist(SpecialistAgent):
    """
    Frontend specialist for HTML/CSS/JS, React, Vue, responsive design

    Provides:
    - Frontend code generation
    - Responsive design recommendations
    - Accessibility checks
    - Performance optimization
    - Component architecture
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.FRONTEND)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze frontend requirements"""

        logger.info("frontend_analysis_started")

        report = SpecialistReport(
            specialist_type="FrontendSpecialist",
            domain=SpecialistDomain.FRONTEND,
            success=False
        )

        system_prompt = """You are a Frontend Engineer expert specializing in React, Vue, HTML/CSS/JavaScript, and modern web development.

Analyze the provided code/requirements and provide:
- Component architecture recommendations
- Responsive design strategies
- Accessibility (WCAG) compliance
- Performance optimization
- State management patterns
- UI/UX best practices"""

        user_prompt = f"""Analyze this code/API and suggest frontend implementation:

```python
{code}
```

Context: {context.get('frontend_framework', 'React') if context else 'React'}

Return JSON with:
{{
  "summary": "frontend strategy overview",
  "overall_score": 85,  // 0-100, implementation quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "frontend concern or suggestion",
      "description": "detailed explanation",
      "suggested_fix": "code or pattern to implement"
    }}
  ],
  "artifacts": {{
    "components": "suggested component structure",
    "state_management": "state management approach",
    "api_integration": "how to integrate with backend"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.FRONTEND,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("frontend_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "frontend_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "React/Vue component generation",
            "HTML/CSS/JavaScript",
            "Responsive design",
            "Accessibility (WCAG)",
            "Performance optimization",
            "State management"
        ]


class DatabaseSpecialist(SpecialistAgent):
    """
    Database specialist for schema design, query optimization, migrations

    Provides:
    - Schema design recommendations
    - Query optimization
    - Index strategies
    - Migration planning
    - Database normalization
    - Performance tuning
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.DATABASE)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze database schema and queries"""

        logger.info("database_analysis_started")

        report = SpecialistReport(
            specialist_type="DatabaseSpecialist",
            domain=SpecialistDomain.DATABASE,
            success=False
        )

        system_prompt = """You are a Senior Database Engineer with expertise in relational databases (PostgreSQL, MySQL, SQLite), NoSQL (MongoDB, Redis), and data modeling.

Your mission is to design efficient, scalable, and maintainable database schemas and optimize query performance.

SCHEMA DESIGN PRINCIPLES:
✓ **Normalization (reduce redundancy)**
  - 1NF: Atomic values, no repeating groups
  - 2NF: No partial dependencies
  - 3NF: No transitive dependencies
  - BCNF: Every determinant is a candidate key
  - When to denormalize: Read-heavy workloads, performance critical paths

✓ **Data Types**
  - Use appropriate types (INT vs BIGINT, VARCHAR vs TEXT)
  - Fixed-length for known sizes
  - TIMESTAMP WITH TIME ZONE for datetime
  - ENUM for fixed value sets
  - JSON/JSONB for flexible schemas

✓ **Constraints**
  - PRIMARY KEY on every table
  - FOREIGN KEY for referential integrity
  - UNIQUE constraints for natural keys
  - NOT NULL for required fields
  - CHECK constraints for validation
  - Default values where appropriate

✓ **Naming Conventions**
  - snake_case for tables and columns
  - Singular table names or plural (be consistent)
  - Descriptive names (user_orders not uo)
  - FK columns: table_id (e.g., user_id)

INDEXING STRATEGY:
✓ **When to Index**
  - Primary keys (automatic)
  - Foreign keys (for joins)
  - Columns in WHERE clauses
  - Columns in ORDER BY
  - Columns in GROUP BY
  - Frequently joined columns

✓ **Index Types**
  - B-tree: Default, general purpose
  - Hash: Equality comparisons only
  - GiST/GIN: Full-text search, arrays
  - Partial indexes: Index subset of rows
  - Composite indexes: Multiple columns (order matters!)

✓ **Index Anti-patterns**
  - Over-indexing (slows writes, wastes space)
  - Indexing low-cardinality columns (gender, boolean)
  - Not maintaining indexes (VACUUM ANALYZE)

QUERY OPTIMIZATION:
✓ **Performance Checklist**
  - Use EXPLAIN ANALYZE for query plans
  - Avoid SELECT * (specify columns)
  - Use appropriate JOIN types
  - Filter early (WHERE before JOIN)
  - Use LIMIT for pagination
  - Avoid N+1 queries (use JOINs or eager loading)
  - Use CTEs for complex queries
  - Batch inserts/updates

✓ **Anti-patterns to Avoid**
  - Functions in WHERE clause (prevents index use)
  - OR conditions (use UNION or IN)
  - Leading wildcards in LIKE ('%value')
  - Cartesian products (missing JOIN conditions)
  - Implicit type conversions

TRANSACTIONS & CONCURRENCY:
✓ **ACID Properties**
  - Use transactions for multi-statement operations
  - Appropriate isolation levels (READ COMMITTED default)
  - Optimistic vs pessimistic locking
  - Handle deadlocks gracefully

MIGRATIONS:
✓ **Safe Migration Practices**
  - Never drop columns in production (deprecate first)
  - Add columns as NULL, backfill, then NOT NULL
  - Create indexes CONCURRENTLY (PostgreSQL)
  - Test on production-like data volumes
  - Rollback plan for every migration
  - Use tools: Alembic, Flyway, Liquibase

SPECIFIC DATABASE SYSTEMS:
- **PostgreSQL**: Advanced features (JSONB, arrays, CTEs, window functions)
- **MySQL**: InnoDB for ACID, utf8mb4 charset
- **SQLite**: Great for embedded, limited concurrency
- **MongoDB**: Document model, embedded vs referenced
- **Redis**: In-memory, caching layer, pub/sub

OUTPUT REQUIREMENTS:
- Provide CREATE TABLE statements with constraints
- Suggest indexes with reasoning
- Identify N+1 query patterns
- Show optimized queries with EXPLAIN plans
- Estimate storage requirements
- Include migration scripts (up and down)"""

        user_prompt = f"""Analyze this database code and suggest improvements:

```python
{code}
```

Database type: {context.get('database_type', 'PostgreSQL/SQLite') if context else 'PostgreSQL/SQLite'}

Return JSON with:
{{
  "summary": "database analysis overview",
  "overall_score": 80,  // 0-100, schema quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "database concern or optimization",
      "description": "detailed explanation",
      "code_location": "table or query location",
      "suggested_fix": "SQL or schema change"
    }}
  ],
  "artifacts": {{
    "schema_improvements": "suggested schema changes",
    "indexes": "recommended indexes",
    "migrations": "migration strategy"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.DATABASE,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        code_location=rec.get("code_location"),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("database_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "database_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Schema design",
            "Query optimization",
            "Index strategies",
            "Migration planning",
            "Database normalization",
            "Performance tuning"
        ]


class APISpecialist(SpecialistAgent):
    """
    API Design specialist for REST/GraphQL design and documentation

    Provides:
    - API design best practices
    - REST/GraphQL recommendations
    - API documentation
    - Versioning strategies
    - Error handling patterns
    - Authentication/authorization design
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.API_DESIGN)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze API design"""

        logger.info("api_analysis_started")

        report = SpecialistReport(
            specialist_type="APISpecialist",
            domain=SpecialistDomain.API_DESIGN,
            success=False
        )

        system_prompt = """You are a Senior API Architect with expertise in RESTful design, GraphQL, API governance, and developer experience.

Your mission is to design APIs that are intuitive, consistent, scalable, and a joy to use.

REST API DESIGN PRINCIPLES:
✓ **Resource Naming**
  - Use nouns, not verbs (/users, not /getUsers)
  - Plural resources (/users, not /user)
  - Hierarchical relationships (/users/123/orders)
  - Lowercase, hyphen-separated (/user-profiles)
  - Collection vs singular (/users vs /users/123)

✓ **HTTP Methods (Idempotency)**
  - GET: Retrieve (safe, idempotent, cacheable)
  - POST: Create (not idempotent)
  - PUT: Update/replace (idempotent)
  - PATCH: Partial update (not necessarily idempotent)
  - DELETE: Remove (idempotent)
  - OPTIONS: CORS preflight
  - HEAD: Metadata only

✓ **Status Codes (Use Correctly)**
  - 200 OK: Success with body
  - 201 Created: Resource created (return Location header)
  - 204 No Content: Success, no body
  - 400 Bad Request: Client error (validation)
  - 401 Unauthorized: Missing/invalid auth
  - 403 Forbidden: Authenticated but not authorized
  - 404 Not Found: Resource doesn't exist
  - 409 Conflict: Constraint violation
  - 422 Unprocessable Entity: Semantic errors
  - 429 Too Many Requests: Rate limit exceeded
  - 500 Internal Server Error: Server error
  - 503 Service Unavailable: Temporary downtime

✓ **Request/Response Format**
  - JSON as default (application/json)
  - Consistent field naming (snake_case or camelCase)
  - ISO 8601 for dates (2024-01-15T10:30:00Z)
  - Pagination for collections (limit/offset or cursor)
  - Filtering (?status=active&role=admin)
  - Sorting (?sort=-created_at)
  - Field selection (?fields=id,name,email)

✓ **Error Responses (RFC 7807)**
  ```json
  {
    "type": "https://api.example.com/errors/validation",
    "title": "Validation Error",
    "status": 400,
    "detail": "Email field is required",
    "instance": "/users/create",
    "errors": [
      {"field": "email", "message": "Required field missing"}
    ]
  }
  ```

VERSIONING STRATEGIES:
1. **URL versioning**: /v1/users (visible, explicit)
2. **Header versioning**: Accept: application/vnd.api+json; version=1
3. **Query param**: /users?version=1 (not recommended)

API SECURITY:
✓ **Authentication**
  - JWT tokens (short-lived access + refresh tokens)
  - OAuth 2.0 for third-party access
  - API keys for server-to-server
  - Basic auth only over HTTPS

✓ **Authorization**
  - Role-based access control (RBAC)
  - Attribute-based access control (ABAC)
  - Scope-based permissions
  - Resource-level permissions

✓ **Security Headers**
  - CORS (proper origin configuration)
  - Rate limiting (per-user, per-IP)
  - HTTPS only (HSTS header)
  - Content-Security-Policy
  - X-Content-Type-Options: nosniff

DOCUMENTATION (OpenAPI 3.0):
✓ **Must Include**
  - Endpoint descriptions
  - Request/response examples
  - Parameter descriptions and constraints
  - Error response examples
  - Authentication requirements
  - Rate limits
  - Deprecation notices

GRAPHQL (if applicable):
✓ **Schema Design**
  - Nullable vs non-nullable fields
  - Pagination (connections pattern)
  - Mutations return full objects
  - Error handling (errors array + data)
  - N+1 query prevention (DataLoader)

PERFORMANCE & SCALABILITY:
- ETags for caching
- Conditional requests (If-None-Match)
- Compression (gzip, br)
- Async operations (202 + status endpoint)
- Webhooks for long operations
- GraphQL query complexity limits

OUTPUT REQUIREMENTS:
- Provide OpenAPI/Swagger spec excerpt
- Show request/response examples
- Include error handling examples
- Suggest authentication flow
- Design pagination strategy
- Rate limiting recommendations"""

        user_prompt = f"""Analyze this API code and suggest improvements:

```python
{code}
```

API type: {context.get('api_type', 'REST') if context else 'REST'}

Return JSON with:
{{
  "summary": "API design analysis",
  "overall_score": 85,  // 0-100, API design quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "API design issue or improvement",
      "description": "detailed explanation",
      "code_location": "endpoint or schema location",
      "suggested_fix": "improved API design"
    }}
  ],
  "artifacts": {{
    "openapi_spec": "OpenAPI/Swagger spec improvements",
    "versioning_strategy": "API versioning approach",
    "error_responses": "standardized error responses"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.API_DESIGN,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        code_location=rec.get("code_location"),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("api_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "api_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "REST API design",
            "GraphQL schema design",
            "API documentation (OpenAPI/Swagger)",
            "Versioning strategies",
            "Error handling",
            "Authentication/Authorization"
        ]


class DataSpecialist(SpecialistAgent):
    """
    Data Engineering specialist for pipelines, ETL, validation

    Provides:
    - Data pipeline design
    - ETL/ELT recommendations
    - Data validation strategies
    - Schema evolution
    - Data quality checks
    - Stream processing
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.DATA_ENGINEERING)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze data pipelines and processing"""

        logger.info("data_analysis_started")

        report = SpecialistReport(
            specialist_type="DataSpecialist",
            domain=SpecialistDomain.DATA_ENGINEERING,
            success=False
        )

        system_prompt = """You are a Data Engineering expert specializing in data pipelines, ETL, and data quality.

Analyze the provided data code and provide:
- Data pipeline design recommendations
- ETL/ELT optimization
- Data validation strategies
- Schema evolution planning
- Data quality improvements
- Stream processing patterns"""

        user_prompt = f"""Analyze this data processing code and suggest improvements:

```python
{code}
```

Context: {context.get('data_context', 'Data pipeline') if context else 'Data pipeline'}

Return JSON with:
{{
  "summary": "data engineering analysis",
  "overall_score": 80,  // 0-100, pipeline quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "data engineering concern",
      "description": "detailed explanation",
      "suggested_fix": "improved data processing approach"
    }}
  ],
  "artifacts": {{
    "pipeline_design": "suggested pipeline architecture",
    "validation_rules": "data validation logic",
    "error_handling": "data error handling strategy"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.DATA_ENGINEERING,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("data_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "data_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Data pipeline design",
            "ETL/ELT optimization",
            "Data validation",
            "Schema evolution",
            "Data quality checks",
            "Stream processing"
        ]


class IntegrationSpecialist(SpecialistAgent):
    """
    Integration specialist for API integrations, webhooks, third-party services

    Provides:
    - Third-party API integration
    - Webhook design and handling
    - Service mesh patterns
    - Integration error handling
    - Rate limiting strategies
    - Retry/circuit breaker patterns
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.INTEGRATION)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze integration patterns"""

        logger.info("integration_analysis_started")

        report = SpecialistReport(
            specialist_type="IntegrationSpecialist",
            domain=SpecialistDomain.INTEGRATION,
            success=False
        )

        system_prompt = """You are an Integration Specialist expert in API integrations, webhooks, and service architecture.

Analyze the provided integration code and provide:
- Third-party API integration patterns
- Webhook design and security
- Service mesh recommendations
- Error handling and retries
- Rate limiting strategies
- Circuit breaker patterns"""

        user_prompt = f"""Analyze this integration code and suggest improvements:

```python
{code}
```

Integration type: {context.get('integration_type', 'API integration') if context else 'API integration'}

Return JSON with:
{{
  "summary": "integration analysis",
  "overall_score": 85,  // 0-100, integration quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "integration concern",
      "description": "detailed explanation",
      "suggested_fix": "improved integration pattern"
    }}
  ],
  "artifacts": {{
    "error_handling": "error handling strategy",
    "retry_logic": "retry and circuit breaker pattern",
    "webhook_security": "webhook signature verification"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.INTEGRATION,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("integration_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "integration_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Third-party API integration",
            "Webhook design",
            "Service mesh patterns",
            "Error handling",
            "Rate limiting",
            "Circuit breaker patterns"
        ]


class DiagnosticSpecialist(SpecialistAgent):
    """
    Diagnostic specialist for debugging, profiling, performance analysis

    Provides:
    - Debugging strategies
    - Performance profiling
    - Memory leak detection
    - Bottleneck identification
    - Logging recommendations
    - Monitoring setup
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.DIAGNOSTICS)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze code for debugging and profiling"""

        logger.info("diagnostic_analysis_started")

        report = SpecialistReport(
            specialist_type="DiagnosticSpecialist",
            domain=SpecialistDomain.DIAGNOSTICS,
            success=False
        )

        system_prompt = """You are a Diagnostic Specialist expert in debugging, profiling, and performance analysis.

Analyze the provided code and provide:
- Debugging strategy recommendations
- Performance profiling suggestions
- Memory leak detection
- Bottleneck identification
- Logging improvements
- Monitoring and observability"""

        user_prompt = f"""Analyze this code for potential issues and diagnostics:

```python
{code}
```

Context: {context.get('diagnostic_context', 'General analysis') if context else 'General analysis'}

Return JSON with:
{{
  "summary": "diagnostic analysis",
  "overall_score": 80,  // 0-100, code health
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "diagnostic concern",
      "description": "detailed explanation",
      "code_location": "problematic area",
      "suggested_fix": "debugging or profiling approach"
    }}
  ],
  "artifacts": {{
    "logging_strategy": "improved logging approach",
    "profiling_points": "areas to profile",
    "monitoring_metrics": "key metrics to track"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.DIAGNOSTICS,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        code_location=rec.get("code_location"),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("diagnostic_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "diagnostic_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Debugging strategies",
            "Performance profiling",
            "Memory leak detection",
            "Bottleneck identification",
            "Logging recommendations",
            "Monitoring setup"
        ]


class PerformanceSpecialist(SpecialistAgent):
    """
    Performance specialist for optimization and scalability

    Provides:
    - Algorithm optimization
    - Caching strategies
    - Database query optimization
    - Async/parallel processing
    - Memory optimization
    - Scalability recommendations
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.PERFORMANCE)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze performance and optimization opportunities"""

        logger.info("performance_analysis_started")

        report = SpecialistReport(
            specialist_type="PerformanceSpecialist",
            domain=SpecialistDomain.PERFORMANCE,
            success=False
        )

        system_prompt = """You are a Senior Performance Engineer with expertise in profiling, optimization, scalability, and systems performance.

Your mission is to identify performance bottlenecks and design solutions that scale efficiently.

PERFORMANCE ANALYSIS METHODOLOGY:
1. **Measure First** (don't optimize blindly)
   - Profile with real workloads
   - Identify hotspots (Pareto principle: 80/20)
   - Set performance budgets
   - A/B test optimizations

2. **Big-O Complexity** (algorithmic efficiency)
   - O(1): Constant - hash lookups, array access
   - O(log n): Logarithmic - binary search
   - O(n): Linear - single loop
   - O(n log n): Linearithmic - merge sort
   - O(n²): Quadratic - nested loops (AVOID!)
   - O(2ⁿ): Exponential - recursive branching (AVOID!)

OPTIMIZATION TARGETS:
✓ **CPU Optimization**
  - Reduce algorithmic complexity
  - Avoid repeated calculations (memoization)
  - Use efficient data structures
  - Batch operations (list comprehensions vs loops)
  - Avoid premature optimization
  - Profile-guided optimization

✓ **Memory Optimization**
  - Use generators for large datasets (yield vs return)
  - Lazy loading (load when needed)
  - Object pooling for frequent allocations
  - Weak references for caches
  - Stream processing vs loading all into memory
  - Profile memory with memory_profiler

✓ **I/O Optimization**
  - Minimize disk/network I/O
  - Batch database queries (avoid N+1)
  - Connection pooling
  - Async I/O (asyncio, aiohttp)
  - Buffering for file operations
  - CDN for static assets

CACHING STRATEGIES:
✓ **Cache Layers**
  - L1: In-memory (local, fast, small)
  - L2: Distributed cache (Redis, Memcached)
  - L3: Database query cache
  - L4: CDN for static content

✓ **Cache Patterns**
  - Cache-aside (lazy loading)
  - Write-through cache
  - Write-behind cache
  - Refresh-ahead cache

✓ **Cache Invalidation** (hardest problem!)
  - TTL (time-to-live)
  - Event-based invalidation
  - Cache keys with version/hash
  - LRU eviction policy

CONCURRENCY & PARALLELISM:
✓ **Python Concurrency**
  - asyncio: I/O-bound tasks (async/await)
  - threading: I/O-bound with blocking code
  - multiprocessing: CPU-bound tasks (bypass GIL)
  - concurrent.futures: High-level interface

✓ **When to Use**
  - Single-threaded: Simple, CPU-light
  - Async: Many I/O operations (web requests, DB)
  - Multi-threading: I/O with blocking libraries
  - Multi-processing: CPU-intensive (image processing, ML)

DATABASE OPTIMIZATION:
✓ **Query Performance**
  - Use indexes (EXPLAIN ANALYZE)
  - Avoid SELECT * (specify columns)
  - Pagination (LIMIT/OFFSET or cursor)
  - Batch operations (bulk inserts)
  - Connection pooling
  - Read replicas for read-heavy loads

✓ **ORM Optimization**
  - Eager loading (select_related, prefetch_related)
  - Avoid N+1 queries
  - Use raw SQL for complex queries
  - Database-level aggregation

SCALABILITY PATTERNS:
✓ **Vertical Scaling** (scale up)
  - Increase CPU, RAM, disk
  - Limits: Single machine ceiling
  - Simpler but expensive

✓ **Horizontal Scaling** (scale out)
  - Add more servers
  - Load balancing
  - Stateless services
  - Distributed caching
  - Message queues (RabbitMQ, Kafka)

PROFILING TOOLS (Python):
- cProfile: CPU profiling
- line_profiler: Line-by-line profiling
- memory_profiler: Memory usage
- py-spy: Sampling profiler (no code changes)
- scalene: CPU + memory + GPU profiling

PERFORMANCE METRICS:
- Latency: Response time (p50, p95, p99)
- Throughput: Requests per second
- Resource utilization: CPU, memory, I/O
- Scalability: Performance vs load

OPTIMIZATION CHECKLIST:
✓ Algorithmic complexity (Big-O)
✓ Data structure choice (list vs set vs dict)
✓ Caching frequently accessed data
✓ Database query optimization
✓ Async for I/O operations
✓ Batch processing
✓ Connection pooling
✓ Lazy loading
✓ Compression (gzip)
✓ Pagination for large datasets

OUTPUT REQUIREMENTS:
- Identify specific bottlenecks with evidence
- Provide Big-O analysis before/after
- Show concrete code improvements
- Suggest caching strategy with keys
- Estimate performance gains (2x, 10x, etc.)
- Include profiling approach"""

        user_prompt = f"""Analyze this code for performance optimization:

```python
{code}
```

Context: {context.get('performance_context', 'Performance optimization') if context else 'Performance optimization'}

Return JSON with:
{{
  "summary": "performance analysis",
  "overall_score": 75,  // 0-100, current performance
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "performance bottleneck or optimization",
      "description": "detailed explanation",
      "code_location": "specific code location",
      "suggested_fix": "optimized code or approach"
    }}
  ],
  "artifacts": {{
    "caching_strategy": "recommended caching approach",
    "async_opportunities": "areas for async/parallel processing",
    "complexity_analysis": "time/space complexity improvements"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.PERFORMANCE,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        code_location=rec.get("code_location"),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("performance_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "performance_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Algorithm optimization",
            "Caching strategies",
            "Database query optimization",
            "Async/parallel processing",
            "Memory optimization",
            "Scalability recommendations"
        ]


class PyTorchEngineer(SpecialistAgent):
    """
    PyTorch/ML specialist for machine learning model design and optimization

    Provides:
    - Model architecture recommendations
    - Training optimization
    - Hyperparameter tuning suggestions
    - GPU/TPU utilization
    - Model deployment strategies
    - Data pipeline for ML
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.MACHINE_LEARNING)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze ML/PyTorch code"""

        logger.info("ml_analysis_started")

        report = SpecialistReport(
            specialist_type="PyTorchEngineer",
            domain=SpecialistDomain.MACHINE_LEARNING,
            success=False
        )

        system_prompt = """You are a Machine Learning Engineer expert specializing in PyTorch, TensorFlow, and ML systems.

Analyze the provided ML code and provide:
- Model architecture recommendations
- Training optimization strategies
- Hyperparameter tuning suggestions
- GPU/TPU utilization improvements
- Model deployment patterns
- Data pipeline optimization"""

        user_prompt = f"""Analyze this ML code and suggest improvements:

```python
{code}
```

ML framework: {context.get('ml_framework', 'PyTorch') if context else 'PyTorch'}

Return JSON with:
{{
  "summary": "ML analysis",
  "overall_score": 80,  // 0-100, model implementation quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "ML concern or optimization",
      "description": "detailed explanation",
      "suggested_fix": "improved ML approach"
    }}
  ],
  "artifacts": {{
    "model_architecture": "suggested model improvements",
    "training_strategy": "training optimization approach",
    "deployment": "model deployment recommendations"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.MACHINE_LEARNING,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("ml_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "ml_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "Model architecture design",
            "Training optimization",
            "Hyperparameter tuning",
            "GPU/TPU utilization",
            "Model deployment",
            "ML data pipelines"
        ]


class UXSpecialist(SpecialistAgent):
    """
    UX specialist for user experience, accessibility, user flows

    Provides:
    - User experience recommendations
    - Accessibility compliance (WCAG)
    - User flow optimization
    - Interaction design patterns
    - Usability improvements
    - Mobile/responsive UX
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(llm_provider, SpecialistDomain.UX_DESIGN)

    async def analyze(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SpecialistReport:
        """Analyze UX and accessibility"""

        logger.info("ux_analysis_started")

        report = SpecialistReport(
            specialist_type="UXSpecialist",
            domain=SpecialistDomain.UX_DESIGN,
            success=False
        )

        system_prompt = """You are a UX Specialist expert in user experience, accessibility, and interaction design.

Analyze the provided code/design and provide:
- User experience recommendations
- Accessibility compliance (WCAG 2.1)
- User flow optimization
- Interaction design patterns
- Usability improvements
- Mobile/responsive UX"""

        user_prompt = f"""Analyze this UI/UX code and suggest improvements:

```python
{code}
```

UI framework: {context.get('ui_framework', 'Web/React') if context else 'Web/React'}

Return JSON with:
{{
  "summary": "UX analysis",
  "overall_score": 85,  // 0-100, UX quality
  "recommendations": [
    {{
      "severity": "high/medium/low/info",
      "title": "UX concern or improvement",
      "description": "detailed explanation",
      "suggested_fix": "improved UX pattern"
    }}
  ],
  "artifacts": {{
    "user_flows": "optimized user flow diagrams",
    "accessibility": "WCAG compliance improvements",
    "interaction_patterns": "better interaction design"
  }}
}}"""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3072,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result:
                report.summary = result.get("summary", "")
                report.overall_score = result.get("overall_score", 0)
                report.artifacts = result.get("artifacts", {})

                for rec in result.get("recommendations", []):
                    recommendation = SpecialistRecommendation(
                        domain=SpecialistDomain.UX_DESIGN,
                        severity=rec.get("severity", "info"),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        suggested_fix=rec.get("suggested_fix")
                    )
                    report.recommendations.append(recommendation)

                    if recommendation.severity == "high":
                        report.high_issues += 1
                    elif recommendation.severity == "medium":
                        report.medium_issues += 1
                    elif recommendation.severity == "low":
                        report.low_issues += 1

                report.success = True

        except Exception as e:
            logger.error("ux_analysis_failed", error=str(e))
            report.summary = f"Analysis failed: {str(e)}"

        logger.info(
            "ux_analysis_complete",
            success=report.success,
            recommendations=len(report.recommendations)
        )

        return report

    def get_capabilities(self) -> List[str]:
        return [
            "User experience design",
            "Accessibility (WCAG 2.1)",
            "User flow optimization",
            "Interaction design",
            "Usability testing",
            "Mobile/responsive UX"
        ]


class SpecialistRegistry:
    """
    Registry for managing specialist agents

    Allows easy lookup and invocation of specialists by domain
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.specialists: Dict[SpecialistDomain, SpecialistAgent] = {}

    def register(self, specialist: SpecialistAgent):
        """Register a specialist agent"""
        self.specialists[specialist.domain] = specialist
        logger.info("specialist_registered", domain=specialist.domain.value)

    def get_specialist(self, domain: SpecialistDomain) -> Optional[SpecialistAgent]:
        """Get a specialist by domain"""
        return self.specialists.get(domain)

    def get_all_specialists(self) -> List[SpecialistAgent]:
        """Get all registered specialists"""
        return list(self.specialists.values())

    def get_capabilities_map(self) -> Dict[str, List[str]]:
        """Get map of domain -> capabilities"""
        return {
            domain.value: specialist.get_capabilities()
            for domain, specialist in self.specialists.items()
        }


def create_default_registry(llm_provider: LLMProvider) -> SpecialistRegistry:
    """Create registry with default specialists"""

    registry = SpecialistRegistry(llm_provider)

    # Register all default specialists
    registry.register(SecurityEngineer(llm_provider))
    registry.register(TestEngineer(llm_provider))
    registry.register(DeploymentSpecialist(llm_provider))
    registry.register(FrontendSpecialist(llm_provider))
    registry.register(DatabaseSpecialist(llm_provider))
    registry.register(APISpecialist(llm_provider))
    registry.register(DataSpecialist(llm_provider))
    registry.register(IntegrationSpecialist(llm_provider))
    registry.register(DiagnosticSpecialist(llm_provider))
    registry.register(PerformanceSpecialist(llm_provider))
    registry.register(PyTorchEngineer(llm_provider))
    registry.register(UXSpecialist(llm_provider))

    logger.info(
        "specialist_registry_created",
        specialists=len(registry.specialists)
    )

    return registry
