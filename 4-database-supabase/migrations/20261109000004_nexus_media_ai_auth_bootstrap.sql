-- ============================================================================
-- NEXUS MEDIA AI — Migration 0004: Auth Bootstrap & Password Authentication
-- Target: Supabase PostgreSQL
-- ============================================================================

-- 1. Ensure password_hash exists on public.users for direct/standalone JWT auth
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 2. Bootstrap default super_admin account (Email: admin@nexusmedia.ai / Password: AdminPass123!)
-- Hash generated via Argon2id (m=65536, t=3, p=4)
DO $$
DECLARE
  v_admin_id UUID;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.users WHERE email = 'admin@nexusmedia.ai') THEN
    INSERT INTO public.users (email, full_name, password_hash, status)
    VALUES (
      'admin@nexusmedia.ai',
      'System Administrator',
      '$argon2id$v=19$m=65536,t=3,p=4$+YlI1iue3ctOGOsjuU89Ew$7XVUzrDWSIUdWNC3tMJ2YegYOaXpRc0MgP421DkvwIo',
      'active'
    )
    RETURNING id INTO v_admin_id;

    INSERT INTO public.user_roles (user_id, role_name)
    VALUES (v_admin_id, 'super_admin')
    ON CONFLICT (user_id, role_name) DO NOTHING;
  END IF;
END $$;
