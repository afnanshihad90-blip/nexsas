# NEXUS MEDIA AI — Step 2: Supabase Database Architecture & RLS Documentation

## 1. Overview
NEXUS MEDIA AI uses **Supabase PostgreSQL** as its primary relational database. The schema is organized into **10 operational domains** comprising **37 normalized tables**, engineered with UUID primary keys (`gen_random_uuid()`), strict foreign-key referential integrity, automated `updated_at` triggers, targeted indexes, and defense-in-depth **Row Level Security (RLS)**.

---

## 2. Relational Schema by Domain (37 Tables)

### Domain 1: User Management
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `users` | `id (UUID)` | `email UNIQUE`, `auth_user_id UNIQUE` | Newsroom staff, editors, and system operators. |
| `user_roles` | `id (UUID)` | `user_id -> users(id) ON DELETE CASCADE`, `UNIQUE(user_id, role_name)` | Role-based access control (`super_admin`, `managing_editor`, `fact_checker`, `operator`, `viewer`). |
| `user_sessions` | `id (UUID)` | `user_id -> users(id) ON DELETE CASCADE` | Audit trail of active, expired, or revoked operator sessions. |

### Domain 2: AI Agent Management
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `agents` | `id (UUID)` | `slug UNIQUE`, `name UNIQUE` | Master registry of the 9 autonomous newsroom agents. |
| `agent_configs` | `id (UUID)` | `agent_id -> agents(id) ON DELETE CASCADE` | Protected LLM model parameters, concurrency limits, and system directives. |
| `agent_tasks` | `id (UUID)` | `agent_id -> agents(id) ON DELETE CASCADE` | Queued, running, completed, and failed execution units. |
| `agent_activity` | `id (UUID)` | `agent_id -> agents(id) ON DELETE CASCADE`, `task_id -> agent_tasks(id)` | Chronological operational telemetry across all 7 pipeline event types. |

### Domain 3: News Intelligence
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `news_categories` | `id (UUID)` | `slug UNIQUE`, `name UNIQUE` | Editorial verticals with `is_public_approved` visibility gate. |
| `news_sources` | `id (UUID)` | `feed_url UNIQUE` | RSS/Atom, Wire API, Regulatory Filing, and Social Stream endpoints. |
| `trending_topics` | `id (UUID)` | `category_id -> news_categories(id)`, `assigned_agent_id -> agents(id)` | High-velocity signal clusters and corroboration counts. |
| `news_items` | `id (UUID)` | `source_id -> news_sources(id) ON DELETE RESTRICT`, `UNIQUE(source_id, external_guid)` | Raw ingested wire dispatches and regulatory bulletins. |

### Domain 4: Research & Verification
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `research_sessions` | `id (UUID)` | `trending_topic_id -> trending_topics(id)`, `lead_agent_id -> agents(id)` | Deep background dossiers compiled before article drafting. |
| `research_sources` | `id (UUID)` | `research_session_id -> research_sessions(id) ON DELETE CASCADE` | Primary filings and institutional citations attached to a dossier. |
| `fact_checks` | `id (UUID)` | `research_session_id -> research_sessions(id) ON DELETE CASCADE` | Verification gate audits performed by the Fact Checker agent. |
| `verified_claims` | `id (UUID)` | `fact_check_id -> fact_checks(id) ON DELETE CASCADE` | Individual quantitative or factual claims and primary source verdicts. |

### Domain 5: Content Management
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `articles` | `id (UUID)` | `article_code UNIQUE`, `slug UNIQUE`, `primary_category_id -> news_categories(id)` | Master news article records across `Drafts`, `Awaiting Approval`, `Scheduled`, `Published`, and `Failed`. |
| `article_versions` | `id (UUID)` | `article_id -> articles(id) ON DELETE CASCADE`, `UNIQUE(article_id, version_number)` | Immutable revision history for every draft iteration. |
| `article_categories` | `id (UUID)` | `article_id -> articles(id)`, `category_id -> news_categories(id)` | Many-to-many join mapping articles to approved categories. |
| `article_tags` | `id (UUID)` | `article_id -> articles(id) ON DELETE CASCADE`, `UNIQUE(article_id, tag_slug)` | Taxonomy tags for topic clustering and internal linking. |
| `editorial_quality` | `id (UUID)` | `article_id -> articles(id) ON DELETE CASCADE` | Readability, neutrality, citation density, and originality scores. |
| `seo_metadata` | `id (UUID)` | `article_id -> articles(id) ON DELETE CASCADE` | Meta titles, descriptions, canonical URLs, and Schema.org `NewsArticle` JSON-LD. |

