
-- 1. Create role enum
CREATE TYPE public.app_role AS ENUM ('admin', 'member');

-- 2. User roles table
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  role app_role NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, role)
);
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- 3. Security definer helper function
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;

-- 4. Roster members table (all 58 EAA fields)
CREATE TABLE public.roster_members (
  key_id INTEGER PRIMARY KEY,
  eaa_number TEXT,
  member_type TEXT,
  nickname TEXT,
  first_name TEXT,
  last_name TEXT,
  spouse TEXT,
  gender TEXT,
  email TEXT,
  email_private BOOLEAN DEFAULT false,
  username TEXT,
  birth_date DATE,
  street_address_1 TEXT,
  street_address_2 TEXT,
  address_private BOOLEAN DEFAULT false,
  home_phone TEXT,
  home_phone_private BOOLEAN DEFAULT false,
  cell_phone TEXT,
  cell_phone_private BOOLEAN DEFAULT false,
  current_standing TEXT,
  current_joined_on_date DATE,
  expiration_date DATE,
  other_info TEXT,
  preferred_city TEXT,
  preferred_state TEXT,
  country TEXT,
  zip_code TEXT,
  ratings TEXT,
  aircraft_owned TEXT,
  aircraft_project TEXT,
  aircraft_built TEXT,
  imc BOOLEAN DEFAULT false,
  vmc BOOLEAN DEFAULT false,
  young_eagle_pilot BOOLEAN DEFAULT false,
  young_eagle_volunteer BOOLEAN DEFAULT false,
  eagle_pilot BOOLEAN DEFAULT false,
  eagle_flight_volunteer BOOLEAN DEFAULT false,
  date_added DATE,
  date_updated DATE,
  updated_by TEXT,
  eaa_expiration DATE,
  youth_protection TEXT,
  background_check TEXT,
  udf1 TEXT,
  udf1_text TEXT,
  udf2 TEXT,
  udf2_text TEXT,
  udf3 TEXT,
  udf3_text TEXT,
  udf4 TEXT,
  udf4_text TEXT,
  udf5 TEXT,
  udf5_text TEXT,
  admin_level_desc TEXT,
  chapter_name TEXT,
  chapter_number TEXT,
  chapter_type TEXT,
  aptify_id INTEGER,
  last_import_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.roster_members ENABLE ROW LEVEL SECURITY;

-- 5. Member chapter data (chapter-specific fields)
CREATE TABLE public.member_chapter_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key_id INTEGER NOT NULL REFERENCES public.roster_members(key_id) ON DELETE CASCADE,
  chapter_payment_method TEXT,
  chapter_payment_notes TEXT,
  application_status TEXT DEFAULT 'Submitted',
  pending_roster_update BOOLEAN DEFAULT false,
  internal_notes TEXT,
  volunteer_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(key_id)
);
ALTER TABLE public.member_chapter_data ENABLE ROW LEVEL SECURITY;

-- 6. Roster imports tracking
CREATE TABLE public.roster_imports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  imported_by UUID REFERENCES auth.users(id),
  file_name TEXT,
  record_count INTEGER DEFAULT 0,
  added_count INTEGER DEFAULT 0,
  modified_count INTEGER DEFAULT 0,
  removed_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'completed'
);
ALTER TABLE public.roster_imports ENABLE ROW LEVEL SECURITY;

-- 7. Import change records (field-level diffs)
CREATE TABLE public.roster_import_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_id UUID NOT NULL REFERENCES public.roster_imports(id) ON DELETE CASCADE,
  key_id INTEGER NOT NULL,
  change_type TEXT NOT NULL CHECK (change_type IN ('added', 'modified', 'removed')),
  field_name TEXT,
  old_value TEXT,
  new_value TEXT,
  first_name TEXT,
  last_name TEXT,
  eaa_number TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.roster_import_changes ENABLE ROW LEVEL SECURITY;
CREATE INDEX idx_import_changes_import_id ON public.roster_import_changes(import_id);
CREATE INDEX idx_import_changes_key_id ON public.roster_import_changes(key_id);

-- 8. Updated_at trigger function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_roster_members_updated_at
  BEFORE UPDATE ON public.roster_members
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_member_chapter_data_updated_at
  BEFORE UPDATE ON public.member_chapter_data
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- 9. RLS Policies

-- user_roles: admins see all, users see own
CREATE POLICY "Users can view own role" ON public.user_roles
  FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins manage roles" ON public.user_roles
  FOR ALL TO authenticated
  USING (public.has_role(auth.uid(), 'admin'))
  WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- roster_members: authenticated can read, admins can write
CREATE POLICY "Authenticated users can view members" ON public.roster_members
  FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "Admins can insert members" ON public.roster_members
  FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can update members" ON public.roster_members
  FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can delete members" ON public.roster_members
  FOR DELETE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

-- member_chapter_data: authenticated can read, admins can write
CREATE POLICY "Authenticated users can view chapter data" ON public.member_chapter_data
  FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "Admins can insert chapter data" ON public.member_chapter_data
  FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can update chapter data" ON public.member_chapter_data
  FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can delete chapter data" ON public.member_chapter_data
  FOR DELETE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

-- roster_imports: authenticated can read, admins can write
CREATE POLICY "Authenticated users can view imports" ON public.roster_imports
  FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "Admins can insert imports" ON public.roster_imports
  FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can update imports" ON public.roster_imports
  FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can delete imports" ON public.roster_imports
  FOR DELETE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

-- roster_import_changes: authenticated can read, admins can write
CREATE POLICY "Authenticated users can view changes" ON public.roster_import_changes
  FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "Admins can insert changes" ON public.roster_import_changes
  FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Admins can delete changes" ON public.roster_import_changes
  FOR DELETE TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));
