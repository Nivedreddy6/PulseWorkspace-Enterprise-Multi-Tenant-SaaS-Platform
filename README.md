<div align="center">

  <!-- Animated SVG Header Banner -->
  <img src="docs/assets/banner.svg" alt="PulseWorkspace Banner" width="100%" />

  <br/><br/>

  <!-- Dynamic Tech & Status Badges -->
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
    <img src="https://img.shields.io/badge/DRF-3.18-A30000?style=for-the-badge&logo=django&logoColor=white" alt="DRF" />
    <img src="https://img.shields.io/badge/OpenAPI-3.0%20Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black" alt="Swagger" />
    <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
    <img src="https://img.shields.io/badge/Tests-Passing%20(100%25)-10B981?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests" />
    <img src="https://img.shields.io/badge/License-MIT-6366F1?style=for-the-badge" alt="License" />
  </p>

  <p align="center">
    <strong>A production-ready, multi-tenant B2B SaaS platform engineered for team collaboration and enterprise scale.</strong>
  </p>

  <p align="center">
    <a href="#-quickstart--local-setup">⚡ Quickstart</a> •
    <a href="#-architectural-overview">🏗️ Architecture</a> •
    <a href="#-key-features">✨ Features</a> •
    <a href="#-interactive-api-documentation">📡 API Docs</a> •
    <a href="#-pre-loaded-demo-credentials">🔑 Demo Accounts</a>
  </p>

</div>

---

## 🌟 Executive Summary

**PulseWorkspace** is an enterprise-grade multi-tenant team management and SaaS operations platform built with **Django 6** and **Django REST Framework**. 

Designed for high-velocity software engineering organizations, this platform demonstrates real-world software engineering competencies: **strict tenant data boundaries**, **granular Role-Based Access Control (RBAC)**, **immutable compliance audit trails**, **tiered quota gating**, **automated OpenAPI 3.0 documentation**, and **containerized DevOps readiness**.

---

---

## 🏗️ Architectural Overview & Data Flow

PulseWorkspace enforces a multi-tier defense architecture ensuring that tenant datasets are strictly sandboxed at both ORM and API query execution levels.

<div align="center">
  <img src="docs/assets/architecture.svg" alt="System Architecture Diagram" width="100%" />
</div>

### 🛡️ Core Security Invariants:
1. **Multi-Tenant Scoping**: All projects, tasks, and audit logs are bound to a `Workspace` foreign key.
2. **Permission Guards**: Attempting to query another tenant's slug or identifiers immediately terminates with **`HTTP 403 Forbidden`**.
3. **Atomic Operations**: Workspace initialization, member provisioning, and subscription assignments execute inside `transaction.atomic()` blocks.
4. **Non-Blocking Audit Telemetry**: Auditing uses safe helper logging that captures IP addresses, actors, and diff payloads without blocking critical paths.

---

## ✨ Key Platform Features

<div align="center">
  <img src="docs/assets/key_features_animated.svg" alt="PulseWorkspace Key Features Showcase" width="100%" />
</div>

---

## ⚡ Quickstart & Local Setup

### 1. Clone & Setup Environment
```bash
# Clone the repository
git clone https://github.com/Nivedreddy6/PulseWorkspace-Enterprise-Multi-Tenant-SaaS-Platform.git
cd PulseWorkspace-Enterprise-Multi-Tenant-SaaS-Platform

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.venv\Scripts\activate          # On Windows
```

### 2. Install Dependencies & Migrate
```bash
# Install packages
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed rich enterprise demo data
python manage.py seed_demo_data
```

### 3. Launch the Server
```bash
python manage.py runserver
```

🌐 Open your browser at **`http://127.0.0.1:8000/`** to view the app!

---

## 🔑 Pre-Loaded Demo Credentials

The platform includes pre-configured demo personas for instant 1-click evaluation:

| Role | Username | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **👑 Workspace Owner** | `admin` | `password123` | Full administrative control, billing upgrades, team management |
| **🛡️ Workspace Admin** | `sarah_lead` | `password123` | Project creation, member invitations, role modifications |
| **💻 Workspace Member** | `alex_dev` | `password123` | Task execution, Kanban board progression, status updates |

---

## 📡 Interactive API Documentation

PulseWorkspace provides full OpenAPI 3.0 and Swagger UI support:

| Endpoint | Description |
| :--- | :--- |
| **`/api/docs/`** | Interactive Swagger UI documentation with live testing |
| **`/api/redoc/`** | Beautiful ReDoc API specifications |
| **`/api/schema/`** | Raw OpenAPI 3.0 YAML/JSON schema endpoint |
| **`/api/v1/workspaces/`** | Tenant workspaces, memberships, and role assignments |
| **`/api/v1/projects/`** | Workspace-scoped project tracking |
| **`/api/v1/tasks/`** | Kanban tickets, priority filtering, and status updates |
| **`/api/v1/audit-logs/`** | Enterprise compliance audit trail endpoint |
| **`/api/v1/billing/`** | Subscription tiers and upgrade simulation |

---

## 🧪 Automated Testing

Execute the automated test suite verifying tenant security, RBAC rules, audit logs, and billing quotas:

```bash
python manage.py test
```

### Test Output:
```text
Creating test database for alias 'default'...
....
----------------------------------------------------------------------
Ran 4 tests in 14.063s

OK
Destroying test database for alias 'default'...
```

---

## 🐳 Docker Deployment

Run PulseWorkspace with PostgreSQL inside containers:

```bash
docker-compose up --build
```

The application will be accessible at `http://localhost:8000/` with a dedicated PostgreSQL database container.

---

## 📄 License & Attribution

Distributed under the **MIT License**. See `LICENSE` for more information.

<div align="center">
  <sub>Built with ❤️ by an ambitious software engineer to demonstrate enterprise backend &amp; full-stack excellence.</sub>
</div>
