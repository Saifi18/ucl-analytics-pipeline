-- ================================================================
-- Model   : stg_matches
-- Layer   : Staging
-- Source  : data/silver_local/matches_silver_ucl_matches_*.parquet
-- Purpose : Clean wrapper over Silver matches Parquet.
--           Confirms column names and types before mart consumption.
--           No aggregation, no joins, no business logic here.
-- ================================================================

with source as (

    select *
    from read_parquet('../data/silver_local/matches_silver_ucl_matches_*.parquet')

),

staged as (

    select
        -- Match identifiers 
        match_id,
        match_date,
        match_timestamp,
        matchday,
        stage,
        group_name,
        status,
        is_finished,

        -- ── Competition ───────────────────────────────────
        competition_id,
        competition_name,
        competition_code,
        season_id,

        -- ── Teams ─────────────────────────────────────────
        home_team_id,
        home_team_name,
        home_team_short,
        away_team_id,
        away_team_name,
        away_team_short,

        -- ── Scores ────────────────────────────────────────
        home_score_ft,
        away_score_ft,
        home_score_ht,
        away_score_ht,

        -- ── Derived columns from Silver ───────────────────
        winner,
        home_result,
        total_goals,
        goal_difference,
        referee_name,

        -- ── Audit metadata ────────────────────────────────
        silver_processed_at,
        source_blob

    from source

)

select * from staged