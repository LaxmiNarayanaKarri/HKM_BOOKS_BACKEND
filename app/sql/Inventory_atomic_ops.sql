-- migrations/inventory_atomic_ops.sql
--
-- 1. A stock row is one-per-book by convention already (StockDomain.create_stock
--    enforces it in app code) -- make the DB enforce it too, since ON CONFLICT
--    below depends on it.
alter table public.stock
  add constraint stock_book_id_key unique (book_id);


-- 2. Stock-only atomic batch adjust. Backs IStockRepository.upsert_batch /
--    StockDomain.adjust_stock_for_batch. A single function call runs as one
--    Postgres transaction -- if any delta would take a book negative, the
--    exception aborts the whole batch and nothing is written.
create or replace function public.adjust_stock_batch(p_deltas jsonb)
returns setof public.stock
language plpgsql
as $$
declare
  item jsonb;
  v_book_id bigint;
  v_delta bigint;
begin
  if p_deltas is null or jsonb_array_length(p_deltas) = 0 then
    raise exception 'p_deltas must contain at least one item';
  end if;

  for item in select * from jsonb_array_elements(p_deltas)
  loop
    v_book_id := (item->>'book_id')::bigint;
    v_delta   := (item->>'delta')::bigint;

    insert into public.stock (book_id, stock, cost)
    values (v_book_id, greatest(v_delta, 0), null)
    on conflict (book_id) do update
      set stock = public.stock.stock + v_delta
    where public.stock.stock + v_delta >= 0;

    if not found then
      raise exception 'Adjusting book_id % by % would take stock negative', v_book_id, v_delta;
    end if;
  end loop;

  return query
    select s.* from public.stock s, jsonb_array_elements(p_deltas) d
    where s.book_id = (d->>'book_id')::bigint;
end;
$$;


-- 3. record_inward_batch backing: inserts one purchases row per item AND
--    applies the matching stock delta, all in the single transaction this
--    function call runs in. Each item is self-contained (carries its own
--    purchase_date/source_id/recorded_by) so this one function backs
--    record_purchase (1 item), record_batch (N items, no shared header),
--    and record_inward_stock (N items sharing a header the caller repeats
--    per item) alike.
create or replace function public.record_inward_stock_batch(
  p_items jsonb  -- [{ "book_id", "qty", "cost_price", "purchase_date", "source_id", "recorded_by" }, ...]
)
returns setof public.purchases
language plpgsql
as $$
declare
  item jsonb;
  v_book_id bigint;
  v_qty bigint;
  v_cost bigint;
  v_purchase_date date;
  v_source_id bigint;
  v_recorded_by text;
begin
  if p_items is null or jsonb_array_length(p_items) = 0 then
    raise exception 'p_items must contain at least one item';
  end if;

  for item in select * from jsonb_array_elements(p_items)
  loop
    v_book_id      := (item->>'book_id')::bigint;
    v_qty          := (item->>'qty')::bigint;
    v_cost         := (item->>'cost_price')::bigint;
    v_purchase_date := (item->>'purchase_date')::date;
    v_source_id    := (item->>'source_id')::bigint;
    v_recorded_by  := item->>'recorded_by';

    if v_book_id is null then
      raise exception 'book_id is required for every item';
    end if;
    if v_qty is null or v_qty <= 0 then
      raise exception 'qty must be positive for book_id %', v_book_id;
    end if;

    return query
      insert into public.purchases
        (purchase_date, book_id, source_id, qty, cost_price, recorded_by, created_at)
      values
        (v_purchase_date, v_book_id, v_source_id, v_qty, v_cost, v_recorded_by, now())
      returning *;

    -- last-cost tracking: overwrites stock.cost with this purchase's
    -- cost_price. Swap for a weighted-average calc here if you want that.
    insert into public.stock (book_id, stock, cost)
    values (v_book_id, v_qty, v_cost)
    on conflict (book_id) do update
      set stock = public.stock.stock + excluded.stock,
          cost  = excluded.cost;
  end loop;
end;
$$;