### Domain 6: Media Management
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `image_licenses` | `id (UUID)` | `license_code UNIQUE` | Commercial usage rights and attribution requirements. |
| `image_library` | `id (UUID)` | `license_id -> image_licenses(id)`, `storage_path UNIQUE` | Verified editorial photography, aspect ratios, and WCAG alt text. |
| `media_attributions` | `id (UUID)` | `image_id -> image_library(id)`, `article_id -> articles(id)` | Links visual assets to articles with credit lines and captions. |

### Domain 7: Publishing
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `social_accounts` | `id (UUID)` | `UNIQUE(platform, handle)` | Connected distribution profiles (X, LinkedIn, YouTube, Threads, Bluesky, Telegram). |
| `publishing_jobs` | `id (UUID)` | `article_id -> articles(id) ON DELETE CASCADE` | Staged release jobs across permanent web, social, and video channels. |
| `social_posts` | `id (UUID)` | `publishing_job_id -> publishing_jobs(id)`, `social_account_id -> social_accounts(id)` | Platform-tailored social copy and external post IDs. |
| `publishing_logs` | `id (UUID)` | `publishing_job_id -> publishing_jobs(id) ON DELETE CASCADE` | Delivery receipts, retry traces, and webhook responses. |

### Domain 8: Website Management
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `site_templates` | `id (UUID)` | `template_key UNIQUE` | Layout configurations for the permanent news portal. |
| `site_settings` | `id (UUID)` | `setting_key UNIQUE` | Global publication configuration and branding metadata. |
| `ad_placements` | `id (UUID)` | `slot_code UNIQUE` | Programmatic display and native sponsorship slot definitions. |

### Domain 9: Analytics
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `analytics_daily` | `id (UUID)` | `metric_date UNIQUE` | Daily rollup of articles, views, social reach, revenue, and failed jobs. |
| `website_traffic` | `id (UUID)` | `article_id -> articles(id) ON DELETE SET NULL` | Per-article reader sessions, unique visitors, and referral sources. |
| `social_analytics` | `id (UUID)` | `social_post_id -> social_posts(id) ON DELETE CASCADE` | Impressions, engagements, and link clicks per syndicated post. |
| `revenue_reports` | `id (UUID)` | `ad_placement_id -> ad_placements(id)`, `category_id -> news_categories(id)` | Daily RPM yield and gross revenue attribution. |

### Domain 10: System Management
| Table | Primary Key | Key Foreign Keys & Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `api_connections` | `id (UUID)` | `service_slug UNIQUE` | Non-secret connection health telemetry for external services. |
| `system_logs` | `id (UUID)` | Indexed on `(severity, created_at DESC)` | Infrastructure and worker diagnostic logs. |
| `system_settings` | `id (UUID)` | `setting_key UNIQUE` | Global orchestration flags and safety gates. |
| `webhook_events` | `id (UUID)` | Indexed on `(status, created_at DESC)` | Inbound webhook payloads and processing state. |

---

## 3. Row Level Security (RLS) Policy Matrix

Every table has `ROW LEVEL SECURITY` enabled by default:

1. **Public Visitor Access (`anon`, `authenticated`)**:
   - `articles`: `SELECT` permitted **only** when `stage = 'Published' AND is_public = TRUE`.
   - `news_categories`: `SELECT` permitted **only** when `is_public_approved = TRUE`.
   - `article_categories`, `article_tags`, `seo_metadata`, `media_attributions`: `SELECT` permitted **only** when linked to a published public article.
   - `image_library`: `SELECT` permitted **only** when `status = 'approved' AND is_public = TRUE`.
2. **Protected Admin & Staff Tables**:
   - `agent_configs`, `api_connections`, `analytics_daily`, `website_traffic`, `social_analytics`, `revenue_reports`, `system_logs`, `system_settings`, `webhook_events`: Restricted strictly to authenticated admins (`public.is_nexus_admin()`).
   - `user_roles`: Only `super_admin` can modify role assignments.
3. **Privileged Backend Mutations (Step 3 FastAPI Integration)**:
   - Autonomous agent background writes use the server-side FastAPI service in Step 3. The Supabase `service_role` key is **never** exposed in frontend `VITE_*` variables.
