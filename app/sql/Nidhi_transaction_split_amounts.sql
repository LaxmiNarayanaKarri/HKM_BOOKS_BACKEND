-- Preserve cents in the per-fund transparency columns.
alter table public.nidhi_transactions
  alter column tirtha_amount type numeric(14, 2)
    using tirtha_amount::numeric,
  alter column contribution_amount type numeric(14, 2)
    using contribution_amount::numeric;

-- Backfill rows created before the split columns were populated.
update public.nidhi_transactions
set
  tirtha_amount = case
    when fund_type = 'tirtha_nidhi' then amount
    else 0
  end,
  contribution_amount = case
    when fund_type = 'contribution_nidhi' then amount
    else 0
  end
where coalesce(tirtha_amount, 0) = 0
  and coalesce(contribution_amount, 0) = 0;
