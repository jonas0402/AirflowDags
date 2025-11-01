# Contributing to TransferMkt Airflow DAG

Thank you for your interest in contributing to the TransferMkt Airflow DAG project! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Commit Messages](#commit-messages)
7. [Pull Request Process](#pull-request-process)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Collaborate openly and transparently
- Maintain professional communication

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Apache Airflow installed (version 2.0+)
- Docker installed and running
- Python 3.8+ installed
- Git for version control
- Access to required AWS and Slack credentials (for testing)

### Setting Up Development Environment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AirflowDags
   ```

2. **Set up Airflow**
   ```bash
   export AIRFLOW_HOME=~/airflow
   airflow db init
   ```

3. **Install required providers**
   ```bash
   pip install apache-airflow-providers-docker
   pip install apache-airflow-providers-slack
   ```

4. **Configure test connections**
   ```bash
   # Set up test connections (see CONFIGURATION.md)
   airflow connections add aws_default --conn-type aws --conn-login test --conn-password test
   airflow connections add slack_webhook --conn-type http --conn-host https://test.slack.com
   airflow connections add docker_registry --conn-type docker
   ```

5. **Copy DAG to Airflow**
   ```bash
   cp transfermkt_workflow.py $AIRFLOW_HOME/dags/
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications

### 2. Make Your Changes

- Modify the DAG file or add new files as needed
- Add inline comments for complex logic
- Update documentation if adding new features
- Follow the coding standards (see below)

### 3. Test Your Changes

```bash
# Validate DAG syntax
python $AIRFLOW_HOME/dags/transfermkt_workflow.py

# Test the DAG
airflow dags test transfermkt_smart_workflow $(date +%Y-%m-%d)

# Test individual tasks
airflow tasks test transfermkt_smart_workflow smart_data_loading $(date +%Y-%m-%d)
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

See [Commit Messages](#commit-messages) section for format guidelines.

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on the repository.

## Coding Standards

### Python Style Guide

Follow PEP 8 guidelines:

- Use 4 spaces for indentation (not tabs)
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to all functions

### DAG Development Best Practices

1. **Use meaningful task IDs**
   ```python
   # Good
   task_id='extract_player_data'

   # Bad
   task_id='task1'
   ```

2. **Add proper documentation**
   ```python
   # Good - Explains why and what
   # Task 1: Smart Data Loading
   # Implements watermark-based incremental loading to avoid duplicate data

   # Bad - States the obvious
   # Task 1
   ```

3. **Handle errors gracefully**
   ```python
   # Always set appropriate retry policies
   default_args = {
       'retries': 2,
       'retry_delay': timedelta(minutes=5),
   }
   ```

4. **Use parameterization**
   ```python
   # Good - Uses template variables
   command="python /app/script.py {{ ds }}"

   # Bad - Hardcoded dates
   command="python /app/script.py 2024-01-01"
   ```

### Docker Operator Configuration

When adding new DockerOperator tasks:

```python
new_task = DockerOperator(
    task_id='descriptive_task_name',
    image='jonasandata/transfermkt_app:latest',
    command="python /app/your_script.py",
    docker_url='unix://var/run/docker.sock',
    network_mode='bridge',
    auto_remove=True,              # Always remove containers
    mount_tmp_dir=False,
    force_pull=True,               # Ensure latest code
    environment={
        'AWS_ACCESS_KEY_ID': aws_conn.login,
        'AWS_SECRET_ACCESS_KEY': aws_conn.password,
    },
    api_version='auto',
    docker_conn_id="docker_registry",
    on_success_callback=lambda context: slack_notify(context, "SUCCESS"),
    on_failure_callback=lambda context: slack_notify(context, "FAILURE"),
)
```

## Testing Guidelines

### Manual Testing

1. **Syntax Validation**
   ```bash
   python transfermkt_workflow.py
   ```

2. **DAG Import Test**
   ```bash
   airflow dags list | grep transfermkt
   ```

3. **Task Test**
   ```bash
   airflow tasks test transfermkt_smart_workflow <task_id> $(date +%Y-%m-%d)
   ```

4. **Full DAG Test**
   ```bash
   airflow dags test transfermkt_smart_workflow $(date +%Y-%m-%d)
   ```

### Test Checklist

Before submitting a PR, verify:

- [ ] DAG file has no syntax errors
- [ ] DAG imports successfully in Airflow
- [ ] All tasks can be tested individually
- [ ] Task dependencies are correct
- [ ] Slack notifications work (if modified)
- [ ] Docker containers execute successfully
- [ ] No hardcoded credentials or sensitive data
- [ ] Documentation is updated

### Testing with Mock Data

For testing without actual AWS/Slack credentials:

```python
# Use mock connections for testing
from unittest.mock import MagicMock

# Mock AWS connection
mock_aws = MagicMock()
mock_aws.login = 'test_key'
mock_aws.password = 'test_secret'
```

## Commit Messages

Follow the Conventional Commits specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
# Feature addition
git commit -m "feat(tasks): add data validation task"

# Bug fix
git commit -m "fix(slack): correct notification message formatting"

# Documentation
git commit -m "docs(readme): update setup instructions"

# With body
git commit -m "feat(monitoring): add data completeness report

- Implements watermark-based completeness check
- Generates JSON report with data coverage metrics
- Runs regardless of upstream task status"
```

## Pull Request Process

### 1. Before Submitting

- Ensure all tests pass
- Update documentation (README.md, CONFIGURATION.md)
- Add comments to complex code sections
- Remove any debug code or print statements
- Verify no secrets are committed

### 2. PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing Done
- [ ] Tested DAG syntax
- [ ] Tested individual tasks
- [ ] Tested full DAG run
- [ ] Verified Slack notifications (if applicable)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] No hardcoded credentials
- [ ] Commit messages follow conventions
```

### 3. Review Process

- PRs require at least one approval
- Address all review comments
- Keep PR scope focused (one feature/fix per PR)
- Be responsive to feedback

### 4. After Approval

- Squash commits if requested
- Ensure branch is up to date with main
- Maintainer will merge the PR

## Reporting Issues

### Bug Reports

Include:
- Airflow version
- Docker version
- Python version
- Error message and stack trace
- Steps to reproduce
- Expected vs actual behavior

### Feature Requests

Include:
- Clear description of the feature
- Use case and benefits
- Proposed implementation (if any)
- Alternative solutions considered

## Questions?

If you have questions about contributing:

1. Check existing documentation (README.md, CONFIGURATION.md)
2. Review closed issues and PRs
3. Open a new issue with the "question" label

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to the TransferMkt Airflow DAG project!
