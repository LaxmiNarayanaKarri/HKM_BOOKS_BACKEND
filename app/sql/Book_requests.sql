create table if not exists public.book_requests (
  id uuid not null default gen_random_uuid(),
  book_id bigint not null,
  quantity integer not null check (quantity > 0),
  location_id bigint not null,
  event_id bigint not null,
  priority text not null check (priority in ('cant_wait', 'important', 'immediate')),
  requested_by text not null,
  status text not null default 'pending' check (status in ('pending', 'fulfilled', 'cancelled')),
  created_at timestamp with time zone not null default now(),
  constraint book_requests_pkey primary key (id),
  constraint book_requests_book_id_fkey foreign key (book_id) references public.catalog(id),
  constraint book_requests_location_id_fkey foreign key (location_id) references public.locations(id),
  constraint book_requests_event_id_fkey foreign key (event_id) references public.events(id),
  constraint book_requests_requested_by_fkey foreign key (requested_by) references public.users(username)
) tablespace pg_default;

create index if not exists idx_book_requests_requested_by
  on public.book_requests using btree (requested_by, created_at desc);
create index if not exists idx_book_requests_status_priority
  on public.book_requests using btree (status, priority, created_at desc);

-- The Books API authenticates users before reaching Supabase. These policies
-- are needed only when the server is configured with an anon/authenticated
-- key; a server-side service_role key bypasses RLS and is preferred.
alter table public.book_requests enable row level security;

drop policy if exists book_requests_api_insert on public.book_requests;
create policy book_requests_api_insert
  on public.book_requests for insert
  to anon, authenticated
  with check (true);

drop policy if exists book_requests_api_select on public.book_requests;
create policy book_requests_api_select
  on public.book_requests for select
  to anon, authenticated
  using (true);
