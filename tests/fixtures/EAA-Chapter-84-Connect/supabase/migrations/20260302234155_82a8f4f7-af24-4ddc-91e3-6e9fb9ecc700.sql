
-- Create storage bucket for member images
INSERT INTO storage.buckets (id, name, public) VALUES ('member-images', 'member-images', true);

-- Storage policies: anyone can view, members can manage their own images
CREATE POLICY "Anyone can view member images"
ON storage.objects FOR SELECT
USING (bucket_id = 'member-images');

CREATE POLICY "Members can upload own images"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'member-images'
  AND (storage.foldername(name))[1] IN (
    SELECT rm.key_id::text FROM public.roster_members rm
    WHERE rm.email = (auth.jwt() ->> 'email')
  )
);

CREATE POLICY "Members can delete own images"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'member-images'
  AND (storage.foldername(name))[1] IN (
    SELECT rm.key_id::text FROM public.roster_members rm
    WHERE rm.email = (auth.jwt() ->> 'email')
  )
);

CREATE POLICY "Admins can manage all member images"
ON storage.objects FOR ALL
USING (bucket_id = 'member-images' AND public.has_role(auth.uid(), 'admin'))
WITH CHECK (bucket_id = 'member-images' AND public.has_role(auth.uid(), 'admin'));

-- Table to track member images with metadata
CREATE TABLE public.member_images (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key_id integer NOT NULL,
  storage_path text NOT NULL,
  caption text,
  sort_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT member_images_max_4 UNIQUE (key_id, sort_order),
  CONSTRAINT sort_order_range CHECK (sort_order >= 0 AND sort_order <= 3)
);

ALTER TABLE public.member_images ENABLE ROW LEVEL SECURITY;

-- Anyone authenticated can view
CREATE POLICY "Authenticated users can view member images"
ON public.member_images FOR SELECT
USING (true);

-- Members can insert their own (up to 4 enforced by sort_order constraint)
CREATE POLICY "Members can insert own images"
ON public.member_images FOR INSERT
WITH CHECK (
  key_id IN (SELECT rm.key_id FROM public.roster_members rm WHERE rm.email = (auth.jwt() ->> 'email'))
);

CREATE POLICY "Members can update own images"
ON public.member_images FOR UPDATE
USING (key_id IN (SELECT rm.key_id FROM public.roster_members rm WHERE rm.email = (auth.jwt() ->> 'email')))
WITH CHECK (key_id IN (SELECT rm.key_id FROM public.roster_members rm WHERE rm.email = (auth.jwt() ->> 'email')));

CREATE POLICY "Members can delete own images"
ON public.member_images FOR DELETE
USING (key_id IN (SELECT rm.key_id FROM public.roster_members rm WHERE rm.email = (auth.jwt() ->> 'email')));

-- Admins full access
CREATE POLICY "Admins can manage all images"
ON public.member_images FOR ALL
USING (public.has_role(auth.uid(), 'admin'))
WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- Trigger for updated_at
CREATE TRIGGER update_member_images_updated_at
BEFORE UPDATE ON public.member_images
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();
