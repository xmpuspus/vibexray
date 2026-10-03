create table public.survey_responses (
  id uuid primary key default gen_random_uuid(),
  survey_key text not null,
  answers jsonb not null default '{}'::jsonb,
  submitted_at timestamptz not null default now()
);

create index survey_responses_survey_key_idx on public.survey_responses (survey_key);

grant insert on public.survey_responses to anon, authenticated;
grant select, delete on public.survey_responses to authenticated;
grant all on public.survey_responses to service_role;

alter table public.survey_responses enable row level security;

create policy "Anyone can submit a survey response"
on public.survey_responses
for insert
to anon, authenticated
with check (true);

create policy "Admins and officers can read responses"
on public.survey_responses
for select
to authenticated
using (
  has_role(auth.uid(), 'admin'::app_role)
  or has_role(auth.uid(), 'officer'::app_role)
  or is_officer((auth.jwt() ->> 'email'))
);

create policy "Admins can delete responses"
on public.survey_responses
for delete
to authenticated
using (has_role(auth.uid(), 'admin'::app_role));