-- 4. update_purchase_atomic: edits a purchase row AND corrects stock by
--    the resulting delta, in one transaction. Handles both a plain qty/cost
--    edit and a book_id change (reverses the old book's stock, applies to
--    the new book's stock). Raises rather than letting stock go negative --
--    e.g. reducing a purchase's qty below what's already been sold.
create or replace function public.update_purchase_atomic(
  p_purchase_id bigint,
  p_fields jsonb  -- any of: book_id, qty, cost_price, purchase_date, source_id, recorded_by
)
returns public.purchases
language plpgsql
as $$
declare
  old_row public.purchases%rowtype;
  new_book_id bigint;
  new_qty bigint;
  new_cost bigint;
  qty_delta bigint;
  updated public.purchases%rowtype;
begin
  select * into old_row from public.purchases where id = p_purchase_id for update;
  if not found then
    raise exception 'Purchase % not found', p_purchase_id;
  end if;

  new_book_id := coalesce((p_fields->>'book_id')::bigint, old_row.book_id);
  new_qty     := coalesce((p_fields->>'qty')::bigint, old_row.qty);
  new_cost    := case when p_fields ? 'cost_price'
                       then (p_fields->>'cost_price')::bigint
                       else old_row.cost_price end;

  if new_qty is null or new_qty <= 0 then
    raise exception 'qty must be positive';
  end if;

  update public.purchases
  set
    book_id       = new_book_id,
    qty           = new_qty,
    cost_price    = new_cost,
    purchase_date = coalesce((p_fields->>'purchase_date')::date, purchase_date),
    source_id     = coalesce((p_fields->>'source_id')::bigint, source_id),
    recorded_by   = coalesce(p_fields->>'recorded_by', recorded_by)
  where id = p_purchase_id
  returning * into updated;

  if new_book_id = old_row.book_id then
    qty_delta := new_qty - old_row.qty;
    if qty_delta <> 0 then
      update public.stock
      set stock = stock + qty_delta,
          cost  = new_cost
      where book_id = new_book_id
        and stock + qty_delta >= 0;

      if not found then
        raise exception 'Editing purchase % would take stock for book_id % negative',
          p_purchase_id, new_book_id;
      end if;
    end if;
  else
    update public.stock
    set stock = stock - old_row.qty
    where book_id = old_row.book_id
      and stock - old_row.qty >= 0;

    if not found then
      raise exception 'Reversing purchase % from book_id % would take stock negative',
        p_purchase_id, old_row.book_id;
    end if;

    insert into public.stock (book_id, stock, cost)
    values (new_book_id, new_qty, new_cost)
    on conflict (book_id) do update
      set stock = public.stock.stock + excluded.stock,
          cost  = excluded.cost;
  end if;

  return updated;
end;
$$;


-- 5. delete_purchase_atomic: deletes a purchase row AND reverses its
--    contribution to stock, in one transaction. Raises rather than letting
--    stock go negative -- i.e. refuses to delete a purchase if the stock
--    it brought in has already been partly sold.
create or replace function public.delete_purchase_atomic(p_purchase_id bigint)
returns boolean
language plpgsql
as $$
declare
  old_row public.purchases%rowtype;
begin
  select * into old_row from public.purchases where id = p_purchase_id for update;
  if not found then
    return false;
  end if;

  delete from public.purchases where id = p_purchase_id;

  update public.stock
  set stock = stock - old_row.qty
  where book_id = old_row.book_id
    and stock - old_row.qty >= 0;

  if not found then
    raise exception 'Deleting purchase % would take stock for book_id % negative',
      p_purchase_id, old_row.book_id;
  end if;

  return true;
end;
$$;


---------------------------




-- Sales atomic ops

-- migrations/sales_atomic_ops.sql
--
-- record_sale_batch: inserts one sales row per item AND decrements
-- stock by the matching qty, all in the single transaction this
-- function call runs in. Mirrors record_inward_stock_batch, just in
-- the opposite direction (stock down instead of up).
--
-- category_id/language_id are passed in per item rather than looked
-- up here, matching the app's existing behaviour: SupabaseSellEntryRepository
-- already resolves the book via IBookRepository before calling this,
-- to snapshot the book's *current* category/language onto the sale row.
--
-- sales.created_at has a DB default (now() at time zone 'utc') and is
-- a real timestamptz, so it's left untouched -- no ::text formatting
-- needed here, unlike purchases.created_at.
create or replace function public.record_sale_batch(
  p_items jsonb,  -- [{ "book_id", "category_id", "language_id", "qty", "cost_price", "sell_price" }, ...]
  p_sales_date date,
  p_seller_username text,
  p_location_id bigint,
  p_event_id bigint
)
returns setof public.sales
language plpgsql
as $$
declare
  item jsonb;
  v_book_id bigint;
  v_category_id bigint;
  v_language_id bigint;
  v_qty bigint;
  v_cost_price double precision;
  v_sell_price double precision;
begin
  if p_items is null or jsonb_array_length(p_items) = 0 then
    raise exception 'p_items must contain at least one item';
  end if;

  for item in select * from jsonb_array_elements(p_items)
  loop
    v_book_id     := (item->>'book_id')::bigint;
    v_category_id := (item->>'category_id')::bigint;
    v_language_id := (item->>'language_id')::bigint;
    v_qty         := (item->>'qty')::bigint;
    v_cost_price  := (item->>'cost_price')::double precision;
    v_sell_price  := (item->>'sell_price')::double precision;

    if v_book_id is null then
      raise exception 'book_id is required for every item';
    end if;
    if v_qty is null or v_qty <= 0 then
      raise exception 'qty must be positive for book_id %', v_book_id;
    end if;

    return query
      insert into public.sales
        (sales_date, book_id, category_id, seller_username, qty, cost_price,
         sell_price, language_id, location_id, event_id)
      values
        (p_sales_date, v_book_id, v_category_id, p_seller_username, v_qty, v_cost_price,
         v_sell_price, v_language_id, p_location_id, p_event_id)
      returning *;

    update public.stock
    set stock = stock - v_qty
    where book_id = v_book_id
      and stock - v_qty >= 0;

    if not found then
      raise exception 'Selling % of book_id % would take stock negative', v_qty, v_book_id;
    end if;
  end loop;
end;
$$;